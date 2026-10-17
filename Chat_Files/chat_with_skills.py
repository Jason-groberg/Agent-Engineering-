"""Terminal skills chat. Run: python chat_with_skills.py

Dependencies: openai python-dotenv litellm pyyaml
Uses OPENAI_API_KEY from the environment or repository .env.

Add reusable skills at ../Skills/<skill-folder>/SKILL.md with YAML metadata:
    ---
    name: skill-name
    description: When to use this skill.
    ---
    Skill instructions go here. Reference supporting text files relative to
    this SKILL.md; they are read only when requested.
"""

from argparse import ArgumentParser
import json
from pathlib import Path
import sys
import time

from dotenv import load_dotenv
from litellm import cost_per_token
from openai import OpenAI
import yaml

from usage_tracker import UsageTracker

REPOSITORY_DIR = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPOSITORY_DIR / "Skills"
# The shared Tools directory is beside Chat_Files, not inside it.
sys.path.insert(0, str(REPOSITORY_DIR))
from Tools.agentic_tools import shell, read, write, edit, tools as custom_tools

DEFAULT_MODEL = "gpt-5.6-luna"
MAX_STEPS = 10
INSTRUCTIONS = (
    "Reply in plain text suitable for a terminal. Use the available tools to "
    "complete the user's task. The skill catalog contains metadata only. "
    "When a skill is relevant, call load_skill before following its instructions. "
    "Loaded skill instructions remain in conversation history. Read supporting "
    "text resources with read_skill_resource only when needed, using paths "
    "relative to that skill's SKILL.md. Do not load unrelated skills or resources."
)
available_tools = {"shell": shell, "read": read, "write": write, "edit": edit}
tools = custom_tools + [
    {
        "type": "function",
        "name": "load_skill",
        "description": "Load a cataloged skill's instructions into this conversation once.",
        "parameters": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "read_skill_resource",
        "description": "Read a UTF-8 supporting file relative to a loaded skill's SKILL.md.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "path": {"type": "string"},
            },
            "required": ["name", "path"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


def discover_skills(skills_dir=SKILLS_DIR):
    """Read only front matter, leaving bodies and resources out of the catalog."""
    catalog = {}
    for path in sorted(skills_dir.rglob("SKILL.md")):
        try:
            resolved_path = path.resolve()
            if not resolved_path.is_relative_to(skills_dir.resolve()):
                raise ValueError("Skill file must be inside the Skills directory")
            with path.open(encoding="utf-8-sig") as file:
                if file.readline().strip() != "---":
                    raise ValueError("Expected YAML front matter starting with ---")
                header = []
                for line in file:
                    if line.strip() == "---":
                        break
                    header.append(line)
                else:
                    raise ValueError("Missing closing --- for YAML front matter")
            metadata = yaml.safe_load("".join(header))
            if not isinstance(metadata, dict):
                raise ValueError("Skill metadata must contain name and description")
            name = metadata.get("name")
            description = metadata.get("description")
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Skill name must be a nonempty string")
            if not isinstance(description, str) or not description.strip():
                raise ValueError("Skill description must be a nonempty string")
            name = name.strip()
            if name in catalog:
                raise ValueError(f"Duplicate skill name: {name}")
            catalog[name] = {
                "name": name,
                "description": description.strip(),
                "file": path.relative_to(skills_dir).as_posix(),
                "path": resolved_path,
            }
        except (OSError, ValueError, yaml.YAMLError) as exc:
            print(f"Skipping skill {path}: {exc}")
    return catalog


def catalog_instructions(catalog):
    metadata = [
        {key: skill[key] for key in ("name", "description", "file")}
        for skill in catalog.values()
    ]
    return INSTRUCTIONS + "\nAvailable skills:\n" + json.dumps(metadata, ensure_ascii=False)


def load_skill(name, catalog, loaded_skills):
    if name not in catalog:
        raise ValueError(f"Unknown skill: {name}")
    if name in loaded_skills:
        return {"name": name, "status": "Already loaded; use instructions in history."}
    skill = catalog[name]
    content = skill["path"].read_text(encoding="utf-8-sig")
    loaded_skills.add(name)
    return {"name": name, "file": skill["file"], "instructions": content}


def read_skill_resource(name, path, catalog, loaded_skills):
    if name not in loaded_skills:
        raise ValueError(f"Load skill {name} before reading its resources")
    skill_dir = catalog[name]["path"].parent
    relative_path = Path(path)
    if relative_path.is_absolute() or relative_path.drive or not path.strip():
        raise ValueError("Resource path must be relative to the skill directory")
    resource_path = (skill_dir / relative_path).resolve()
    if not resource_path.is_relative_to(skill_dir):
        raise ValueError("Resource path must stay inside the skill directory")
    if resource_path == catalog[name]["path"]:
        raise ValueError("Use load_skill for skill instructions")
    return {"name": name, "path": path, "content": resource_path.read_text(encoding="utf-8")}


def execute_tool(call, catalog, loaded_skills):
    try:
        args = json.loads(call.arguments or "{}")
        if not isinstance(args, dict):
            raise ValueError("Tool arguments must be a JSON object")
        print(f"Function: {call.name} with args {args}")
        if call.name == "load_skill":
            return load_skill(catalog=catalog, loaded_skills=loaded_skills, **args)
        if call.name == "read_skill_resource":
            return read_skill_resource(catalog=catalog, loaded_skills=loaded_skills, **args)
        if call.name not in available_tools:
            raise ValueError(f"Unknown tool: {call.name}")
        return available_tools[call.name](**args)
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def record_response(tracker, response, elapsed, user_input):
    tracker.track(response, elapsed, user_input)
    record = tracker["records"][-1]
    calls = [
        {"name": item.name, "arguments": item.arguments, "call_id": item.call_id}
        for item in response.output if item.type == "function_call"
    ]
    if calls:
        record["response_text"] = (
            response.output_text + "\n[Tool calls] " + json.dumps(calls)
        ).strip()
    # The shared tracker uses zero when pricing lookup fails. Make that visible
    # in the terminal and saved conversation without changing the shared helper.
    try:
        cost_per_token(model=response.model, prompt_tokens=response.usage.input_tokens,
                       completion_tokens=response.usage.output_tokens)
        record["cost_available"] = True
    except Exception:
        record["cost_available"] = False
        note = f"Cost estimate unavailable for {response.model}; recorded zero is a placeholder."
        record["response_text"] += "\n[" + note + "]"
        print(note)


def chat_with_skills(model=DEFAULT_MODEL, max_steps=MAX_STEPS, effort="medium"):
    if max_steps < 1:
        raise ValueError("max_steps must be at least 1")
    load_dotenv(REPOSITORY_DIR / ".env")
    tracker = UsageTracker()
    history = []
    loaded_skills = set()
    print("Blank input or /exit exits; /reset clears history and loaded skills.")
    try:
        catalog = discover_skills()
        print(f"Found {len(catalog)} skills in {SKILLS_DIR}")
        with OpenAI() as client:
            while True:
                user_input = input("User: ").strip()
                if not user_input or user_input == "/exit":
                    break
                if user_input == "/reset":
                    history.clear()
                    loaded_skills.clear()
                    catalog = discover_skills()
                    print(f"Conversation reset. Found {len(catalog)} skills.")
                    continue
                history.append({"role": "user", "content": user_input})
                try:
                    for step in range(max_steps):
                        start = time.perf_counter()
                        response = client.responses.create(
                            model=model,
                            input=history,
                            instructions=catalog_instructions(catalog),
                            reasoning={"effort": effort},
                            tools=tools,
                            # Reserve the final response for an answer after tool results.
                            tool_choice="none" if step == max_steps - 1 else "auto",
                        )
                        record_response(tracker, response, time.perf_counter() - start, user_input)
                        history.extend(response.output)
                        calls = [item for item in response.output if item.type == "function_call"]
                        if not calls:
                            print("Assistant:", response.output_text or "No text returned.")
                            break
                        for call in calls:
                            result = execute_tool(call, catalog, loaded_skills)
                            history.append({
                                "type": "function_call_output",
                                "call_id": call.call_id,
                                "output": json.dumps(result, ensure_ascii=False),
                            })
                    else:
                        print(f"Stopped: exceeded response step limit ({max_steps}).")
                except Exception as exc:
                    # Clear a potentially unfinished tool exchange before another turn.
                    history.clear()
                    loaded_skills.clear()
                    print(f"Stopped: {type(exc).__name__}: {exc}. Conversation reset.")
    except (KeyboardInterrupt, EOFError):
        print("\nChat stopped.")
    finally:
        if any(not record.get("cost_available", True) for record in tracker["records"]):
            print("Cost totals are incomplete: unavailable prices use zero placeholders.")
        print("API costs are estimates.")
        tracker.print_summary()
        try:
            tracker.save_to_file()
        except (KeyboardInterrupt, EOFError):
            print("\nSession log not saved.")


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-steps", type=int, default=MAX_STEPS)
    parser.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max"],
                        default="medium")
    args = parser.parse_args()
    if args.max_steps < 1:
        parser.error("--max-steps must be at least 1")
    chat_with_skills(args.model, args.max_steps, args.effort)

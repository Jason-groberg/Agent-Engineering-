from openai import OpenAI
from dotenv import load_dotenv
import time
from litellm import completion, completion_cost
from pygments.lexers import q
import argparse
import os
import datetime
import json
from rich import print as rprint

#Global Settings
gbt = "gpt-5.6-luna"
load_dotenv()

def load_schema(schema_name):
    with open(schema_name, "r", encoding="utf-8") as f:
        return json.load(f)


def create_prompt_session():
    output_dir = "Past_Prompts"
    os.makedirs(output_dir, exist_ok=True)

    session_num = 1
    date = datetime.datetime.now().strftime("%Y-%m-%d")

    while True:
        filename = os.path.join(output_dir, f"prompt_session_{session_num}.txt")
        if not os.path.exists(filename):
            break
        session_num += 1

    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"Prompt Session {session_num} on {date}\n")

    return filename


def save_prompt(filename, prompt, prompt_num):
    with open(filename, "a", encoding="utf-8") as f:
        f.write(f"{prompt_num}. {prompt}\n")


def run_prompt(prompt, model=gbt,messages=None,  schema_file=None):
    if messages is None:
        messages = [{"role": "user", "content": prompt}]

    client = OpenAI()
    start = time.time()

    api_params = {
        "model": model,
        "messages": messages
    }

    if schema_file:
        schema= load_schema(schema_file)
        if schema:
            api_params["response_format"] = {
                "type": "json_schema",
                "json_schema": schema
            }
    response = client.chat.completions.create(**api_params)

    end = time.time()
    response_time = end - start
    usage = response.usage
    cost = completion_cost(completion_response=response, model=gbt)
    model_response = response.choices[0].message.content
    print(f"Usage Stats -> Response time: {response_time:.3f} seconds || Input Tokens: {usage.prompt_tokens} || Output Tokens: {usage.completion_tokens} || Total Tokens: {usage.total_tokens} || Cost: ${cost:.6f} || ")
    return model_response, cost


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run prompt app with optional schema support.")
    parser.add_argument("-f", "--file", type=str, help="File path to prompt from", required=False)
    parser.add_argument("-s", "--schema", type=str, help="Path to JSON schema file for structured output", required=False)
    args = parser.parse_args()

    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                prompt = f.read()
            response, cost = run_prompt(prompt, schema_file=args.schema)
            print(f"\nResponse:\n{response}")
        except FileNotFoundError:
            print(f"File not found: {args.file}")

    else:
        print("Enter 'q' to quit.")
        if args.schema:
            print(f"Mode: Structured Output (Schema: {args.schema})")
        else:
            print("Mode: Standard Text Completion")

        session_cost = 0
        prompts_used = 0
        prompt_num = 1

        session_file = create_prompt_session()
        print(f"Logging this session to: {session_file}")

        while True:
            prompt = input("\nEnter your prompt: ")

            if prompt.strip().lower() == "q":
                print(f"\nSession cost: ${session_cost:.6f}")
                print(f"Prompts used: {prompts_used}")
                with open(session_file, "a", encoding="utf-8") as f:
                    f.write(f"\nSession cost: ${session_cost:.6f}\nPrompts used: {prompts_used}\n")
                break

            save_prompt(session_file, prompt, prompt_num)
            prompt_num += 1

            print("\nThinking...")
            response, cost = run_prompt(prompt, schema_file=args.schema)
            print(f"\n{gbt}:\n")
            if args.schema:
                try:
                    parsed_response = json.loads(response)
                    formatted = json.dumps(parsed_response, indent=2)
                    rprint(formatted)
                except json.JSONDecodeError:
                    rprint(response)
            else:
                rprint(response)

            session_cost += cost
            prompts_used += 1
"""Track an existing local Codex conversation without making API calls.

Run from Chat_Files: python Codex_Usage_Tracking/codex_usage_tracker.py
Stop with Ctrl+C to name and save the report. Includes the whole session history.
Use --once to export an existing session, or --session PATH_OR_ID to select one.
Local Codex JSONL formats are internal and may change between releases.
"""

import datetime
import json
import math
import os
import time
from argparse import ArgumentParser
from pathlib import Path


TRACKING_DIR = Path(__file__).resolve().parent
PROJECT = TRACKING_DIR.parent
OUTPUT_DIR = PROJECT.parent / "Past_Prompts"
CODEX_DIR = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
PRICING_URL = "https://developers.openai.com/api/docs/pricing"
PRICING_DATE = "2026-10-10"
# Standard USD per million tokens: input, cached input, cache writes, output.
# The estimate uses Standard pricing regardless of the subscription's service tier.
PRICES = {
    "gpt-6.1-sol": (2.0, 0.10, 2.50, 10.0),
    "gpt-6-astra": (10.0, 1.0, 12.50, 50.0),
    "gpt-6-luna": (0.10, 0.01, 0.125, 0.50),
    "gpt-5.6-sol": (4.0, 0.40, 5.0, 20.0),
}
TOKEN_KEYS = (
    "input_tokens", "cached_input_tokens", "cache_write_input_tokens",
    "output_tokens", "reasoning_output_tokens", "total_tokens",
)


def read_events(session):
    events, malformed = [], 0
    with session.open("r", encoding="utf-8-sig") as f:
        for line in f:
            try:
                event = json.loads(line)
                if isinstance(event, dict):
                    events.append(event)
            except json.JSONDecodeError:
                # A writer may still be appending the final JSONL line.
                if line.endswith("\n"):
                    malformed += 1
    return events, malformed


def session_meta(session):
    with session.open("r", encoding="utf-8-sig") as f:
        for _ in range(20):
            line = f.readline()
            if not line:
                break
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "session_meta":
                return event.get("payload", {})
    return {}


def find_session(sessions_dir, workspace, selection=None):
    if selection and Path(selection).is_file():
        return Path(selection).resolve()
    candidates = sorted(sessions_dir.rglob("*.jsonl"),
                        key=lambda p: p.stat().st_mtime, reverse=True)
    for candidate in candidates:
        meta = session_meta(candidate)
        if selection:
            if selection == meta.get("id", meta.get("session_id")):
                return candidate
        elif meta.get("cwd") and Path(meta["cwd"]).resolve() == workspace.resolve():
            source = meta.get("source", "")
            if not isinstance(source, dict) or "subagent" not in source:
                return candidate
    raise ValueError("No matching Codex session. Use --session PATH_OR_ID or --workspace PATH.")


def message_text(content):
    if isinstance(content, str):
        return content
    parts = []
    for part in content or []:
        if isinstance(part, dict):
            if isinstance(part.get("text"), str):
                parts.append(part["text"])
            elif "image" in str(part.get("type", "")).lower():
                parts.append("[Image attachment]")
    return "\n".join(parts)


def normalize_usage(usage):
    result = {k: int(usage.get(k, 0) or 0) for k in TOKEN_KEYS}
    details = usage.get("input_tokens_details") or {}
    result["cached_input_tokens"] = int(usage.get("cached_input_tokens", details.get("cached_tokens", 0)) or 0)
    result["cache_write_input_tokens"] = int(usage.get("cache_write_input_tokens", details.get("cache_write_tokens", 0)) or 0)
    details = usage.get("output_tokens_details") or {}
    result["reasoning_output_tokens"] = int(usage.get("reasoning_output_tokens", details.get("reasoning_tokens", 0)) or 0)
    result["total_tokens"] = int(usage.get("total_tokens", result["input_tokens"] + result["output_tokens"]) or 0)
    return result


def estimate_cost(usage, model, prices, multiplier=1.0):
    rates = prices.get(model)
    if rates is None:
        return None
    input_rate, cached_rate, write_rate, output_rate = rates
    # Long-context premiums apply per request, not to cumulative session input.
    if usage["input_tokens"] > 272_000 and model in PRICES:
        input_rate, cached_rate, write_rate = (r * 2 for r in rates[:3])
        output_rate *= 1.5
    cached = usage["cached_input_tokens"]
    writes = usage["cache_write_input_tokens"]
    uncached = max(0, usage["input_tokens"] - cached - writes)
    return multiplier * (uncached * input_rate + cached * cached_rate
                         + writes * write_rate + usage["output_tokens"] * output_rate) / 1_000_000


def parse_session(session, prices=PRICES, multiplier=1.0):
    events, malformed = read_events(session)
    direct = any(e.get("type") == "token_usage_record" for e in events)
    item_messages = any(e.get("type") == "event_msg" and
                        (e.get("payload", {}).get("item") or {}).get("type") in
                        ("UserMessage", "userMessage") for e in events)
    user_events = any(e.get("payload", {}).get("type") == "user_message" for e in events)
    turns, by_id, requests, seen = [], {}, [], set()
    active, model, previous, meta = None, "unknown", {}, {}

    def get_turn(turn_id, timestamp):
        nonlocal active
        if turn_id not in by_id:
            by_id[turn_id] = {"turn_id": turn_id, "started": timestamp, "ended": None,
                              "prompts": [], "answer": "", "requests": [], "status": "in progress"}
            turns.append(by_id[turn_id])
        active = by_id[turn_id]
        return active

    for index, event in enumerate(events):
        payload = event.get("payload") or {}
        kind, timestamp = event.get("type"), event.get("timestamp", "")
        if kind == "session_meta":
            meta = payload
        elif kind == "turn_context":
            model = payload.get("model", model)
            get_turn(payload.get("turn_id", "unattributed"), timestamp)
        elif kind == "event_msg" and payload.get("type") == "task_started":
            get_turn(payload.get("turn_id", f"turn-{index}"), timestamp)
        elif kind == "event_msg" and payload.get("type") == "item_completed":
            item = payload.get("item") or {}
            turn = get_turn(payload.get("turn_id", "unattributed"), timestamp)
            if item.get("type") in ("UserMessage", "userMessage"):
                turn["prompts"].append(message_text(item.get("content")))
            elif item.get("type") in ("AgentMessage", "agentMessage") and item.get("phase") != "commentary":
                turn["answer"] = message_text(item.get("content", item.get("text", "")))
        elif kind == "event_msg" and payload.get("type") == "user_message" and not item_messages:
            turn = active or get_turn(f"turn-{index}", timestamp)
            turn["prompts"].append(message_text(payload.get("message", "")))
        elif kind == "response_item" and payload.get("type") == "message":
            turn = active or get_turn("unattributed", timestamp)
            if payload.get("role") == "user" and not item_messages and not user_events:
                text = message_text(payload.get("content"))
                if not text.lstrip().startswith(("<environment_context>", "<turn_aborted>")):
                    turn["prompts"].append(text)
            elif payload.get("role") == "assistant" and payload.get("phase") != "commentary":
                turn["answer"] = message_text(payload.get("content"))
        elif kind == "event_msg" and payload.get("type") in ("task_complete", "task_aborted"):
            turn = get_turn(payload.get("turn_id", active["turn_id"] if active else "unattributed"), timestamp)
            turn["ended"] = timestamp
            turn["status"] = "completed" if payload["type"] == "task_complete" else "interrupted"
            turn["answer"] = payload.get("last_agent_message") or turn["answer"]

        usage = None
        response_id = None
        if kind == "token_usage_record":
            response_id = payload.get("response_id", f"record-{index}")
            if response_id in seen:
                continue
            seen.add(response_id)
            usage = normalize_usage(payload.get("usage") or {})
            turn = get_turn(payload.get("turn_id", "unattributed"), timestamp)
        elif not direct and kind == "event_msg" and payload.get("type") == "token_count":
            info = payload.get("info") or {}
            if not info.get("total_token_usage"):
                continue
            cumulative = normalize_usage(info["total_token_usage"])
            if cumulative == previous:
                continue
            # Some older logs reset cumulative usage after compaction.
            reset = cumulative["total_tokens"] < previous.get("total_tokens", 0)
            usage = {k: max(0, cumulative[k] - (0 if reset else previous.get(k, 0))) for k in TOKEN_KEYS}
            previous = cumulative
            turn = active or get_turn("unattributed", timestamp)
        if usage is not None and any(usage.values()):
            request = {"timestamp": timestamp, "response_id": response_id,
                       "model": model, **usage, "cost": estimate_cost(usage, model, prices, multiplier)}
            turn["requests"].append(request)
            requests.append(request)
    return {"meta": meta, "turns": turns, "requests": requests, "malformed": malformed,
            "usage_source": "per-response records" if direct else "cumulative token-count deltas"}


def token_summary(requests):
    totals = {k: sum(r[k] for r in requests) for k in TOKEN_KEYS}
    cost = sum(r["cost"] for r in requests if r["cost"] is not None)
    unknown = sum(r["cost"] is None for r in requests)
    lines = [f"Model responses: {len(requests)}",
             f"Input Tokens: {totals['input_tokens']:,}",
             f"Cached Input Tokens (included in input): {totals['cached_input_tokens']:,}",
             f"Cache Write Tokens (included in input): {totals['cache_write_input_tokens']:,}",
             f"Output Tokens: {totals['output_tokens']:,}",
             f"Reasoning Tokens (included in output): {totals['reasoning_output_tokens']:,}",
             f"Total Tokens: {totals['total_tokens']:,}"]
    label = "Known-cost subtotal" if unknown else "Estimated API token cost"
    lines.append(f"{label}: ${cost:.6f}")
    if unknown:
        models = sorted({r["model"] for r in requests if r["cost"] is None})
        lines.append(f"Cost unavailable for {unknown} responses: {', '.join(models)}")
    return "\n".join(lines)


def duration(turn):
    if not turn["started"] or not turn["ended"]:
        return "unfinished"
    try:
        start = datetime.datetime.fromisoformat(turn["started"].replace("Z", "+00:00"))
        end = datetime.datetime.fromisoformat(turn["ended"].replace("Z", "+00:00"))
        return f"{(end - start).total_seconds():.2f}s"
    except ValueError:
        return "unknown"


def build_report(data, session, prices, multiplier):
    meta = data["meta"]
    lines = ["=== CODEX SESSION USAGE SUMMARY ===",
             f"Session: {meta.get('id', meta.get('session_id', session.stem))}",
             f"Workspace: {meta.get('cwd', 'unknown')}", f"Source log: {session}",
             f"Usage source: {data['usage_source']}",
             f"Conversation turns: {len(data['turns'])}", token_summary(data["requests"]),
             "", "=== API COST ASSUMPTIONS ===",
             "Hypothetical API token cost, not a ChatGPT subscription charge.",
             f"Built-in Standard rates checked {PRICING_DATE}: {PRICING_URL}",
             f"Rate multiplier: {multiplier:g} (Standard baseline = 1)",
             "Rates below are USD per 1M tokens: input / cached input / cache writes / output."]
    for model in sorted({r["model"] for r in data["requests"]}):
        rates = prices.get(model)
        lines.append(f"{model}: " + (" / ".join(f"${r:g}" for r in rates) if rates else "unavailable"))
    lines += ["Reasoning is already included in output; cached input is already included in input.",
              "Built-in models: requests over 272,000 input tokens use 2x input and 1.5x output rates.",
              "Excludes tool fees, regional premiums, and separately logged subagent sessions.",
              "Only usage available in this log is included; missing reasoning counts are reported as 0.",
              "Older cumulative-only logs may lack enough detail for exact per-request pricing."]
    if data["malformed"]:
        lines.append(f"Warning: skipped {data['malformed']} malformed complete log lines.")
    lines += ["", "=== CONVERSATION LOG ===", ""]
    for number, turn in enumerate(data["turns"], 1):
        lines += [f"--- Prompt {number} ---", f"Turn: {turn['turn_id']}",
                  f"Started: {turn['started']} | Status: {turn['status']} | Time Taken: {duration(turn)}",
                  token_summary(turn["requests"]), "", "User:",
                  "\n\n".join(turn["prompts"]) or "[Prompt unavailable in log]",
                  "", "AI:", turn["answer"] or "[No final response recorded]",
                  "", "Model response usage:"]
        for request in turn["requests"]:
            cost = f"${request['cost']:.6f}" if request["cost"] is not None else "unavailable"
            lines.append(f"{request['timestamp']} | {request['model']} | "
                         f"Input: {request['input_tokens']} | Cached: {request['cached_input_tokens']} | "
                         f"Cache writes: {request['cache_write_input_tokens']} | Output: {request['output_tokens']} | "
                         f"Reasoning: {request['reasoning_output_tokens']} | Total: {request['total_tokens']} | Cost: {cost}")
        lines.append("")
    return "\n".join(lines) + "\n"


def report_filename(name):
    name = name.strip() or datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    if name.lower().endswith(".txt"):
        name = name[:-4]
    if name.lower().startswith("codex_"):
        name = name[6:]
    if not name or name.endswith((".", " ")) or any(ord(c) < 32 or c in '<>:"/\\|?*' for c in name):
        raise ValueError("Enter a filename without folders or invalid filename characters.")
    return f"Codex_{name}.txt"


def save_report(report, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    while True:
        try:
            filename = report_filename(input("Session filename (Enter for automatic name): "))
            target = output_dir / filename
            # Exclusive creation prevents overwriting an earlier conversation.
            with target.open("x", encoding="utf-8") as f:
                f.write(report)
            print(f"Session history and usage saved to: {target}")
            return target
        except FileExistsError:
            print("That filename already exists. Please choose another.")
        except ValueError as exc:
            print(exc)


def load_prices(filename):
    prices = dict(PRICES)
    if filename:
        # Optional JSON: {"model-name": [input, cached_input, cache_write, output]}.
        overrides = json.loads(Path(filename).read_text(encoding="utf-8-sig"))
        for model, rates in overrides.items():
            if len(rates) != 4 or any(not isinstance(r, (int, float)) or not math.isfinite(r) or r < 0 for r in rates):
                raise ValueError(f"Invalid rates for {model}; provide four nonnegative USD rates per 1M tokens.")
            prices[model] = tuple(rates)
    return prices


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--session", help="Exact session ID or JSONL file path")
    parser.add_argument("--workspace", type=Path, default=PROJECT, help="Match the session working directory")
    parser.add_argument("--sessions-dir", type=Path, default=CODEX_DIR / "sessions")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--once", action="store_true", help="Read the session once, then ask for a filename")
    parser.add_argument("--poll", type=float, default=2.0, help="Watch interval in seconds")
    parser.add_argument("--prices", help="JSON file with model rate overrides")
    parser.add_argument("--rate-multiplier", type=float, default=1.0, help="Multiply Standard rates, e.g. 2 for Fast")
    args = parser.parse_args()
    if not math.isfinite(args.poll) or args.poll <= 0 or not math.isfinite(args.rate_multiplier) or args.rate_multiplier <= 0:
        parser.error("--poll and --rate-multiplier must be positive finite numbers")
    try:
        prices = load_prices(args.prices)
        session = find_session(args.sessions_dir, args.workspace, args.session)
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        parser.error(str(exc))
    print(f"Tracking: {session}")
    print("Includes existing history. Stays attached to this session across replies.")
    print("When finished chatting, press Ctrl+C here to name and save the report.")
    signature = None
    try:
        while True:
            stat = session.stat()
            current = (stat.st_size, stat.st_mtime_ns)
            if current != signature:
                data = parse_session(session, prices, args.rate_multiplier)
                print("\n--- Session Usage Summary ---")
                print(token_summary(data["requests"]))
                signature = current
            if args.once:
                break
            time.sleep(args.poll)
    except KeyboardInterrupt:
        print("\nTracking stopped.")
    # Re-read once at shutdown to pick up the latest flushed response usage.
    data = parse_session(session, prices, args.rate_multiplier)
    if not data["turns"] and not data["requests"]:
        print("No conversation or usage records found. Nothing to save.")
        return
    print("\n--- Final Session Usage Summary ---")
    print(token_summary(data["requests"]))
    try:
        save_report(build_report(data, session, prices, args.rate_multiplier), args.output_dir)
    except (EOFError, KeyboardInterrupt):
        print("\nReport not saved. Run again with --once to export the recorded session.")


if __name__ == "__main__":
    main()

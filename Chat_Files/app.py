from argparse import ArgumentParser
import time
import gradio as gr
from openai import OpenAI
from dotenv import load_dotenv
from litellm import completion_cost
from usage_tracker import UsageTracker

load_dotenv()

MODEL = "gpt-5.6-luna"
COIN = "\U0001FA99"
client = OpenAI()
EFFORTS=["none","minimal","medium","high"]
CHAT_KW = {"type": "messages"} if int(gr.__version__.split(".")[0]) < 6 else {}
SYSTEM = None
KEYS = ("input_tokens", "reasoning_tokens", "output_tokens", "total_tokens", "cost", "time_taken_sec")

def load_prompt(path):
    if not path.lower().endswith(".md"):
        raise SystemExit(f"System prompt must be a .md file: {path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise SystemExit(f"System prompt not found: {path}")


def usage_block(r, title):
    bar = "=" * 19
    lines = [bar, title, f"<- {r['input_tokens']:,}{COIN} input <-"]
    if r["reasoning_tokens"]:
        lines.append(f"-> {r['reasoning_tokens']:,}{COIN} thought ->")
    lines += [
        f"-> {r['output_tokens']:,}{COIN} output ->",
        f"cost: ${r['cost']:.6f} | {r['time_taken_sec']:.1f}s",
        bar,
    ]
    return "\n".join(lines)


def usage_md(records):
    if not records:
        return "```\nNo turns yet.\n```"
    tot = {k: sum(r[k] for r in records) for k in KEYS}
    return (
        "```\n"
        + usage_block(records[-1], "Last turn")
        + "\n\n"
        + usage_block(tot, f"Session total ({len(records)} turns)")
        + "\n```"
    )


def respond(user_msg, chat, api_history, records, effort):
    if not user_msg.strip():
        yield user_msg, chat, gr.skip(), usage_md(records), api_history, records
        return

    chat = chat + [{"role": "user", "content": user_msg},
                   {"role": "assistant", "content": ""}]
    pending = api_history + [{"role": "user", "content": user_msg}]
    thinking, answer, final = "", "", None

    yield "", chat, "_Thinking…_", usage_md(records), api_history, records

    start = time.time()
    try:
        kwargs = dict(model=MODEL, input=pending, stream=True)
        if effort == "none":
            kwargs["reasoning"] = {"effort": "none"}
        else:
            kwargs["reasoning"] = {"effort": effort, "summary": "auto"}
        if SYSTEM:
            kwargs["instructions"] = SYSTEM
        stream = client.responses.create(**kwargs)
        for event in stream:
            if event.type == "response.reasoning_summary_part.added" and thinking:
                thinking += "\n\n"
            elif event.type == "response.reasoning_summary_text.delta":
                thinking += event.delta
            elif event.type == "response.output_text.delta":
                answer += event.delta
                chat[-1]["content"] = answer
            elif event.type == "response.completed":
                final = event.response
            else:
                continue
            yield "", chat, thinking or "_Thinking…_", usage_md(records), api_history, records
    except Exception as e:
        chat[-1]["content"] = f"⚠️ Error: {e}"
        yield user_msg, chat, "_Error — see chat._", usage_md(records), api_history, records
        return

    total_time = time.time() - start

    # Carry reasoning + message items forward
    api_history = pending + [item.model_dump(exclude_none=True) for item in final.output]

    usage = final.usage
    try:
        cost = completion_cost(completion_response=final)
    except Exception:
        cost = 0.0

    records = records + [{
        "prompt_text": user_msg,
        "input_tokens": usage.input_tokens,
        "reasoning_tokens": usage.output_tokens_details.reasoning_tokens,
        "output_tokens": usage.output_tokens,
        "total_tokens": usage.total_tokens,
        "time_taken_sec": total_time,
        "cost": cost,
    }]

    if effort == "none":
        reasoning_text = "_Reasoning off._"
    else:
        reasoning_text = thinking or "_No reasoning summary this turn._"

    yield ("", chat, reasoning_text, usage_md(records), api_history, records)


def save_usage(records):
    if not records:
        return "Nothing to save."
    tracker = UsageTracker()
    for r in records:
        tracker.add_record(r)
    tracker.print_summary()
    tracker.save_to_file()
    return f"Saved {len(records)} turns."


def reset():
    return [], "_Reasoning summary appears here._", usage_md([]), [], [], ""


def build_app(default_effort):
    with gr.Blocks(title=f"{MODEL} chat") as demo:
        api_history = gr.State([])
        records = gr.State([])

        gr.Markdown(f"## {MODEL}")
        with gr.Row():
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(height=560, label="Chat", **CHAT_KW)
                msg = gr.Textbox(placeholder="Message…", show_label=False, autofocus=True)
                with gr.Row():
                    send = gr.Button("Send", variant="primary")
                    clear = gr.Button("Clear")
            with gr.Column(scale=2):
                effort = gr.Dropdown(EFFORTS, value=default_effort, label="Reasoning effort")
                gr.Markdown("###  Reasoning")
                reasoning_box = gr.Markdown("_Reasoning summary appears here._", height=300)
                gr.Markdown("###  Usage")
                usage_box = gr.Markdown(usage_md([]))
                save_btn = gr.Button("Save usage log")
                save_status = gr.Markdown()

        io_in = [msg, chatbot, api_history, records, effort]
        io_out = [msg, chatbot, reasoning_box, usage_box, api_history, records]
        msg.submit(respond, io_in, io_out)
        send.click(respond, io_in, io_out)
        clear.click(reset, None, [chatbot, reasoning_box, usage_box, api_history, records, save_status])
        save_btn.click(save_usage, records, save_status)

    return demo



if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-r", "--reasoning", default="none", choices=EFFORTS)
    parser.add_argument("-f", "--file", default=None, help="Path to .md system prompt")
    parser.add_argument("--share", action="store_true", help="Public gradio.live link")
    args = parser.parse_args()

    if args.file:
        SYSTEM = load_prompt(args.file)
        print(f"System prompt: {args.file}")
    else:
        print("System prompt: none")

    build_app(args.reasoning).launch(share=args.share)
from argparse import ArgumentParser
from pygments.lexers import q
from openai import OpenAI
from dotenv import load_dotenv
import time
from litellm import completion_cost
from usage_tracker import UsageTracker
import app as gr

load_dotenv()

gbt = "gpt-5.6-luna"
coin = "\U0001FA99"
with open("System_Prompts/Game.md", "r", encoding="utf-8") as f:
    system = f.read()

def reasoning_chat(reasoning="medium",  ):
    client = OpenAI()
    tracker = UsageTracker()
    history = []

    while True:

        user_input = input("User: ")
        if not user_input:
            break

        history.append({"role" : "user", "content": user_input})
        start = time.time()
        response = client.responses.create(
            model=gbt,
            reasoning={"effort": reasoning, "summary":"auto"},
            instructions=system,
            input=history
        )
        total_time = time.time() - start

        history += response.output

        usage = response.usage
        input_tokens = usage.input_tokens
        output_tokens = usage.output_tokens
        reasoning_tokens = usage.output_tokens_details.reasoning_tokens
        cost = completion_cost(completion_response=response)

        output = response.output_text
        thoughts = []
        for item in response.output:
            if item.type == "reasoning":
                for s in item.summary:
                    thoughts.append(s.text)
        thinking = "\n".join(thoughts)

        if thinking:
            print(f"[thinking]\n{thinking}\n")
        print(f"{gbt}: {response.output_text}")
        history.append({"role": "assistant", "content": output})

        record = {
            "input_tokens": input_tokens,
            "reasoning_tokens": reasoning_tokens,
            "output_tokens": output_tokens,
            "total_tokens": usage.total_tokens,
            "time_taken_sec": total_time,
            "cost": cost
        }
        tracker.add_record(record)

    tracker.print_summary()
    tracker.save_to_file()

if __name__ == "__main__":
    arg_parser = ArgumentParser()
    arg_parser.add_argument("-r", "--reasoning", default="medium", type=str, help="Reasoning")
    arg_parser.add_argument("-f", "--file", default="System_Prompts/Game.md", help="File")
    args = arg_parser.parse_args()
    reasoning_chat(args.reasoning)


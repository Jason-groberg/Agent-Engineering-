from pygments.lexers import q
from openai import OpenAI
from dotenv import load_dotenv
import time
from litellm import completion, completion_cost
from pygments.lexers import q
from usage_tracker import UsageTracker
load_dotenv()

gbt = "gpt-5.6-luna"



coin = "\U0001FA99"
with open("System_Prompts/Game.md", "r", encoding="utf-8") as f:
    system = f.read()

def chat():
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
            reasoning={"effort": "medium"},
            instructions=system,
            input=history
        )

        end = time.time()
        total_time = end - start
        usage = response.usage
        input_tokens = usage.input_tokens
        output_tokens = usage.output_tokens
        reasoning_tokens = usage.output_tokens_details.reasoning_tokens
        cost = completion_cost(completion_response=response)
        output = response.output_text

        if reasoning_tokens == 0:
            print(f"{gbt}: {output}\n{"="*18}\n<- {input_tokens}{coin} inputed <-\n-> {output_tokens}{coin} output ->\ncost: ${cost:.6f}\n{"="*18}\n")
        else:
            print(
                f"{gbt}: {output}\n{"="*19}\n<- {input_tokens}{coin} inputed <-\n-> {reasoning_tokens}{coin} thought <-\n-> {output_tokens}{coin} output ->\ncost: ${cost:.6f}\n{"="*19}\n")

        # print(f"Chat: {output}\n")
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
    chat()

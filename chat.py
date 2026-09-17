from pygments.lexers import q
from openai import OpenAI
from dotenv import load_dotenv
import time
from litellm import completion, completion_cost
from openai.resources.responses import input_tokens
from pygments.lexers import q
import argparse
import os
import datetime
load_dotenv()

gbt = "gpt-5.6-luna"

class UsageTracker(dict):
    def __init__(self):
        super().__init__()
        self["records"] = []
        self["total_requests"] = 0
        self["total_time_sec"] = 0.0
        self["total_input_tokens"] = 0
        self["total_reasoning_tokens"] = 0
        self["total_output_tokens"] = 0
        self["grand_total_tokens"] = 0
        self["total_cost"] = 0.0

    def add_record(self, record: dict):
        self["records"].append(record)
        self["total_requests"] += 1
        self["total_time_sec"] += record.get("time_taken_sec", 0)
        self["total_input_tokens"] += record.get("input_tokens", 0)
        self["total_reasoning_tokens"] += record.get("reasoning_tokens", 0)
        self["total_output_tokens"] += record.get("output_tokens", 0)
        self["grand_total_tokens"] += record.get("total_tokens", 0)
        self["total_cost"] += record.get("cost", 0)

    def print_summary(self):
        if not self["records"]:
            print("\nNo requests made this session.")
            return
            
        print("\n--- Session Usage Summary ---")
        print(f"Total Requests: {self['total_requests']}")
        print(f"Total Time: {self['total_time_sec']:.2f}s")
        print(f"Total Input Tokens: {self['total_input_tokens']}")
        print(f"Total Reasoning Tokens: {self['total_reasoning_tokens']}")
        print(f"Total Output Tokens: {self['total_output_tokens']}")
        print(f"Grand Total Tokens: {self['grand_total_tokens']}")
        print(f"Total Cost: ${self['total_cost']:.6f}")
        print("-----------------------------\n")

    def save_to_file(self):
        if not self["records"]:
            return

        os.makedirs("Past_Prompts", exist_ok=True)
        date_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = os.path.join("Past_Prompts", f"chat_session_{date_str}.txt")
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write("=== SESSION USAGE SUMMARY ===\n")
            f.write(f"Total Requests: {self['total_requests']}\n")
            f.write(f"Total Time: {self['total_time_sec']:.2f}s\n")
            f.write(f"Total Input Tokens: {self['total_input_tokens']}\n")
            f.write(f"Total Reasoning Tokens: {self['total_reasoning_tokens']}\n")
            f.write(f"Total Output Tokens: {self['total_output_tokens']}\n")
            f.write(f"Grand Total Tokens: {self['grand_total_tokens']}\n")
            f.write(f"Total Cost: ${self['total_cost']:.6f}\n")
            f.write("=============================\n\n")
            
            # Write Individual Records
            f.write("=== CONVERSATION LOG ===\n\n")
            for i, record in enumerate(self["records"], 1):
                f.write(f"--- Prompt {i} ---\n")
                f.write(f"Time Taken: {record.get('time_taken_sec', 0):.2f}s | ")
                f.write(f"Cost: ${record.get('cost', 0):.6f} | ")
                f.write(f"Total Tokens: {record.get('total_tokens', 0)}\n")
                f.write(f"Input: {record.get('input_tokens', 0)} | Output: {record.get('output_tokens', 0)} | Reasoning: {record.get('reasoning_tokens', 0)}\n\n")
                
                f.write(f"User: {record.get('prompt_text', '')}\n\n")
                #f.write(f"AI: {record.get('response_text', '')}\n\n")
        
        print(f"\nSession history and usage successfully saved to: {filename}")

gbt = "gpt-5.6-luna"

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
        print(f"AI: {output}\n")
        
        # Append the AI's response to your history list so it remembers it for the next loop!
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
        print(f"{gbt}: {output}\ncost: ${cost:.6f}")


    tracker.print_summary()
    tracker.save_to_file()

if __name__ == "__main__":
    chat()

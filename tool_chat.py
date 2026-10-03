from argparse import ArgumentParser
import json
import time
from dotenv import load_dotenv
from openai import OpenAI
from Tools.agentic_tools import shell, read, write, edit, tools as custom_tools
from usage_tracker import UsageTracker

load_dotenv()

gbt = "gpt-5.6-sol"
coin = "\U0001FA99"
tools = custom_tools
available_tools = {
   "shell": shell,
    "read": read,
    "write": write,
    "edit": edit,
}

def chat_with_tools():
    client = OpenAI()
    history = []
    tracker = UsageTracker()

    while True:
        user_input = input("User: ")
        if not user_input:
            break

        history.append({"role": "user", "content": user_input})
        for _ in range(10):
            start = time.time()
            response = client.responses.create(
                model=gbt,
                input = history,
                instructions="You are replying in a plain-text-terminal, format your answers properly so they render correctly in the terminal.",
                reasoning = {"effort" : "medium"},
                tools = tools,
            )
            tracker.track(response, time.time() - start, user_input)

            history += response.output

            tool_calls = [item for item in response.output if item.type == "function_call"]
            if not tool_calls:
                print(response.output_text)
                break

            for call in tool_calls:
                args = json.loads(call.arguments or "{}")
                print(f"Function: {call.name} with args {args}")

                try :
                    tool_result = available_tools[call.name](**args)
                except Exception as e:
                    tool_result = {"error": str(e)}

                history.append({
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(tool_result),
                })
        else:
            print(f"Stopped: exceeded Tool Call Limit: 10 ")

    tracker.print_summary()
    tracker.save_to_file()


if __name__ == "__main__":
    chat_with_tools()
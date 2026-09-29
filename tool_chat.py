from argparse import ArgumentParser
import json
import time
from dotenv import load_dotenv
from openai import OpenAI
from Tools.custom_tools import get_weather, mod_exp, get_url_contents, get_conference_speakers, fermat, generate_large_prime, tools as custom_tools
from usage_tracker import UsageTracker

load_dotenv()

gbt = "gpt-5.6-luna"
coin = "\U0001FA99"
tools = custom_tools
available_tools = {
    "get_weather": get_weather,
    "mod_exp": mod_exp,
    "get_url_contents": get_url_contents,
    "get_conference_speakers": get_conference_speakers,
    "fermat": fermat,
    "generate_large_prime": generate_large_prime,
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
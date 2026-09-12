from openai import OpenAI
from dotenv import load_dotenv
import time
load_dotenv()
from litellm import completion, completion_cost
from pygments.lexers import q
import argparse
import os
import datetime

def run_prompt(prompt):
    # instructions = "respond in concise sentences that get to the point, and don't repeat the same information twice. Keep responses under 3 paragraphs."
    # prompt += instructions
    client = OpenAI()
    start = time.time()
    response = client.chat.completions.create(
        model="gpt-5.6-sol",
        messages=[{"role": "user", "content": prompt}]
    )
    end = time.time()
    response_time = end - start
    usage = response.usage
    cost = completion_cost(completion_response=response, model="gpt-5.6-luna")
    print(f"Usage Stats -> Response time: {response_time:.3f} seconds || Input Tokens: {usage.prompt_tokens} || Output Tokens: {usage.completion_tokens} || Total Tokens: {usage.total_tokens} || Cost: ${cost:.6f} || ")
    return response.choices[0].message.content, cost

def create_prompt_session():
    session_num = 1
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    while os.path.exists(f"prompt_session_{session_num}.txt"):
        session_num += 1
    with open(f"prompt_session_{session_num}.txt", "w", encoding="utf-8") as f:
        f.write(f"Prompt Session {session_num} on {date}\n")
    return f"prompt_session_{session_num}.txt"

def save_prompt(filename, prompt, prompt_num):
    with open(filename, "a", encoding="utf-8") as f:
        f.write(f"{prompt_num}. {prompt}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Select a File as prompt input, or run from command line")
    parser.add_argument("-f", "--file", type=str, help="File path to prompt from", required=False)
    args = parser.parse_args()
    
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                prompt = f.read()
            response, cost = run_prompt(prompt)
            print(f"\nResponse Usage: {response}")
        except FileNotFoundError:
            print(f"File not found: {args.file}")

    else:
        print("enter q to quit")
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
                    f.write(f"\nSession cost: ${session_cost:.6f}")
                    f.write(f"\nPrompts used: {prompts_used}")
                break

            save_prompt(session_file, prompt, prompt_num)
            prompt_num += 1
            response, cost = run_prompt(prompt)
            print("\nThinking...")
            print(f"\nChat: {response}")

            session_cost += cost
            prompts_used += 1

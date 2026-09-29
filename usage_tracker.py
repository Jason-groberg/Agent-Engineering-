import os
import datetime
from litellm import cost_per_token

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
        while True:
            name = input(
                "Session filename (Enter for automatic name): "
            ).strip()

            if not name:
                name = f"chat_session_{date_str}"

            # Require a filename rather than a path.
            if any(char in name for char in '<>:"/\\|?*') or name.endswith("."):
                print("Please enter a valid filename without folders.")
                continue

            if not name.lower().endswith(".txt"):
                name += ".txt"

            filename = os.path.join("Past_Prompts", name)

            if os.path.exists(filename):
                print("That filename already exists. Please choose another.")
                continue

            break

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
                f.write(
                    f"Input: {record.get('input_tokens', 0)} | Output: {record.get('output_tokens', 0)} | Reasoning: {record.get('reasoning_tokens', 0)}\n\n")

                f.write(f"User: {record.get('prompt_text', '')}\n\n")
                f.write(f"AI: {record.get('response_text', '')}\n\n")

        print(f"\nSession history and usage successfully saved to: {filename}")

    def track(self, response, time_taken: float, prompt_text: str = ""):
        u = response.usage
        reasoning = getattr(u.output_tokens_details, "reasoning_tokens", 0) or 0

        try:
            in_cost, out_cost = cost_per_token(
                model=response.model,
                prompt_tokens=u.input_tokens,
                completion_tokens=u.output_tokens,  # reasoning is billed inside output
            )
            cost = in_cost + out_cost
        except Exception:
            cost = 0.0  # model not in litellm's price list

        tool_calls = [i.name for i in response.output if i.type == "function_call"]

        self.add_record({
            "time_taken_sec": time_taken,
            "input_tokens": u.input_tokens,
            "output_tokens": u.output_tokens,
            "reasoning_tokens": reasoning,
            "total_tokens": u.total_tokens,
            "cost": cost,
            "prompt_text": prompt_text,
            "response_text": response.output_text or f"[tool calls: {', '.join(tool_calls)}]",
        })

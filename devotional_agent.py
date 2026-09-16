import os
from completion import run_prompt

def analyze_devotional():
    devo_path = "devo2.txt"
    output_path = "Devotional_Agent3.md"

    with open(devo_path, "r", encoding="utf-8") as f:
        devo_text = f.read()

    custom_criteria = "Metaphors, analogies, and real-life stories used by the speaker to illustrate their points."

    prompt = f"""
You are an expert at analyzing and summarizing religious speeches and devotionals. 
Please read the following devotional transcript and provide a structured analysis.

Format your response in Markdown using exactly the following sections:

# Devotional Summary
[Provide a concise but comprehensive summary of the speech here, no more than 3 paragraphs.]

## Key Take-aways
[Use bullet points to list the 3-5 main actionable take-aways for the audience]

## Heart of the Message (Important to the Speaker)
[Identify and explain the core messages that the speaker seemed most passionate or emphatic about]

## Interesting Content: Metaphors and Stories
[Identify and extract content that meets this criteria: {custom_criteria}]

---

Here is the devotional text:
{devo_text}
"""
    
    print("Sending text to the LLM for analysis...")
    response, cost = run_prompt(prompt)
    print(f"Writing analysis to {output_path}...")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(response)
        
    print(f"The output has been saved to {output_path}")

if __name__ == "__main__":
    analyze_devotional()

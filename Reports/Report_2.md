**Report 2a**
- 

1. First I refactored my basic app.py to add more functionality and use cases. 
    - Global settings section implemented to easily change variables like the model, role, and prompt.
    - Refactored project structure to have previous prompt sessions save in their own directory
    - Added new directory for schema outputs, command line flag -s to call app.py with a predefefined schema, and functions to automically load and print the structured output cleanly to the terminal. 
    - Json schema is instered into the client when the -s flag is used automatically.

2. I choose to build a JSON schema which give strcutured output for mathematical questions, specifically explaining Proofs, and Theorems. 
    - I created the schema ProofSchema.json which returns structured explanations of a proof of theorem. 
    - The Schema outlines explaining the intuition first, any prerequisites needed to understand the proof, the premises of the proof, then a number list of steps, each step includes a number, statement, justification, and example. Then the conclusion of the proof.
    - I also set the strict value to true so that ChatGPT will not return anything else than the schema.
    - This schema improved the outputs greatly, mostly because the structure of the output was easier to follow and was consitent. 
    - Using just the simple completion app I compared responses explaining Cantors Diagonilzation proof. 
      - The simple completion app was able to generate a logical explanition, but it was very long and hard to follow. 
      - The Schema was able to generate the same explanition, but it was better compacted into steps and many more examples which where explained at each step. 
      - In the future I could see how this will help in an Agent, as having the first reponse structured so well, will allow tools to be used to verify the truth of every step, and allow the user to question exact areas of an explanation
    -Some other areas I explored were different libraries for printing json to the terminal, for ease of use. 
   -Writing system prompts for Math related inquiries, these could potentially be used in the future to devolop a full agent. 
3. I completed the Devotional Agent Summizer, in the file devtion_agent.py file.
   - This agent uses my built completions.py file to call ChatGPT with the agent prompt, custom instructions to identify content that meets what it is interesting to myself
   - The agent takes a .txt input and returns a structured markdown output, with a 3 paragraph summary of the overall talk, then bulleted points for messages that the speaker thought was important, and final section which includes sections that relate the custom intructions. 
   - The agent is able to identify the most important sections of the talk, and cite key passages and sciptures used
4. Testing with different models on the same input, sol was almost 10x as expensive than Luna, but produced a Similiar summary. 
   - Smaller models like gpt4o was faster, but produced a much shorter and less accruate summary, than models like Luna and Sol.
   - The best performer considering cost was Luna, which consistently cost the least, and its summaries were accurate and robust.

5. What I learned/Challenges/Hours
   - I learned that JSON output schemas can be incredibly useful for one-shot completions, espiecially for structured math proofs, as typical the AI models will add extra information, or explain similar proofs or theorems in completely different ways. 
   - I learned that inputing large amounts of text, especially into the stronger models becomes expensive quickly, well smaller models like Luna, perform just as well at a fraction of the price. 
   - Basic agent engineering and connecting different agents to the same completion.py file 
   - One obstacle I faced was creating the json schema correctly, and researching which feilds to include and which not to, as well as how they effect the structured output. 
   - I spent a total of 4 hours on this homework.


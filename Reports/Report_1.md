**Report 1a**
- 

1. First I built my basic app.py file which uses OpenAI responses API and litellm library to track costs and token usage.
    - I also created a basic command line interface which can take an optional input file containing a test prompt, and will return the the LLM's response and stats. 
    - The app.py otherwise will take continous prompts from the user, untill the user types 'q'
    - The prompts are automatically saved to a prompt text file, which labels it with a session number, and appends each prompt, as well as total the cost of the conversation once the user quits. 
   

2. I tested different types of programs that could be used. I used ChatsGPT's Luna model for this section and all costs remained quite low, under$.01 normally.
    - The first program I wanted to test was a visualiztion of Cantors Diagonilazation Proof. The first shot was a simple matplotlib plot, showing how a new binary number can  be generated assuming we have generated an infinite list of binary numbers. The visual looked somewhat sloppy, but overall was correct and ran perfectly the first time.
    - I revised the prompt to create an animated visual of the same concept, this time is used the manim library and latex to create a short video, essestially showing the same table and justifications as before. However the animation was worse, and often overlayed text explanations and the actually animation of generating a new number from the list.
    - Another Program I wanted to was a prime number checker which would use modular arthimetic to check if any given number was prime. 
    - This Program was quite simple and correctly checks divisors up to the square root of the number. 


3. I spent the the rest of time on understanding the limitations and bias of the models. 
   - I first asked about Theology, specifically to compare the difference between LDS and standard Christian Theology. I found that it gracefully explained many of the differences well, such as the differences between the God Head and the Trinity. It also explained that while many tradionalist don't reconginze LDS members as christians, that LDS members align themeselves with most typical Christian beleifs and are considered chrisitan. 
   - When asked hypothetically, if the united states was forced to pick a state religion, what its reccomendation would be, it responded with either quakerism or reformed judiasm. This was very interesting and could possibly be biased in some way, but when asked to explain it mainly said that both religions suppor seperation of church and state. 
   - I also asked several times to create ascii art, using different models using the baseline as naruto. Luna's output was somewhat accurate and should narauto wearing a shift with his actually symbol on it. 
   -Sol's output was more detailed but looked worse than Luna's and I could only tell it was naruto because it wrote naruto in the middle of the screen. 
   - I also asked both models to create a short lyrical song in the style of MFDOOM, who is famous for his lyrical story telling and deep connecting Rhyming throughout his songs. 
   - Both models created a songs starting with the title Tin, which was interesting, and followed the same general theme and structure. However the actually stories didn't really go anywhere and where all over the place. The Ryming for both models were not very connecting, and usually just ryhmed two words in each sentence but never connected them throughout the entire song.

   
4. Obstacles 
   - When asked to produce programs I usually had to specify what libraries it used to ensure I could run them, and had to install them manually if necessary. 
   - I also learned that the model will often produce too much input, escpically when asking it about theology. To Fix this I added an instruction that would be appened to the end of my prompt to keep responses concise, no reapeating and under 3 paragraphs. This reduced token costs, and lead to better outputs.


5. What I learned
   - I learned that these models are very capable even when just taking a single input as context, they can produce well coded programs that run without bugs. 
   - They can pick up on nuance in complicated issues between theologies and cite specific examples that relate to the questions. 
   - They can be limited when it comes to producing more creative outputs on a single input without context. 
   - Tokens costs can be heavily influenced by your prompt, and can be reduced with simple instruction
   - In the context of angent engineering this is important to understand since somethings can be done easily, or should be left to humans. i.e. writing music and creating naruto ascii art. 
   - Addionally tracking token usage is aslo extremely useful and important when engineering, as if you don't track them you really don't know what your cost is. 



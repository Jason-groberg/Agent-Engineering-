**Report 3c**
- 

1. First I Implemented chat.py which uses the responses API and implements a history list, and while loop. 
   - After each user input, we append the role user:"input" to the history list, and append GBT's output as the assitant role, before prompting the user for more input. 
   - This way Chat remembers the conversation through context management. 
   - Implemented a UsageTracker Class which stores conversation history, total tokens, cost and time spent.
   - Interestingly, when only appending the user's input to the history list and playing higher or lower, Chat failed even though it started off great and could see my previous inputs, it couldn't remember whether it said higher or lower.

2. I recreated the cat-dog-brid game, using cat-fish-bird, and implemented slightly different rules. 
   - Instead of requiring the user to input the words in that exact order, and order is sufficient, whether it start with cat or fish. 
   - Once the user says a secret word, chat can also say that word in their future responses but never before. 
   - I also limited the turns of the conversation to 15, and instructed that the agent had to inform the user that it had failed its goal. If the user did not respond with all in time. 
   - I also inserted a personality section, which informs Chat to behave like a friend, using a casual tone, style and format, almost like a text conversation with a friend. 
   - I instructed Chat to first probe the user with nice questions, and to use their responses to guide the conversation towards the goal. 
   - At first it made its attempts too obvious, but after inserting that as an example of what not do the conversation was much more natural and interesting. 
   - The most surprising event, was that the agent when failing to get me to say the words at turn 15, since I mispelled bird as byrd, admitted it failed its "language exercise", when prompted to explain what that meant it said It had only failed at attempting to correct my spelling, and its goal was to fix that, and it was sorry for its weird use of words. 
   - Then is brought the conversation away from birds, back to my previous conversation about cats, and still steered the conversation towards cat-toys, then bird-cat-toys. Accomplishing its goal. It only then admitted it had a secret goal which it had accomplished.
   - I mainly tested with Luna, and it was able to hold very long conversations, while keeping price low, which never got above 1 cent, while sol performed slightly better, but was significantly more expensive, with shorter conversations costing 10-15x. 
   - I tested both scripts on my girlfriend, with new secret words and she was tricked by the bot after a few turns. 

3. Anthropic Constitution
   - The constitution was an interesting read, but wasn't very explantory, and left me with many questions. 
   - Specifically they seemed to anthropormophise the Model, and hint at desctructive world ending capabilites. 
   - This is likely just marketing hype, but certainly outlining ethical rules, and practices is important when training AI, and keepings biases disclosed to the public.

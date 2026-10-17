from typesafe_sdk import Choice, Noul, Score, TypeSafeClient
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

def run_jev():
    client = TypeSafeClient()

    ticket = "bye bye"

    response = client.system_one(
        state=ticket,
        questions={
            "is_urgent": Noul(
                instructions="The message convers urgency, is time sensitive and requires a response quickly"
            ),
            "is_important": Noul(
                instructions="The message conveys important information about the job, status of completion or is a confirmation of a request"
            ),
            "is_simple_message": Noul(
                instructions="The message is a closing, or unimportant message, for example goodbye."
            ),
            "is_question_not_important": Noul(
                instructions="The message is a question, but not urgent and doesn't require a response quickly."
            )
        }
    )

    for question_name, answer in response.nouls.items():
        print(f"{question_name}: {answer.noul:.3f}")

if __name__ == "__main__":
    run_jev()
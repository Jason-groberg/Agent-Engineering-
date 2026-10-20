"""Search math expressions using embeddings; answer labels are for comparison only."""

import asyncio
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from openai import AsyncOpenAI

from embedding_demo import cosine_scores, embed


def load_statements(directory: Path) -> tuple[list[str], list[str]]:
    expressions = (directory / "math_expressions.txt").read_text(encoding="utf-8").splitlines()
    answers = (directory / "math_answers.txt").read_text(encoding="utf-8").splitlines()
    if not expressions or len(expressions) != len(answers):
        raise ValueError("Expression and answer files must have the same nonzero number of lines")
    if any(not expression.strip() for expression in expressions):
        raise ValueError("Expressions must not contain blank lines")
    if any(answer not in {"True", "False"} for answer in answers):
        raise ValueError("Each answer must be exactly True or False")
    return expressions, answers


def search(query_vector: np.ndarray, vectors: np.ndarray,
           threshold: float = 0.3) -> list[tuple[int, float]]:
    scores = cosine_scores(query_vector, vectors)
    return [(int(index), float(scores[index]))
            for index in np.argsort(-scores, kind="stable") if scores[index] > threshold]


async def main() -> None:
    directory = Path(__file__).resolve().parent
    expressions, answers = load_statements(directory)
    load_dotenv(directory.parent / ".env")
    query = input("Search (e.g. true statement; blank to quit): ").strip()
    if not query:
        return
    async with AsyncOpenAI() as client:
        vectors = await embed(client, expressions)
        while query:
            query_vector = (await embed(client, [query]))[0]
            matches = search(query_vector, vectors)
            print("\nCosine similarity | Line | Answer | Expression")
            for index, score in matches:
                print(f"{score:.4f} | {index + 1} | {answers[index]} | {expressions[index]}")
            if not matches:
                print("No matches above 0.3 similarity.")
            true_count = sum(answers[index] == "True" for index, _ in matches)
            print(f"Total returned: {len(matches)} | True: {true_count} | False: {len(matches) - true_count}")
            query = input("\nSearch (blank to quit): ").strip()


if __name__ == "__main__":
    asyncio.run(main())

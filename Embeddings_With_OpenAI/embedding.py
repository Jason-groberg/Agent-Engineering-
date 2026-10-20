"""Explore OpenAI embeddings with similarity and 3D vector plots."""

import asyncio
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from dotenv import load_dotenv
from openai import AsyncOpenAI


async def embed(client: AsyncOpenAI, texts: list[str]) -> np.ndarray:
    response = await client.embeddings.create(input=texts, model="text-embedding-3-small")
    return np.array([item.embedding for item in response.data])


def cosine_scores(query: np.ndarray, vectors: np.ndarray) -> np.ndarray:
    return vectors @ query / (np.linalg.norm(vectors, axis=1) * np.linalg.norm(query))


def get_matches(query: np.ndarray, words: list[str], vectors: np.ndarray,
                threshold: float = 0.6) -> list[str]:
    return [word for word, score in zip(words, cosine_scores(query, vectors))
            if score > threshold]


def plot_similarities(query: str, query_vector: np.ndarray, words: list[str],
                      vectors: np.ndarray) -> None:
    fig, ax = plt.subplots()
    ax.bar(words, cosine_scores(query_vector, vectors))
    ax.set_title(f"Embedding similarity to {query}")
    ax.set_ylabel("Cosine similarity")
    ax.tick_params(axis="x", labelrotation=45)
    fig.tight_layout()


def project_3d(vectors: np.ndarray) -> np.ndarray:
    # shortcut: two vectors span at most two dimensions, add more words for depth.
    axes = np.linalg.svd(vectors, full_matrices=False)[2][:3].T
    coordinates = vectors @ axes
    return np.pad(coordinates, ((0, 0), (0, 3 - coordinates.shape[1])))


def plot_vectors_3d(words: list[str], vectors: np.ndarray) -> None:
    if vectors.ndim != 2 or len(words) != len(vectors) or len(words) < 2:
        raise ValueError("Provide at least two words and one embedding per word")
    coordinates = project_3d(vectors)
    colors = plt.cm.hsv(np.linspace(0, 1, len(words), endpoint=False))
    fig = plt.figure()
    ax = fig.add_subplot(projection="3d")
    for word, (x, y, z), color in zip(words, coordinates, colors):
        ax.quiver(0, 0, 0, x, y, z, color=color, arrow_length_ratio=0.12)
        ax.scatter(x, y, z, color=color, label=word)
    limit = max(np.abs(coordinates).max() * 1.1, 0.01)
    ax.set(xlim=(-limit, limit), ylim=(-limit, limit), zlim=(-limit, limit),
           xlabel="X", ylabel="Y", zlabel="Z",
           title="Embedding vectors projected into 3D")
    ax.set_box_aspect((1, 1, 1))
    ax.legend(title="Embedded words")
    fig.tight_layout()


async def main() -> None:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    words = ["king", "queen", "prince", "princess", "apple"]
    query = "royalty"
    async with AsyncOpenAI() as client:
        vectors = await embed(client, words)
        query_vector = (await embed(client, [query]))[0]
    print(f"Matches for {query}: {get_matches(query_vector, words, vectors, 0.3)}")
    plot_similarities(query, query_vector, words, vectors)
    plot_vectors_3d(words, vectors)
    plt.show()


if __name__ == "__main__":
    asyncio.run(main())

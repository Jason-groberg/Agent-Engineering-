"""Run with: python Embeddings_With_OpenAI/embedding_plotly.py (requires plotly)."""

import asyncio
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
from plotly.colors import qualitative
from dotenv import load_dotenv
from openai import AsyncOpenAI

from embedding_demo import embed, project_3d


def plot_vectors_3d(words: list[str], vectors: np.ndarray) -> go.Figure:
    if (vectors.ndim != 2 or len(words) != len(vectors) or not words
            or vectors.shape[1] == 0 or not np.isfinite(vectors).all()):
        raise ValueError("Provide at least one label and one finite embedding per label")
    coordinates = project_3d(vectors)
    fig = go.Figure()
    for index, (word, (x, y, z)) in enumerate(zip(words, coordinates)):
        color = qualitative.Plotly[index % len(qualitative.Plotly)]
        group = str(index)
        fig.add_trace(go.Scatter3d(
            x=[0, x], y=[0, y], z=[0, z], mode="lines+text",
            text=["", word], textposition="top center", name=word,
            line=dict(color=color, width=5), legendgroup=group,
        ))
        fig.add_trace(go.Cone(
            x=[x], y=[y], z=[z], u=[x], v=[y], w=[z],
            anchor="tip", sizemode="absolute", sizeref=0.12,
            colorscale=[[0, color], [1, color]], showscale=False,
            name=word, legendgroup=group, showlegend=False, hoverinfo="name",
        ))
    limit = max(float(np.abs(coordinates).max()) * 1.2, 0.01)
    fig.update_layout(
        title="Embedding vectors projected into 3D (uncentered SVD)",
        scene=dict(
            xaxis=dict(title="Component 1", range=[-limit, limit]),
            yaxis=dict(title="Component 2", range=[-limit, limit]),
            zaxis=dict(title="Component 3", range=[-limit, limit]),
            aspectmode="cube",
        ),
        legend=dict(groupclick="togglegroup"),
    )
    return fig


async def main() -> None:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    phrases = []
    while phrase := input("Enter a phrase (blank to plot): ").strip():
        phrases.append(phrase)
    if not phrases:
        print("No phrases entered.")
        return
    async with AsyncOpenAI() as client:
        embeddings = await embed(client, phrases)
    plot_vectors_3d(phrases, embeddings).show(renderer="browser")


if __name__ == "__main__":
    asyncio.run(main())

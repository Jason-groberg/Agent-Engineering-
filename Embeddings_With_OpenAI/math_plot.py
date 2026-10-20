"""Plot expression embeddings in 3D, colored by the matching answer-file labels."""

import asyncio
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
from dotenv import load_dotenv
from openai import AsyncOpenAI

from embedding_demo import embed
from embedding_plotly import plot_vectors_3d
from math_search import load_statements


def plot_statements(expressions: list[str], answers: list[str],
                    vectors: np.ndarray) -> go.Figure:
    colors = {"True": "#0072B2", "False": "#D55E00"}
    if len(expressions) != len(answers) or any(answer not in colors for answer in answers):
        raise ValueError("Provide one True or False answer per expression")
    fig = plot_vectors_3d(expressions, vectors)
    seen = set()
    for index, (expression, answer) in enumerate(zip(expressions, answers)):
        shaft, head = fig.data[2 * index:2 * index + 2]
        color = colors[answer]
        label = f"Line {index + 1}: {expression} ({answer})"
        shaft.update(
            line_color=color, mode="lines", name=answer,
            legendgroup=answer, showlegend=answer not in seen,
            hovertext=[label, label], hoverinfo="text",
        )
        head.update(
            colorscale=[[0, color], [1, color]], name=label, legendgroup=answer,
        )
        seen.add(answer)
    fig.update_layout(
        title="Math expression embeddings by truth value (3D projection)",
        legend_title_text="Answer label",
    )
    return fig


async def main() -> None:
    directory = Path(__file__).resolve().parent
    expressions, answers = load_statements(directory)
    load_dotenv(directory.parent / ".env")
    async with AsyncOpenAI() as client:
        vectors = await embed(client, expressions)
    plot_statements(expressions, answers, vectors).show(renderer="browser")


if __name__ == "__main__":
    asyncio.run(main())

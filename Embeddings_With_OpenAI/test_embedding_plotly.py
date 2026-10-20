import unittest
from unittest.mock import AsyncMock, patch

import numpy as np

from embedding_demo import project_3d
from embedding_plotly import main, plot_vectors_3d


class EmbeddingPlotlyTest(unittest.TestCase):
    def test_arrows_start_at_origin_and_end_at_projected_vectors(self):
        words = ["king", "queen", "apple"]
        vectors = np.array([[1., 0., 0.], [0.8, 0.6, 0.], [0., 0., 1.]])
        fig = plot_vectors_3d(words, vectors)
        self.assertEqual(len(fig.data), 6)
        for index, endpoint in enumerate(project_3d(vectors)):
            shaft, head = fig.data[2 * index:2 * index + 2]
            np.testing.assert_allclose([shaft.x[0], shaft.y[0], shaft.z[0]], 0)
            np.testing.assert_allclose([shaft.x[1], shaft.y[1], shaft.z[1]], endpoint)
            np.testing.assert_allclose([head.x[0], head.y[0], head.z[0]], endpoint)
            np.testing.assert_allclose([head.u[0], head.v[0], head.w[0]], endpoint)
            self.assertEqual(head.anchor, "tip")
            self.assertEqual(shaft.text[-1], words[index])
        self.assertIn("plotly", fig.to_html(include_plotlyjs=True))

    def test_two_vectors_and_invalid_inputs(self):
        self.assertEqual(len(plot_vectors_3d(["a"], np.ones((1, 3))).data), 2)
        fig = plot_vectors_3d(["a", "b"], np.eye(2))
        self.assertEqual(len(fig.data), 4)
        for vectors in (np.eye(3), np.empty((2, 0)), np.array([[np.nan], [1.]])):
            with self.assertRaises(ValueError):
                plot_vectors_3d(["a", "b"], vectors)


class InteractiveInputTest(unittest.IsolatedAsyncioTestCase):
    async def test_collects_phrases_until_blank_then_plots(self):
        vectors = np.eye(2)
        with (patch("builtins.input", side_effect=[" king ", "queen", ""]) as prompt,
              patch("embedding_plotly.AsyncOpenAI") as client,
              patch("embedding_plotly.embed", new_callable=AsyncMock, return_value=vectors) as embed,
              patch("embedding_plotly.plot_vectors_3d") as plot):
            await main()
            self.assertEqual(prompt.call_count, 3)
            embed.assert_awaited_once_with(client.return_value.__aenter__.return_value, ["king", "queen"])
            plot.assert_called_once_with(["king", "queen"], vectors)
            plot.return_value.show.assert_called_once_with(renderer="browser")

    async def test_empty_input_skips_api_and_plot(self):
        with (patch("builtins.input", return_value="   "),
              patch("builtins.print"),
              patch("embedding_plotly.AsyncOpenAI") as client,
              patch("embedding_plotly.plot_vectors_3d") as plot):
            await main()
            client.assert_not_called()
            plot.assert_not_called()


if __name__ == "__main__":
    unittest.main()

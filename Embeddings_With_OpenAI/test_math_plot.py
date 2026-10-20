import unittest
from pathlib import Path

import numpy as np

from math_plot import plot_statements
from math_search import load_statements


class MathPlotTest(unittest.TestCase):
    def test_all_expressions_have_matching_arrow_colors_and_labels(self):
        expressions, answers = load_statements(Path(__file__).resolve().parent)
        vectors = np.random.default_rng(0).normal(size=(len(expressions), 4))
        fig = plot_statements(expressions, answers, vectors)
        self.assertEqual(len(fig.data), 2 * len(expressions))
        self.assertEqual([trace.name for trace in fig.data if trace.showlegend], ["True", "False"])
        for index, answer in enumerate(answers):
            shaft, head = fig.data[2 * index:2 * index + 2]
            expected = "#0072B2" if answer == "True" else "#D55E00"
            self.assertEqual(shaft.line.color, expected)
            self.assertEqual(head.colorscale, ((0, expected), (1, expected)))
            self.assertEqual(shaft.legendgroup, answer)
            self.assertEqual(head.legendgroup, answer)
            self.assertIn(expressions[index], shaft.hovertext[-1])
            self.assertIn(answer, head.name)
        self.assertIn("plotly", fig.to_html())

    def test_rejects_missing_or_invalid_answers(self):
        for answers in ([], ["Maybe"]):
            with self.assertRaises(ValueError):
                plot_statements(["1 = 1"], answers, np.ones((1, 3)))


if __name__ == "__main__":
    unittest.main()

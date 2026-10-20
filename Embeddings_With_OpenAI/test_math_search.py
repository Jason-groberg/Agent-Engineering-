import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import numpy as np

from math_search import load_statements, main, search


class MathSearchTest(unittest.TestCase):
    def test_ranking_and_threshold(self):
        vectors = np.array([[0., 1.], [1., 0.], [0.8, 0.6]])
        matches = search(np.array([1., 0.]), vectors)
        self.assertEqual([index for index, _ in matches], [1, 2])
        np.testing.assert_allclose([score for _, score in matches], [1., 0.8])
        self.assertEqual(search(np.array([1., 0.]), vectors, threshold=1.), [])

    def test_load_preserves_alignment_and_rejects_bad_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            expressions = directory / "math_expressions.txt"
            answers = directory / "math_answers.txt"
            expressions.write_text("1 = 1\n1 = 2\n", encoding="utf-8")
            answers.write_text("True\nFalse\n", encoding="utf-8")
            self.assertEqual(load_statements(directory), (["1 = 1", "1 = 2"], ["True", "False"]))
            for content in ("True\n", "True\nMaybe\n"):
                answers.write_text(content, encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_statements(directory)
            answers.write_text("True\nFalse\n", encoding="utf-8")
            expressions.write_text("1 = 1\n\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_statements(directory)


class MathSearchMainTest(unittest.IsolatedAsyncioTestCase):
    async def test_search_reuses_embeddings_and_displays_answer_labels(self):
        with (patch("math_search.load_statements", return_value=(["1 = 1", "1 = 2"], ["True", "False"])),
              patch("builtins.input", side_effect=["true statement", "false statement", ""]),
              patch("math_search.AsyncOpenAI"),
              patch("math_search.embed", new_callable=AsyncMock,
                    side_effect=[np.eye(2), np.array([[1., 0.]]), np.array([[0., 1.]])]) as embed,
              patch("builtins.print") as output):
            await main()
            self.assertEqual([call.args[1] for call in embed.await_args_list],
                             [["1 = 1", "1 = 2"], ["true statement"], ["false statement"]])
            output.assert_any_call("1.0000 | 1 | True | 1 = 1")
            output.assert_any_call("1.0000 | 2 | False | 1 = 2")
            output.assert_any_call("Total returned: 1 | True: 1 | False: 0")
            output.assert_any_call("Total returned: 1 | True: 0 | False: 1")

    async def test_counts_mixed_and_empty_results(self):
        with (patch("math_search.load_statements", return_value=(["1 = 1", "1 = 2"], ["True", "False"])),
              patch("builtins.input", side_effect=["statement", "unrelated", ""]),
              patch("math_search.AsyncOpenAI"),
              patch("math_search.embed", new_callable=AsyncMock,
                    side_effect=[np.eye(2), np.array([[1., 1.]]), np.array([[-1., -1.]])]),
              patch("builtins.print") as output):
            await main()
            output.assert_any_call("Total returned: 2 | True: 1 | False: 1")
            output.assert_any_call("Total returned: 0 | True: 0 | False: 0")

    async def test_blank_query_skips_api(self):
        with (patch("builtins.input", return_value=""),
              patch("math_search.AsyncOpenAI") as client):
            await main()
            client.assert_not_called()


if __name__ == "__main__":
    unittest.main()

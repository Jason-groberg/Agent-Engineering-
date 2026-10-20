import unittest

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from embedding_demo import cosine_scores, get_matches, plot_similarities, plot_vectors_3d, project_3d


class EmbeddingDemoTest(unittest.TestCase):
    def test_similarity_and_plots(self):
        words = ["king", "queen", "apple"]
        vectors = np.array([[1., 0., 0.], [0.8, 0.6, 0.], [0., 0., 1.]])
        query = np.array([1., 0., 0.])
        np.testing.assert_allclose(cosine_scores(query, vectors), [1., 0.8, 0.])
        self.assertEqual(get_matches(query, words, vectors, 0.5), ["king", "queen"])
        coordinates = project_3d(vectors)
        np.testing.assert_allclose(coordinates @ coordinates.T, vectors @ vectors.T)

        plot_similarities("royalty", query, words, vectors)
        plot_vectors_3d(words, vectors)
        self.assertEqual(len(plt.get_fignums()), 2)
        ax = plt.gcf().axes[0]
        self.assertEqual((ax.get_xlabel(), ax.get_ylabel(), ax.get_zlabel()), ("X", "Y", "Z"))
        self.assertEqual(ax.get_legend_handles_labels()[1], words)
        plt.close("all")


if __name__ == "__main__":
    unittest.main()

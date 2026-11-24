"""GloVe query expansion using our own cosine-similarity matching.

Only vectors for words that exist in the index lexicon are kept, so every
suggested expansion is searchable and memory stays small.
"""
from pathlib import Path

import numpy as np

from backend.tokenizer.tokenizer import STOPWORDS

ROOT = Path(__file__).resolve().parents[2]
GLOVE_PATH = ROOT / "data" / "glove" / "glove.6B.100d.txt"


class GloVeExpander:
    def __init__(self, lexicon, glove_path=GLOVE_PATH):
        words, vectors = [], []
        with open(glove_path, encoding="utf-8") as file:
            for line in file:
                word, _, rest = line.partition(" ")
                if word in lexicon and word not in STOPWORDS:
                    words.append(word)
                    vectors.append(np.asarray(rest.split(), dtype=np.float32))
        if not words:
            raise ValueError("No GloVe words matched the lexicon.")

        matrix = np.vstack(vectors)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self.words = words
        self.index = {w: i for i, w in enumerate(words)}
        self.matrix = matrix / norms  # unit vectors -> dot product = cosine

    def neighbours(self, word, k=5, min_sim=0.6):
        """Return [(word, cosine_similarity)] for the closest in-lexicon words."""
        i = self.index.get(word)
        if i is None:
            return []
        sims = self.matrix @ self.matrix[i]
        sims[i] = -1.0
        k = min(k, len(sims) - 1)
        top = np.argpartition(-sims, k)[:k]
        top = top[np.argsort(-sims[top])]
        return [(self.words[j], float(sims[j])) for j in top if sims[j] >= min_sim]

    def expand_query(self, terms, k=3, min_sim=0.6):
        """Return {expansion_word: weight} for use as BM25 optional terms."""
        original = set(terms)
        expansion = {}
        for term in terms:
            for word, sim in self.neighbours(term, k, min_sim):
                if word not in original:
                    expansion[word] = max(expansion.get(word, 0.0), sim)
        return expansion
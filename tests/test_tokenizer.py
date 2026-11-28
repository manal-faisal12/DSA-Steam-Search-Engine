import unittest

from backend.tokenizer import normalize_text, tokenize, unique_tokens


class TokenizerTests(unittest.TestCase):
    def test_normalizes_case_accents_and_whitespace(self):
        self.assertEqual(normalize_text("  CAFÉ\tRACER  "), "cafe racer")

    def test_folds_accents_in_tokens(self):
        self.assertEqual(tokenize("Pokémon"), ["pokemon"])

    def test_removes_punctuation_stopwords_and_single_letters(self):
        self.assertEqual(
            tokenize("The co-op's fast-paced action!", remove_stopwords=True),
            ["co", "op", "fast", "paced", "action"],
        )

    def test_keeps_negation_words(self):
        self.assertEqual(
            tokenize("not a casual game", remove_stopwords=True),
            ["not", "casual", "game"],
        )

    def test_keeps_stopwords_by_default(self):
        self.assertEqual(tokenize("A game for you"), ["a", "game", "for", "you"])

    def test_unique_tokens_preserves_first_seen_order(self):
        self.assertEqual(
            unique_tokens(["Space Game", "game tactics"]),
            ["space", "game", "tactics"],
        )
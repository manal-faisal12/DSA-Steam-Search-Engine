import unittest

from backend.tokenizer import normalize_text, tokenize, unique_tokens


class TokenizerTests(unittest.TestCase):
    def test_normalizes_case_unicode_and_whitespace(self):
        self.assertEqual(normalize_text("  CAFÉ\tRACER  "), "café racer")

    def test_removes_punctuation_and_stopwords(self):
        self.assertEqual(tokenize("The co-op's fast-paced action!"), ["co", "op's", "fast", "paced", "action"])

    def test_keeps_negation_words(self):
        self.assertEqual(tokenize("not a casual game"), ["not", "casual", "game"])

    def test_can_keep_stopwords_for_phrase_processing(self):
        self.assertEqual(tokenize("A game for you", remove_stopwords=False), ["a", "game", "for", "you"])

    def test_unique_tokens_preserves_first_seen_order(self):
        self.assertEqual(unique_tokens(["Space Game", "game tactics"]), ["space", "game", "tactics"])

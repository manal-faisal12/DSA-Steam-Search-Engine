"""Small, explicit English stopword set used by the project tokenizer.

The set intentionally keeps negation words (for example ``not`` and ``no``),
because removing them can change the meaning of a game description.
"""

STOPWORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "by",
    "for", "from", "has", "have", "he", "her", "hers", "him", "his", "i",
    "in", "into", "is", "it", "its", "me", "my", "of", "on", "or", "our",
    "ours", "she", "that", "the", "their", "theirs", "them", "they", "this",
    "to", "was", "we", "were", "with", "you", "your", "yours",
})

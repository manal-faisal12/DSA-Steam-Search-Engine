"""Compressed (radix) trie for autocomplete.

Every node stores the best ``K`` suggestions found anywhere below it, so a
lookup only walks the typed prefix and reads the answer: the cost depends on
the length of the prefix, not on how many titles share it.

Two kinds of text are indexed:

* game titles, ranked by how many reviews the game has;
* tags and genres, ranked by how many games use them.

A title is stored under its full text and also under each of its later
words ("Stardew Valley" is found by typing "val"), so typing the middle of a
title still works.  Every key points at one entry, and a node never lists
the same entry twice.
"""

from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Iterable

TOP_K = 5
_SPACES = re.compile(r"\s+")
_SKIP_WORD_STARTS = frozenset({"a", "an", "and", "of", "the", "to", "in", "on", "for", "or", "vs"})


def normalize(text: str) -> str:
    """Lowercase, fold accents and collapse whitespace."""
    folded = unicodedata.normalize("NFKD", str(text))
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    return _SPACES.sub(" ", folded.casefold()).strip()


@dataclass(frozen=True)
class Entry:
    text: str
    kind: str          # "game" or "tag"
    weight: float


class _Node:
    __slots__ = ("children", "entries", "top")

    def __init__(self) -> None:
        # first character of the edge -> (edge label, child node)
        self.children: dict[str, tuple[str, _Node]] = {}
        self.entries: list[int] = []     # entries whose key ends exactly here
        self.top: tuple[int, ...] = ()   # best entry ids in this subtree


class AutocompleteTrie:
    def __init__(self, k: int = TOP_K) -> None:
        self.k = k
        self.root = _Node()
        self.entries: list[Entry] = []
        self._finalised = True

    # ---- building ------------------------------------------------------
    def add_entry(self, text: str, kind: str, weight: float, *, word_starts: bool = False) -> None:
        key = normalize(text)
        if not key:
            return
        entry_id = len(self.entries)
        self.entries.append(Entry(text=str(text).strip(), kind=kind, weight=weight))
        self._insert(key, entry_id)
        if word_starts:
            position = key.find(" ")
            while position != -1:
                start = position + 1
                end = key.find(" ", start)
                word = key[start:end if end != -1 else len(key)]
                if len(word) >= 3 and word not in _SKIP_WORD_STARTS:
                    self._insert(key[start:], entry_id)
                position = end
        self._finalised = False

    def _insert(self, key: str, entry_id: int) -> None:
        node = self.root
        while True:
            if not key:
                if entry_id not in node.entries:
                    node.entries.append(entry_id)
                return
            edge = node.children.get(key[0])
            if edge is None:
                leaf = _Node()
                leaf.entries.append(entry_id)
                node.children[key[0]] = (key, leaf)
                return
            label, child = edge
            common = 0
            limit = min(len(label), len(key))
            while common < limit and label[common] == key[common]:
                common += 1
            if common == len(label):
                node, key = child, key[common:]
                continue
            # split the edge in two at the point where the keys differ
            middle = _Node()
            middle.children[label[common]] = (label[common:], child)
            node.children[key[0]] = (label[:common], middle)
            node, key = middle, key[common:]

    def finalise(self) -> None:
        """Compute the best suggestions below every node (call once after building)."""
        # post-order walk without recursion
        stack: list[tuple[_Node, bool]] = [(self.root, False)]
        while stack:
            node, visited = stack.pop()
            if not visited:
                stack.append((node, True))
                for _, child in node.children.values():
                    stack.append((child, False))
                continue
            seen: set[int] = set()
            pool: list[int] = []
            for entry_id in node.entries:
                if entry_id not in seen:
                    seen.add(entry_id)
                    pool.append(entry_id)
            for _, child in node.children.values():
                for entry_id in child.top:
                    if entry_id not in seen:
                        seen.add(entry_id)
                        pool.append(entry_id)
            pool.sort(key=self._rank)
            node.top = tuple(pool[: self.k])
        self._finalised = True

    def _rank(self, entry_id: int) -> tuple[float, str]:
        entry = self.entries[entry_id]
        return (-entry.weight, entry.text)

    # ---- querying ------------------------------------------------------
    def suggest(self, prefix: str, limit: int | None = None) -> list[dict[str, str]]:
        if not self._finalised:
            self.finalise()
        key = normalize(prefix)
        if not key:
            return []
        node = self.root
        while key:
            edge = node.children.get(key[0])
            if edge is None:
                return []
            label, child = edge
            if len(key) <= len(label):
                if not label.startswith(key):
                    return []
                node = child
                break
            if not key.startswith(label):
                return []
            node, key = child, key[len(label):]
        wanted = self.k if limit is None else min(limit, self.k)
        return [
            {"text": self.entries[i].text, "kind": self.entries[i].kind}
            for i in node.top[:wanted]
        ]

    def __len__(self) -> int:
        return len(self.entries)


def build_trie(games: Iterable[dict[str, Any]], k: int = TOP_K) -> AutocompleteTrie:
    """Build the autocomplete trie from game records (as stored in the index)."""
    trie = AutocompleteTrie(k)
    label_counts: dict[str, int] = {}
    label_text: dict[str, str] = {}
    for game in games:
        title = str(game.get("title", "")).strip()
        if title:
            reviews = int(game.get("positive", 0) or 0) + int(game.get("negative", 0) or 0)
            trie.add_entry(title, "game", math.log1p(reviews), word_starts=True)
        for field in ("tags", "genres"):
            values = game.get(field) or []
            if not isinstance(values, list):
                continue
            for label in values:
                key = normalize(label)
                if key:
                    label_counts[key] = label_counts.get(key, 0) + 1
                    label_text.setdefault(key, str(label).strip())
    for key, count in label_counts.items():
        trie.add_entry(label_text[key], "tag", math.log1p(count))
    trie.finalise()
    return trie

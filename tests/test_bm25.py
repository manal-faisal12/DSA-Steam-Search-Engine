#This checks the BM25 maths by hand (IDF value, tf, length normalisation), AND/OR behaviour, tie-breaking and filters.

import math
from backend.search.bm25 import BM25, idf

def make_bm25(postings, lengths):
    return BM25(
        num_docs=len(lengths),
        avg_doc_len=sum(lengths) / len(lengths),
        doc_lengths=lengths,
        get_postings=lambda term: postings.get(term, []),
    )


def test_idf_hand_calculated():
    # N=3, df=1 -> ln(1 + 2.5/1.5) = 0.980829...
    assert math.isclose(idf(3, 1), 0.980829, abs_tol=1e-6)


def test_idf_never_negative():
    assert idf(10, 10) > 0


def test_score_equals_idf_when_tf1_and_average_length():
    # norm = k1, so tf*(k1+1)/(tf+k1) = 1 and the score collapses to IDF.
    bm = make_bm25({"x": [(0, 1)]}, [10, 10, 10])
    (doc_id, score), = bm.search(["x"])
    assert doc_id == 0
    assert math.isclose(score, idf(3, 1))


def test_higher_tf_ranks_higher():
    bm = make_bm25({"x": [(0, 1), (1, 3)]}, [10, 10])
    assert [d for d, _ in bm.search(["x"])] == [1, 0]


def test_shorter_document_ranks_higher():
    bm = make_bm25({"x": [(0, 2), (1, 2)]}, [5, 20])
    assert [d for d, _ in bm.search(["x"])] == [0, 1]


def test_and_semantics():
    postings = {"space": [(0, 1), (1, 1)], "game": [(1, 1), (2, 1)]}
    bm = make_bm25(postings, [10, 10, 10])
    assert [d for d, _ in bm.search(["space", "game"])] == [1]


def test_or_semantics():
    postings = {"space": [(0, 1)], "game": [(1, 1)]}
    bm = make_bm25(postings, [10, 10])
    found = {d for d, _ in bm.search(["space", "game"], require_all=False)}
    assert found == {0, 1}


def test_ties_broken_by_lower_doc_id():
    bm = make_bm25({"x": [(2, 1), (0, 1), (1, 1)]}, [10, 10, 10])
    assert [d for d, _ in bm.search(["x"])] == [0, 1, 2]


def test_candidate_filter():
    bm = make_bm25({"x": [(0, 1), (1, 1)]}, [10, 10])
    results = bm.search(["x"], candidate_filter=lambda d: d == 1)
    assert [d for d, _ in results] == [1]


def test_top_k_and_empty_and_unknown():
    bm = make_bm25({"x": [(0, 1), (1, 1), (2, 1)]}, [10, 10, 10])
    assert len(bm.search(["x"], top_k=2)) == 2
    assert bm.search([]) == []
    assert bm.search(["nope"]) == []


# Only passes after step 5 (search_weighted) is added to bm25.py.
def test_optional_terms_boost_but_do_not_add_candidates():
    postings = {"x": [(0, 1), (1, 1)], "y": [(1, 1), (2, 1)]}
    bm = make_bm25(postings, [10, 10, 10])
    results = bm.search_weighted(["x"], {"y": 0.5})
    assert [d for d, _ in results] == [1, 0]   # doc 1 boosted by "y"
    assert 2 not in [d for d, _ in results]    # doc 2 lacks required "x"

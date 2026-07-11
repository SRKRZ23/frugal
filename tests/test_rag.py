from frugal.rag import ragcheck


def test_ragcheck_perfect_example():
    report = ragcheck([
        {
            "query": "capital of France?",
            "retrieved": [{"id": "d1", "text": "Paris is the capital of France"}],
            "gold_ids": ["d1"],
            "answer": "Paris is the capital of France",
            "citations": ["d1"],
        }
    ])
    d = report.as_dict()
    assert d["retrieval_hit_rate"] == 1.0
    assert d["faithfulness"] == 1.0
    assert d["citation_coverage"] == 1.0


def test_ragcheck_retrieval_miss():
    report = ragcheck([
        {
            "query": "capital?",
            "retrieved": [{"id": "d9", "text": "unrelated content about penguins"}],
            "gold_ids": ["d1"],
            "answer": "Paris",
            "citations": [],
        }
    ])
    assert report.as_dict()["retrieval_hit_rate"] == 0.0


def test_ragcheck_bad_citation():
    report = ragcheck([
        {
            "query": "q",
            "retrieved": [{"id": "d1", "text": "some grounded text here"}],
            "gold_ids": ["d1"],
            "answer": "some grounded text here",
            "citations": ["dX"],  # not in retrieved
        }
    ])
    assert report.as_dict()["citation_coverage"] == 0.0

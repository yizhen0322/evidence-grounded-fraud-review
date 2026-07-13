from tools.build_guardrail_corpus import build_items
from tools.calibrate_validator import calibrate


def test_corpus_has_required_size_categories_and_unique_ids(tmp_path):
    items = build_items()
    attacks = [item for item in items if item["kind"] == "attack"]
    faithful = [item for item in items if item["kind"] == "faithful"]
    assert len(attacks) >= 150
    assert len(faithful) >= 40
    assert len({item["category"] for item in attacks}) >= 9
    assert len({item["corpus_id"] for item in items}) == len(items)

    path = tmp_path / "corpus.jsonl"
    path.write_text(
        "".join(__import__("json").dumps(item) + "\n" for item in items)
    )
    report, failures = calibrate(path)
    assert failures == []
    assert report["overall"]["gate_passed"] is True

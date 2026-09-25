from __future__ import annotations

from collections import Counter
import dataclasses

import pandas as pd
import pytest

from core.config import load_settings
from core.utils import read_json
from evaluation.metrics import _token_f1, evaluate_pipeline
from evaluation.testset import build_test_set, load_or_build_test_set
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question


@pytest.fixture(scope="module")
def clean_df() -> pd.DataFrame:
    return pd.read_json(load_settings().paths.clean_json)


@pytest.fixture()
def settings(tmp_path):
    base = load_settings()
    paths = dataclasses.replace(
        base.paths,
        chroma_dir=tmp_path / "chroma",
        embeddings_json=tmp_path / "embeddings.json",
        eval_testset=tmp_path / "test_set.json",
    )
    return dataclasses.replace(base, paths=paths, refresh_test_set=False)


def test_build_test_set_contract(clean_df, tmp_path):
    rows = build_test_set(clean_df, tmp_path / "test_set.json")

    assert len(rows) == 10
    assert Counter(row["question_type"] for row in rows) == {"summary": 3, "authors": 3, "date": 2, "categories": 2}
    assert len({row["id"] for row in rows}) == 10
    doc_ids = [row["ground_truth_doc_ids"][0] for row in rows]
    assert len(set(doc_ids)) == 10
    assert set(doc_ids) <= set(clean_df["paper_id"])
    for row in rows:
        paper = clean_df.set_index("paper_id").loc[row["ground_truth_doc_ids"][0]]
        assert f"'{paper['title']}'" in row["question"]
        assert row["ground_truth"]
    assert read_json(tmp_path / "test_set.json") == rows


def test_build_test_set_is_deterministic(clean_df, tmp_path):
    first = build_test_set(clean_df, tmp_path / "a.json")
    second = build_test_set(clean_df.sample(frac=1.0, random_state=7), tmp_path / "b.json")
    assert first == second


def test_build_test_set_rejects_small_dataset(clean_df, tmp_path):
    with pytest.raises(ValueError):
        build_test_set(clean_df.head(5), tmp_path / "test_set.json")


def test_load_or_build_reuses_existing_file(clean_df, settings):
    original = load_or_build_test_set(clean_df, settings)
    # Du lieu corrupted khong duoc lam thay doi bo de da chot.
    reused = load_or_build_test_set(clean_df.head(3), settings)
    assert reused == original


def test_token_f1():
    assert _token_f1("a b c", "a b c") == 1.0
    assert _token_f1("a b c", "") == 0.0
    assert _token_f1("a b c d", "a b") == pytest.approx(2 / 3)


def test_qa_answers_match_ground_truth_on_clean_index(clean_df, settings):
    rows = build_test_set(clean_df, settings.paths.eval_testset)
    index = LocalEmbeddingIndex.build(clean_df, settings)
    assert index.collection.count() == len(clean_df)

    for row in rows:
        result = answer_question(row["question"], settings=settings, index=index)
        assert result.answer == row["ground_truth"], row["id"]
        assert row["ground_truth_doc_ids"][0] == result.retrieved_doc_ids[0]


def test_evaluation_detects_corrupted_answers(clean_df, settings, tmp_path, monkeypatch):
    monkeypatch.setenv("JUDGE_MODE", "heuristic")
    build_test_set(clean_df, settings.paths.eval_testset)

    clean_index = LocalEmbeddingIndex.build(clean_df, settings)
    clean = evaluate_pipeline(
        settings, clean_index, settings.paths.eval_testset, tmp_path / "clean_m.json", tmp_path / "clean_a.json"
    ).summary

    broken_df = clean_df.copy()
    broken_df["summary"] = ""
    broken_df["published"] = "2025-01-01"
    broken_index = LocalEmbeddingIndex.build(broken_df, settings, embeddings_output_path=tmp_path / "broken.json")
    broken = evaluate_pipeline(
        settings, broken_index, settings.paths.eval_testset, tmp_path / "broken_m.json", tmp_path / "broken_a.json"
    ).summary

    assert clean["mean_token_f1"] == 1.0
    assert clean["judge_fallback_count"] == clean["samples"]
    assert broken["mean_token_f1"] < clean["mean_token_f1"]
    assert broken["judge_accuracy"] < clean["judge_accuracy"]

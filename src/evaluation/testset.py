from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import first_sentence, read_json, write_json

TEST_SET_SIZE = 10
REQUIRED_COLUMNS = ("paper_id", "title", "summary", "published", "authors_joined", "categories_joined")
REQUIRED_FIELDS = ("id", "question_type", "question", "ground_truth", "ground_truth_doc_ids")

# Thu tu xoay vong -> 3 summary, 3 authors, 2 date, 2 categories cho 10 cau.
QUESTION_TYPE_CYCLE = ("summary", "authors", "date", "categories")

# Cau chu phai khop voi keyword ma `retrieval.qa._extract_answer` nhan dien,
# va title nam trong dau nhay don de `answer_question` tra exact lookup.
QUESTION_TEMPLATES = {
    "summary": "What is the summary of the paper '{title}'?",
    "authors": "Who authored the paper '{title}'?",
    "date": "When was the paper '{title}' published?",
    "categories": "What categories does the paper '{title}' belong to?",
}


def _ground_truth(row: dict[str, Any], question_type: str) -> str:
    if question_type == "summary":
        return first_sentence(row["summary"])
    if question_type == "authors":
        return row["authors_joined"]
    if question_type == "date":
        return row["published"]
    return row["categories_joined"]


def _eligible_papers(df: pd.DataFrame) -> pd.DataFrame:
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Clean dataframe is missing columns required for the test set: {missing}")
    candidates = df.dropna(subset=list(REQUIRED_COLUMNS)).drop_duplicates(subset="paper_id")
    candidates = candidates[
        candidates["title"].str.strip().ne("")
        # Title chua dau nhay don se lam regex '([^']+)' trong qa.py cat sai title.
        & ~candidates["title"].str.contains("'", regex=False)
        & candidates["summary"].map(first_sentence).str.len().ge(30)
        & candidates["authors_joined"].str.strip().ne("")
        & candidates["categories_joined"].str.strip().ne("")
    ]
    return candidates.sort_values(["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)


def _spread_positions(total: int, count: int) -> list[int]:
    """Chon `count` vi tri trai deu tu moi nhat den cu nhat, co dinh giua cac lan chay."""
    if count == 1:
        return [0]
    return [round(i * (total - 1) / (count - 1)) for i in range(count)]


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Tao bo 10 cau hoi benchmark tu clean dataframe va ghi ra `output_path`.

    Moi cau hoi dung mot paper khac nhau, chon trai deu theo ngay xuat ban de bo de
    bao gom ca bai moi nhat (bi anh huong khi corruption drop latest records) lan bai cu.
    Khong dung random nen chay lai tren cung clean data luon ra cung mot bo de.
    """
    candidates = _eligible_papers(df)
    if len(candidates) < TEST_SET_SIZE:
        raise ValueError(
            f"Need at least {TEST_SET_SIZE} valid papers to build the test set, got {len(candidates)}."
        )

    rows: list[dict[str, Any]] = []
    for number, position in enumerate(_spread_positions(len(candidates), TEST_SET_SIZE), start=1):
        paper = candidates.iloc[position].to_dict()
        question_type = QUESTION_TYPE_CYCLE[(number - 1) % len(QUESTION_TYPE_CYCLE)]
        rows.append(
            {
                "id": f"eval_{number:03d}",
                "question_type": question_type,
                "question": QUESTION_TEMPLATES[question_type].format(title=paper["title"]),
                "ground_truth": _ground_truth(paper, question_type),
                "ground_truth_doc_ids": [paper["paper_id"]],
            }
        )

    write_json(Path(output_path), rows)
    return rows


def load_or_build_test_set(df: pd.DataFrame, settings: Settings) -> list[dict[str, Any]]:
    """Dung lai test set da co de baseline/corrupted/repaired cham tren cung mot bo de.

    Chi build lai khi file chua ton tai hoac REFRESH_TEST_SET=1. `df` phai la clean
    baseline data, khong truyen corrupted data vao day.
    """
    path = settings.paths.eval_testset
    if path.exists() and not settings.refresh_test_set:
        test_set = read_json(path)
        for item in test_set:
            missing = [field for field in REQUIRED_FIELDS if field not in item]
            if missing:
                raise ValueError(f"Test set item {item.get('id', '?')} is missing fields: {missing}")
        return test_set
    return build_test_set(df, path)

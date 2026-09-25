from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import random

import pandas as pd

from core.utils import now_utc, write_json

# Seed co dinh de qua trinh tiem loi tai lap duoc (reproducible corruption).
CORRUPTION_SEED = 20260925

# Chuoi ky tu rac dung cho buoc inject noise.
_NOISE_SNIPPET = "###@@@ %%%$$$ <<lorem-noise>> zzqx ¶§ �"

# Ty le so dong bi anh huong cho tung loai loi (tinh tren so dong con lai).
_DROP_LATEST_RATIO = 0.20
_BLANK_RATIO = 0.15
_NOISE_RATIO = 0.15
_TRUNCATE_RATIO = 0.15
_STALE_RATIO = 0.35  # Vuot nguong freshness SLA 25% sau khi inject va duplicate.
_DUPLICATE_RATIO = 0.10
_STALE_DAYS = 365
_TRUNCATE_LEN = 5  # < 8 ky tu de vi pham quy tac do dai title


def _count(ratio: float, n_rows: int) -> int:
    return max(1, round(ratio * n_rows)) if n_rows else 0


def _shift_date(value, delta_days: int) -> str:
    """Cong delta_days vao mot chuoi ngay ISO; giu nguyen neu khong parse duoc."""
    text = str(value).strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text
    shifted = parsed + timedelta(days=delta_days)
    if "T" in text or " " in text:
        return shifted.isoformat()
    return shifted.date().isoformat()


def _build_text_for_embedding(row) -> str:
    return (
        f"Title: {row['title']}\n"
        f"Authors: {row['authors_joined']}\n"
        f"Published: {row['published']}\n"
        f"Categories: {row['categories_joined']}\n"
        f"Summary: {row['summary']}"
    )


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Tiem 6 dang data corruption vao clean dataframe va ghi corruption log.

    Args:
        df: clean dataframe (output cua build_clean_dataframe).
        output_log_path: noi ghi corruption_log.json (settings.paths.corruption_log).

    Returns:
        DataFrame da bi lam ban; cac cot giu nguyen so voi input.
    """
    rng = random.Random(CORRUPTION_SEED)
    corrupted = df.copy(deep=True).reset_index(drop=True)
    input_rows = len(corrupted)
    log_entries: list[dict] = []

    # --- 1. Drop latest records (bo cac ban ghi moi nhat) ---
    n_drop = _count(_DROP_LATEST_RATIO, len(corrupted))
    newest = corrupted.sort_values("published", ascending=False)
    drop_ids = newest["paper_id"].head(n_drop).tolist()
    corrupted = corrupted[~corrupted["paper_id"].isin(drop_ids)].reset_index(drop=True)
    log_entries.append({
        "step": 1,
        "type": "drop_latest_records",
        "description": "Bo cac ban ghi published moi nhat de mo phong missing records.",
        "params": {"ratio": _DROP_LATEST_RATIO, "dropped": len(drop_ids)},
        "affected_paper_ids": drop_ids,
        "affected_count": len(drop_ids),
    })

    # Chia mot pool vi tri khong trung nhau cho 4 loai loi theo dong.
    n_rows = len(corrupted)
    pool = list(range(n_rows))
    rng.shuffle(pool)
    b, no, tr, st = (
        _count(_BLANK_RATIO, n_rows),
        _count(_NOISE_RATIO, n_rows),
        _count(_TRUNCATE_RATIO, n_rows),
        _count(_STALE_RATIO, n_rows),
    )
    blank_idx = pool[0:b]
    noise_idx = pool[b:b + no]
    trunc_idx = pool[b + no:b + no + tr]
    stale_idx = pool[b + no + tr:b + no + tr + st]

    # --- 2. Blank summary (xoa tom tat) ---
    blank_ids = corrupted.loc[blank_idx, "paper_id"].tolist()
    for idx in blank_idx:
        corrupted.loc[idx, "summary"] = ""
    log_entries.append({
        "step": 2,
        "type": "blank_summary",
        "description": "Xoa noi dung summary de mo phong empty abstract.",
        "params": {"rows": len(blank_ids)},
        "affected_paper_ids": blank_ids,
        "affected_count": len(blank_ids),
    })

    # --- 3. Inject noise (chen ky tu rac) ---
    noise_ids = corrupted.loc[noise_idx, "paper_id"].tolist()
    for idx in noise_idx:
        corrupted.loc[idx, "summary"] = f"{corrupted.loc[idx, 'summary']} {_NOISE_SNIPPET}"
    log_entries.append({
        "step": 3,
        "type": "inject_noise",
        "description": "Chen chuoi ky tu rac vao summary.",
        "params": {"rows": len(noise_ids), "snippet": _NOISE_SNIPPET},
        "affected_paper_ids": noise_ids,
        "affected_count": len(noise_ids),
    })

    # --- 4. Truncate title (cat ngan tieu de < 8 ky tu) ---
    trunc_ids = corrupted.loc[trunc_idx, "paper_id"].tolist()
    for idx in trunc_idx:
        corrupted.loc[idx, "title"] = str(corrupted.loc[idx, "title"])[:_TRUNCATE_LEN]
    log_entries.append({
        "step": 4,
        "type": "truncate_title",
        "description": f"Cat title con {_TRUNCATE_LEN} ky tu (< 8) de vi pham do dai toi thieu.",
        "params": {"rows": len(trunc_ids), "keep_chars": _TRUNCATE_LEN},
        "affected_paper_ids": trunc_ids,
        "affected_count": len(trunc_ids),
    })

    # --- 5. Stale date (lam cu ngay thang) ---
    stale_ids = corrupted.loc[stale_idx, "paper_id"].tolist()
    for idx in stale_idx:
        corrupted.loc[idx, "published"] = _shift_date(corrupted.loc[idx, "published"], -_STALE_DAYS)
        try:
            corrupted.loc[idx, "age_days"] = int(corrupted.loc[idx, "age_days"]) + _STALE_DAYS
        except (TypeError, ValueError):
            pass
    log_entries.append({
        "step": 5,
        "type": "stale_date",
        "description": f"Lui published {_STALE_DAYS} ngay va cong age_days de mo phong stale data.",
        "params": {"rows": len(stale_ids), "days": _STALE_DAYS},
        "affected_paper_ids": stale_ids,
        "affected_count": len(stale_ids),
    })

    # --- 6. Duplicate rows (nhan ban dong -> pha tinh duy nhat paper_id) ---
    dup_count = min(_count(_DUPLICATE_RATIO, len(corrupted)), len(corrupted))
    dup_positions = rng.sample(range(len(corrupted)), dup_count) if len(corrupted) else []
    dup_ids = corrupted.iloc[dup_positions]["paper_id"].tolist()
    if dup_positions:
        corrupted = pd.concat([corrupted, corrupted.iloc[dup_positions]], ignore_index=True)
    log_entries.append({
        "step": 6,
        "type": "duplicate_rows",
        "description": "Nhan ban mot so dong de pha vo tinh duy nhat cua paper_id.",
        "params": {"rows": len(dup_ids)},
        "affected_paper_ids": dup_ids,
        "affected_count": len(dup_ids),
    })

    # --- 7. Rebuild summary_chars + text_for_embedding cho toan bo dong ---
    corrupted["summary_chars"] = corrupted["summary"].astype(str).str.len()
    corrupted["text_for_embedding"] = corrupted.apply(_build_text_for_embedding, axis=1)
    corrupted = corrupted.reset_index(drop=True)

    # --- 8. Ghi corruption log ---
    log = {
        "seed": CORRUPTION_SEED,
        "generated_at": now_utc().isoformat(),
        "input_rows": input_rows,
        "output_rows": len(corrupted),
        "corruptions": log_entries,
    }
    write_json(Path(output_log_path), log)
    return corrupted

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from dateutil import tz


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def today_str(tz_name: str) -> str:
    tzi = tz.gettz(tz_name)
    if tzi is None:
        raise ValueError(f"invalid timezone: {tz_name}")
    now = datetime.now(tzi)
    return now.strftime("%Y-%m-%d")


def since_dt_iso(tz_name: str, since_days: int) -> datetime:
    tzi = tz.gettz(tz_name)
    if tzi is None:
        raise ValueError(f"invalid timezone: {tz_name}")
    now = datetime.now(tzi)
    start = now - timedelta(days=since_days)
    return start


def norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def contains_term(text: str, term: str) -> bool:
    return term.lower() in (text or "").lower()


def dump_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

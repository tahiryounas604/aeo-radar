"""SQLite storage for brands, answers and analysis runs (stdlib sqlite3)."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .models import AnalysisResult, Answer, Brand, Competitor

_SCHEMA = """
CREATE TABLE IF NOT EXISTS brands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    aliases TEXT NOT NULL DEFAULT '[]',
    competitors TEXT NOT NULL DEFAULT '[]',
    prompts TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand_name TEXT NOT NULL,
    engine TEXT NOT NULL,
    prompt TEXT NOT NULL,
    text TEXT NOT NULL,
    imported_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand_name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    overall_score REAL NOT NULL,
    result_json TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def init(self) -> None:
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    # -- brands ---------------------------------------------------------
    def add_brand(self, brand: Brand) -> Brand:
        cur = self.conn.execute(
            "INSERT INTO brands(name, aliases, competitors, prompts, created_at)"
            " VALUES (?,?,?,?,?)"
            " ON CONFLICT(name) DO UPDATE SET aliases=excluded.aliases,"
            " competitors=excluded.competitors, prompts=excluded.prompts",
            (
                brand.name,
                json.dumps(brand.aliases),
                json.dumps([c.to_dict() for c in brand.competitors]),
                json.dumps(brand.prompts),
                _now(),
            ),
        )
        self.conn.commit()
        brand.id = cur.lastrowid if cur.lastrowid else self.get_brand(brand.name).id  # type: ignore[union-attr]
        return brand

    def get_brand(self, name: str) -> Brand | None:
        row = self.conn.execute("SELECT * FROM brands WHERE name=?", (name,)).fetchone()
        if row is None:
            return None
        return Brand(
            id=row["id"],
            name=row["name"],
            aliases=json.loads(row["aliases"]),
            competitors=[Competitor.from_dict(c) for c in json.loads(row["competitors"])],
            prompts=json.loads(row["prompts"]),
        )

    def list_brands(self) -> list[Brand]:
        rows = self.conn.execute("SELECT * FROM brands ORDER BY name").fetchall()
        out = []
        for row in rows:
            out.append(
                Brand(
                    id=row["id"],
                    name=row["name"],
                    aliases=json.loads(row["aliases"]),
                    competitors=[Competitor.from_dict(c) for c in json.loads(row["competitors"])],
                    prompts=json.loads(row["prompts"]),
                )
            )
        return out

    # -- answers --------------------------------------------------------
    def add_answers(self, brand_name: str, answers: list[Answer]) -> int:
        now = _now()
        self.conn.executemany(
            "INSERT INTO answers(brand_name, engine, prompt, text, imported_at)"
            " VALUES (?,?,?,?,?)",
            [(brand_name, a.engine, a.prompt, a.text, now) for a in answers],
        )
        self.conn.commit()
        return len(answers)

    def list_answers(self, brand_name: str) -> list[Answer]:
        rows = self.conn.execute(
            "SELECT * FROM answers WHERE brand_name=? ORDER BY id", (brand_name,)
        ).fetchall()
        return [
            Answer(
                id=r["id"], brand_name=r["brand_name"], engine=r["engine"],
                prompt=r["prompt"], text=r["text"], imported_at=r["imported_at"],
            )
            for r in rows
        ]

    # -- runs / score history -------------------------------------------
    def save_run(self, result: AnalysisResult) -> AnalysisResult:
        created = _now()
        result.created_at = created
        cur = self.conn.execute(
            "INSERT INTO runs(brand_name, created_at, overall_score, result_json)"
            " VALUES (?,?,?,?)",
            (result.brand_name, created, result.overall_score, "{}"),
        )
        result.run_id = cur.lastrowid
        self.conn.execute(
            "UPDATE runs SET result_json=? WHERE id=?",
            (json.dumps(result.to_dict()), result.run_id),
        )
        self.conn.commit()
        return result

    def score_history(self, brand_name: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT id, created_at, overall_score FROM runs WHERE brand_name=?"
            " ORDER BY id",
            (brand_name,),
        ).fetchall()
        return [
            {"run_id": r["id"], "created_at": r["created_at"], "overall_score": r["overall_score"]}
            for r in rows
        ]

    def latest_result(self, brand_name: str) -> dict | None:
        row = self.conn.execute(
            "SELECT result_json FROM runs WHERE brand_name=? ORDER BY id DESC LIMIT 1",
            (brand_name,),
        ).fetchone()
        return json.loads(row["result_json"]) if row else None

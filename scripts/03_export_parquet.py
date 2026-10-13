#!/usr/bin/env python3
"""Write one Parquet file per table from the newest complete run: data/parquet/<stats_id>.parquet.

Each file holds the 47 prefectures of one table (rows ordered by prefecture, then mesh code),
the file's own columns as strings exactly as the source writes them (`*` marks a hidden
value), and a leading `prefecture` column from the file name. data/parquet/columns.json gives
each table's name, datum and the Japanese label of every column.

    uv run python scripts/03_export_parquet.py --version 2026-10-11
"""

import argparse
import json
import sys
from pathlib import Path

import estat_mesh as m
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).parents[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    args = ap.parse_args()
    raw = ROOT / "data" / "raw" / args.version
    manifest = json.loads((raw / "MANIFEST.json").read_text())
    out = ROOT / "data" / "parquet"
    out.mkdir(parents=True, exist_ok=True)
    by_table: dict[str, list[str]] = {}
    for key in sorted(manifest["files"]):
        by_table.setdefault(key.split("/")[0], []).append(key)
    info = {}
    for stats_id, keys in by_table.items():
        if len(keys) != 47:
            print(f"{stats_id}: {len(keys)} files, expected 47", file=sys.stderr)
            return 1
        ids: list[str] | None = None
        labels: list[str] = []
        cols: list[list[str]] = []
        prefs: list[str] = []
        for key in keys:
            code = key.removesuffix(".zip")[-2:]
            i, lab, rows = m.parse_table((raw / m.UNIT / key).read_bytes(), stats_id, code)
            if ids is None:
                ids, labels = i, lab
                cols = [[] for _ in ids]
            elif i != ids or lab != labels:
                print(f"{key}: columns differ from the first prefecture", file=sys.stderr)
                return 1
            for r in rows:
                for c, v in zip(cols, r, strict=True):
                    c.append(v)
            prefs += [code] * len(rows)
        assert ids is not None
        table = pa.table(
            [pa.array(prefs, pa.string()), *[pa.array(c, pa.string()) for c in cols]],
            names=["prefecture", *ids],
        )
        pq.write_table(table, out / f"{stats_id}.parquet", compression="zstd")
        t = manifest["tables"][next(k for k in manifest["tables"] if k.startswith(stats_id))]
        datum = manifest["files"][keys[0]]["datum"]
        info[stats_id] = {
            "name": t["name"],
            "datum": f"JGD{datum}",
            "rows": table.num_rows,
            "columns": dict(zip(ids, labels, strict=True)),
        }
        print(f"{stats_id} {table.num_rows:,} rows, {len(ids)} columns")
    (out / "columns.json").write_text(
        json.dumps(info, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

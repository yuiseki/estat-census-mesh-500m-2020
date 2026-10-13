#!/usr/bin/env python3
"""Check data/parquet/ against the zips: the same rows and values, table by table.

uv run python scripts/04_verify_parquet.py --version 2026-10-11
"""

import argparse
import json
import sys
from pathlib import Path

import estat_mesh as m
import pyarrow.parquet as pq

ROOT = Path(__file__).parents[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    args = ap.parse_args()
    raw = ROOT / "data" / "raw" / args.version
    manifest = json.loads((raw / "MANIFEST.json").read_text())
    info = json.loads((ROOT / "data" / "parquet" / "columns.json").read_text())
    errors = rows = 0
    for stats_id, meta in info.items():
        t = pq.read_table(ROOT / "data" / "parquet" / f"{stats_id}.parquet").to_pylist()
        keys = sorted(k for k in manifest["files"] if k.startswith(stats_id + "/"))
        expect = []
        for key in keys:
            code = key.removesuffix(".zip")[-2:]
            ids, _, body = m.parse_table((raw / m.UNIT / key).read_bytes(), stats_id, code)
            expect += [{"prefecture": code, **dict(zip(ids, r, strict=True))} for r in body]
        ok = t == expect and len(t) == meta["rows"]
        errors += not ok
        rows += len(t)
        print(f"{'ok ' if ok else 'BAD'} {stats_id} {len(t):,} rows")
    print(f"{len(info)} tables, {rows:,} rows, {errors} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

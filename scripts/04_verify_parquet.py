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
        pf = pq.ParquetFile(ROOT / "data" / "parquet" / f"{stats_id}.parquet")
        keys = sorted(k for k in manifest["files"] if k.startswith(stats_id + "/"))
        n = 0
        ok = pf.num_row_groups == len(keys)
        for g, key in enumerate(keys if ok else []):  # one row group per prefecture
            code = key.removesuffix(".zip")[-2:]
            ids, _, body = m.parse_table((raw / m.UNIT / key).read_bytes(), stats_id, code)
            want = [{"prefecture": code, **dict(zip(ids, r, strict=True))} for r in body]
            got = pf.read_row_group(g).to_pylist()
            ok = ok and got == want
            n += len(got)
        ok = ok and n == meta["rows"]
        errors += not ok
        rows += n
        print(f"{'ok ' if ok else 'BAD'} {stats_id} {n:,} rows")
    print(f"{len(info)} tables, {rows:,} rows, {errors} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

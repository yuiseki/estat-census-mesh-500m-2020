"""Check a run against its manifest, then compare the JGD2000 and JGD2011 tables.

Each zip is re-hashed and inspected again (one table file, a header naming the table, every
row as wide as the header, the row count the manifest recorded). Then, for each of the six
tables, the JGD2000 and JGD2011 files of every prefecture are compared: whether the values
are the same apart from the table id in the header line.
"""

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

import estat_mesh as m

ROOT = Path(__file__).parents[1]
# the six tables, as (JGD2000 id, JGD2011 id); the catalogue pairs them in listing order
PAIRS = [
    ("T001101", "T001141"), ("T001108", "T001144"), ("T001173", "T001192"),
    ("T001182", "T001193"), ("T001183", "T001194"), ("T001184", "T001195"),
]  # fmt: skip


def member(path: Path) -> bytes:
    with zipfile.ZipFile(path) as z:
        (name,) = [n for n in z.namelist() if not n.endswith("/")]
        return z.read(name)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    args = ap.parse_args()
    raw = ROOT / "data" / "raw" / args.version
    manifest = json.loads((raw / "MANIFEST.json").read_text())
    errors = 0
    rows = 0
    for key, entry in sorted(manifest["files"].items()):
        path = raw / m.UNIT / key
        stats_id, name = key.split("/")
        code = name.removesuffix(".zip")[-2:]
        data = path.read_bytes()
        try:
            info = m.inspect_zip(data, stats_id, code)
            ok = (
                hashlib.sha256(data).hexdigest() == entry["sha256"]
                and len(data) == entry["bytes"]
                and info.rows == entry["rows"]
            )
        except m.NotATable as err:
            print(f"BAD {key}: {err}")
            ok = False
        if not ok:
            print(f"MISMATCH {key}")
            errors += 1
        rows += entry["rows"]
    print(f"{len(manifest['files'])} files, {rows:,} rows, {errors} errors")
    same = differ = 0
    for a, b in PAIRS:
        for code in (f"{i:02d}" for i in range(1, 48)):
            pa, pb = (
                raw / m.UNIT / a / f"tbl{a}{m.UNIT}{code}.zip",
                raw / m.UNIT / b / f"tbl{b}{m.UNIT}{code}.zip",
            )
            if not (pa.exists() and pb.exists()):
                continue
            if m.same_values(member(pa), a, member(pb), b):
                same += 1
            else:
                differ += 1
                print(f"JGD2000 {a} and JGD2011 {b} differ in values: prefecture {code}")
    print(f"JGD2000 vs JGD2011: {same} pairs with the same values, {differ} that differ")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

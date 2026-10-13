#!/usr/bin/env python3
"""Write data/README.md (the Hub card), data/LICENSE and data/provenance.yaml.

Counts come from the manifest of the newest run under data/raw/ and from data/parquet/.

    uv run python scripts/05_card.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CC = "https://creativecommons.org/licenses/by/4.0/legalcode.ja"
TERMS = "https://www.e-stat.go.jp/terms-of-use"
Q_AND_A = "https://www.stat.go.jp/data/mesh/pdf/ryuijikou.pdf"
HELP = "https://www.e-stat.go.jp/help/data-definition-information/downloaddata/help_mesh_2011.pdf"
GIS_TERMS = "https://www.e-stat.go.jp/gis-terms"
PAGE = "https://www.e-stat.go.jp/gis/statmap-search?page=1&type=1&toukeiCode=00200521&toukeiYear=2020&aggregateUnit=S&serveyId=S002005112020&statsId=T001100"


def facts() -> dict:
    d = sorted((DATA / "raw").glob("*/MANIFEST.json"))[-1].parent
    m = json.loads((d / "MANIFEST.json").read_text())
    cols = json.loads((DATA / "parquet" / "columns.json").read_text())
    files = m["files"]
    return {
        "run": d.name,
        "files": len(files),
        "bytes": sum(v["bytes"] for v in files.values()),
        "rows": sum(v["rows"] for v in files.values()),
        "updated": sorted({v["listed_updated"] for v in files.values()}),
        "fetched": min(v["fetched_at"] for v in files.values())[:10],
        "cols": cols,
    }


def card(f: dict) -> str:
    tables = "\n".join(
        f"| `{k}` | {v['datum']} | {v['name']} | {len(v['columns'])} | {v['rows']:,} |"
        for k, v in f["cols"].items()
    )
    return f"""---
license: cc-by-4.0
license_name: cc-by-4.0
license_link: {CC}
language:
- ja
tags:
- census
- japan
- grid-square
- mesh
- population
- e-stat
pretty_name: 2020 Japan census, 1 km grid-square statistics
---

# estat-census-mesh-2020

The 2020 census (令和2年国勢調査) of Japan, tabulated by 3rd-order grid square (the 1 km
mesh, 基準地域メッシュ), as published by the Statistics Bureau of Japan through e-Stat's
statistical GIS. {len(f["cols"])} tables x 47 prefectures = {f["files"]} files, {f["rows"]:,}
rows, fetched on {f["fetched"]} (the source lists them as updated {", ".join(f["updated"])}).

Source: 政府統計の総合窓口 (e-Stat) 地図で見る統計 (統計GIS), <{PAGE}>.

Credit (出典): 政府統計の総合窓口(e-Stat) (https://www.e-stat.go.jp/), 「令和2年国勢調査」
(総務省統計局). The Parquet files are converted from the source files (encoding, one table per
file); credit them as 「令和2年国勢調査」(総務省統計局) を加工して作成.

## Two geodetic datums, two sets of tables

The source publishes every table twice: on JGD2000 and on JGD2011. The two are not the same
data. The Statistics Bureau says ({Q_AND_A}) that the same mesh code can cover a slightly
different area in the two datums, so results differ in 20 prefectures: Aomori, Iwate, Miyagi,
Akita, Yamagata, Fukushima, Ibaraki, Tochigi, Gunma, Saitama, Chiba, Tokyo, Kanagawa,
Niigata, Toyama, Ishikawa, Fukui, Yamanashi, Nagano and Gifu (codes 02 to 21). The cause is
the assignment of small areas to meshes (同定, {HELP}): a small area that lies inside one
mesh in JGD2000 may straddle two in JGD2011 and is then split between them in proportion.
This copy agrees with that list: in each of the six tables exactly those 20 prefectures
differ between the two versions (checked file by file), and in the total-population column
the number of differing meshes runs from 81 (Fukui) to 2,164 (Miyagi). Each prefecture's total
population is the same in both versions, so people are moved between meshes, not added.
Meshes with no
population have no record, so a few mesh codes exist in only one of the two versions.
Do not merge the two versions; choose one and keep to it. The Bureau's own summary pages
use JGD2000. The `datum` column of the table list below says which tables are which.

## Layout

```
raw/{f["run"]}/MANIFEST.json                 url, size, sha256, fetch time and row count of every file
raw/{f["run"]}/S/<table>/tbl<table>S<pref>.zip   {f["files"]} files, {f["bytes"] / 1e6:.0f} MB, exactly as e-Stat serves them
parquet/<table>.parquet                      one file per table, 47 prefectures each
parquet/columns.json                         each table's name, datum and the label of every column
```

The raw files are zips of one cp932 CSV each: a header line of column ids, a line of
Japanese column labels, then one row per mesh. `KEY_CODE` is the 8-digit mesh code.
`HTKSYORI`, `HTKSAKI` and `GASSAN` are the source's flags; in the files, `HTKSYORI` is
`0` for most rows and `2` for rows that carry the code of another mesh in `HTKSAKI`. The
Bureau's Q&A says that the values of a mesh too small to publish are hidden (`*`) and added
to a destination mesh whose values then are the sums, so a destination's breakdown does not
add up to its total; which flag column marks which is read from the files, not from a
definition sheet. `*` is a hidden value (the total population, households and household
members are never hidden). Meshes with no population have no row. The two averages
(mean age, median age) have one decimal place, and `Y` marks a breakdown whose ages are
unknown. The Parquet files hold the same
cells as strings (nothing is converted, so `*` is kept), with a `prefecture` column (the
two-digit code) in front.

| table | datum | name | columns | rows |
|---|---|---|---|---|
{tables}

## Licence

e-Stat's terms of use ({TERMS}) allow copying, redistribution and adaptation, including for
commercial use, on condition of the credit above and a note when the data has been
processed. The terms are compatible with CC BY 4.0, and the statistical GIS terms
({GIS_TERMS}, article 6) apply the same terms to the data it provides. This dataset is
therefore marked CC BY 4.0. The terms add that the government takes no responsibility for what
is done with the data, and that content may be changed or deleted without notice.

Collection code: <https://github.com/yuiseki/estat-census-mesh-2020> (MIT).
"""


def provenance(f: dict) -> str:
    return f"""source: 政府統計の総合窓口 (e-Stat) 統計GIS, 令和2年国勢調査, 3次メッシュ (1km)
url: {PAGE}
retrieved: {f["fetched"]}
run: {f["run"]}
terms: {TERMS}
files: {f["files"]}
rows: {f["rows"]}
"""


def main() -> int:
    f = facts()
    (DATA / "README.md").write_text(card(f), encoding="utf-8")
    (DATA / "provenance.yaml").write_text(provenance(f), encoding="utf-8")
    (DATA / "LICENSE").write_text(
        "Creative Commons Attribution 4.0 International (CC BY 4.0)\n"
        f"{CC}\n\n"
        "The data is the 2020 census grid-square statistics published by the Statistics Bureau\n"
        "of Japan through e-Stat. Credit: 政府統計の総合窓口(e-Stat) (https://www.e-stat.go.jp/),\n"
        "「令和2年国勢調査」(総務省統計局). The Parquet files are processed from the source:\n"
        "「令和2年国勢調査」(総務省統計局) を加工して作成.\n"
        f"e-Stat terms: {TERMS}\n",
        encoding="utf-8",
    )
    print(f"wrote data/README.md, LICENSE, provenance.yaml for run {f['run']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

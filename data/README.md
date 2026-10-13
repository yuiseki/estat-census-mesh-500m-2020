---
license: cc-by-4.0
license_name: cc-by-4.0
license_link: https://creativecommons.org/licenses/by/4.0/legalcode.ja
language:
- ja
tags:
- census
- japan
- grid-square
- mesh
- population
- e-stat
pretty_name: 2020 Japan census, 500m grid-square statistics
---

# estat-census-mesh-500m-2020

The 2020 census (令和2年国勢調査) of Japan, tabulated by grid square of 500m
(the 2分の1地域メッシュ, a quarter of a 1 km mesh), as published by the Statistics Bureau of Japan through e-Stat's
statistical GIS. 12 tables x 47 prefectures = 564 files, 5,604,594
rows, fetched on 2026-10-13 (the source lists them as updated 2025-10-09).

Source: 政府統計の総合窓口 (e-Stat) 地図で見る統計 (統計GIS), <https://www.e-stat.go.jp/gis/statmap-search?page=1&type=1&toukeiCode=00200521&toukeiYear=2020&aggregateUnit=H&serveyId=H002005112020&statsId=T001101>.

Credit (出典): 政府統計の総合窓口(e-Stat) (https://www.e-stat.go.jp/), 「令和2年国勢調査」
(総務省統計局). The Parquet files are converted from the source files (encoding, one table per
file); credit them as 「令和2年国勢調査」(総務省統計局) を加工して作成.

## Two geodetic datums, two sets of tables

The source publishes every table twice: on JGD2000 and on JGD2011. The two are not the same
data. The Statistics Bureau says (https://www.stat.go.jp/data/mesh/pdf/ryuijikou.pdf) that the same mesh code can cover a slightly
different area in the two datums, so results differ in 20 prefectures: Aomori, Iwate, Miyagi,
Akita, Yamagata, Fukushima, Ibaraki, Tochigi, Gunma, Saitama, Chiba, Tokyo, Kanagawa,
Niigata, Toyama, Ishikawa, Fukui, Yamanashi, Nagano and Gifu (codes 02 to 21). The cause is
the assignment of small areas to meshes (同定, https://www.e-stat.go.jp/help/data-definition-information/downloaddata/help_mesh_2011.pdf): a small area that lies inside one
mesh in JGD2000 may straddle two in JGD2011 and is then split between them in proportion.
This copy agrees with that list: in each of the six tables exactly those 20 prefectures
differ between the two versions (checked file by file), and in the total-population column
the number of differing meshes runs from 214 (Fukui) to 5,137 (Miyagi). Each prefecture's total
population is the same in both versions, so people are moved between meshes, not added.
Meshes with no
population have no record, so a few mesh codes exist in only one of the two versions.
Do not merge the two versions; choose one and keep to it. The Bureau's own summary pages
use JGD2000. The `datum` column of the table list below says which tables are which.

## Layout

```
raw/2026-10-13/MANIFEST.json                 url, size, sha256, fetch time and row count of every file
raw/2026-10-13/H/<table>/tbl<table>H<pref>.zip   564 files, 252 MB, exactly as e-Stat serves them
parquet/<table>.parquet                      one file per table, 47 prefectures each
parquet/columns.json                         each table's name, datum and the label of every column
```

The raw files are zips of one cp932 CSV each: a header line of column ids, a line of
Japanese column labels, then one row per mesh. `KEY_CODE` is the mesh code.
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
| `T001101` | JGD2000 | 人口及び世帯 （JGD2000） | 54 | 467,053 |
| `T001108` | JGD2000 | 人口移動、就業状態等及び従業地・通学地 （JGD2000） | 98 | 467,053 |
| `T001141` | JGD2011 | 人口及び世帯 （JGD2011） | 54 | 467,046 |
| `T001144` | JGD2011 | 人口移動、就業状態等及び従業地・通学地 （JGD2011） | 98 | 467,046 |
| `T001173` | JGD2000 | ５歳階級別人口（JGD2000） | 69 | 467,053 |
| `T001182` | JGD2000 | 労働力状態、産業分類及び職業分類別人口（１５歳以上）（JGD2000） | 115 | 467,053 |
| `T001183` | JGD2000 | 住宅の所有及び建て方（JGD2000） | 25 | 467,053 |
| `T001184` | JGD2000 | ５年前の常住地及び従業地・通学地等（JGD2000） | 124 | 467,053 |
| `T001192` | JGD2011 | ５歳階級別人口（JGD2011） | 69 | 467,046 |
| `T001193` | JGD2011 | 労働力状態、産業分類及び職業分類別人口（１５歳以上）（JGD2011） | 115 | 467,046 |
| `T001194` | JGD2011 | 住宅の所有及び建て方（JGD2011） | 25 | 467,046 |
| `T001195` | JGD2011 | ５年前の常住地及び従業地・通学地等（JGD2011） | 124 | 467,046 |

## Licence

e-Stat's terms of use (https://www.e-stat.go.jp/terms-of-use) allow copying, redistribution and adaptation, including for
commercial use, on condition of the credit above and a note when the data has been
processed. The terms are compatible with CC BY 4.0, and the statistical GIS terms
(https://www.e-stat.go.jp/gis-terms, article 6) apply the same terms to the data it provides. This dataset is
therefore marked CC BY 4.0. The terms add that the government takes no responsibility for what
is done with the data, and that content may be changed or deleted without notice.

Collection code: <https://github.com/yuiseki/estat-census-mesh-500m-2020> (MIT).

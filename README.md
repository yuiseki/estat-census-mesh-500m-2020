# estat-census-mesh-2020

A reproducible copy of the 2020 census (令和2年国勢調査) of Japan tabulated by 1 km
grid square, from the statistical GIS of e-Stat (政府統計の総合窓口). The Hugging Face
dataset is <https://huggingface.co/datasets/yuiseki/estat-census-mesh-2020>.

## Source

<https://www.e-stat.go.jp/gis/statmap-search?page=1&type=1&toukeiCode=00200521&toukeiYear=2020&aggregateUnit=S&serveyId=S002005112020&statsId=T001100>

Six tables, each published on JGD2000 and on JGD2011, one zip per prefecture
(12 x 47 = 564 files). The two datums are not the same data; keep them apart.
The source overwrites files in place, so the version of a copy is the UTC date it
was fetched.

## Run

```
uv run python scripts/01_download.py            # data/raw/<date>/, about 10 minutes, 1 s between requests
uv run python scripts/02_verify.py --version <date>
uv run python scripts/03_export_parquet.py --version <date>
uv run python scripts/04_verify_parquet.py --version <date>
uv run python scripts/05_card.py                # data/README.md, LICENSE, provenance.yaml
uv run python src/publish.py                    # dry run; --push uploads
uv run pytest
```

## Licence

Code: MIT. Data: e-Stat's terms of use, compatible with CC BY 4.0; see `data/LICENSE`.

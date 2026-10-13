"""Parsing and checks for the 2020 census grid-square statistics of e-Stat's statistical GIS.

The listing is the JSON that https://www.e-stat.go.jp/gis/statmap-search/search_detail returns
(its values are HTML fragments); this module reads those fragments and checks the zips. It
does no network I/O.
"""

import csv
import io
import re
import zipfile
from dataclasses import dataclass
from html import unescape

BASE = "https://www.e-stat.go.jp/gis/statmap-search"
TOUKEI_CODE = "00200521"  # 国勢調査
YEAR = "2020"
UNIT = "H"  # 500m mesh
SERVEY_ID = "H002005112020"
SEARCH_FLAGS = "mesh_data_flg=1&facet_flg=1&all_count_flg=1&show_child_item=1&show_child2_item=1"


class NotATable(ValueError):
    pass


@dataclass(frozen=True)
class Table:
    stats_id: str
    datum: str
    name: str
    prefecture_updated: str


@dataclass(frozen=True)
class ListedFile:
    stats_id: str
    code: str
    name: str
    updated: str


@dataclass(frozen=True)
class ZipInfo:
    member: str
    rows: int
    columns: list[str]


def text(fragment: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", unescape(fragment))).strip()


def catalogue_url() -> str:
    return (
        f"{BASE}/search_detail?page=1&type=1&toukeiCode={TOUKEI_CODE}&toukeiYear={YEAR}"
        f"&aggregateUnit={UNIT}&{SEARCH_FLAGS}"
    )


def listing_url(stats_id: str, datum: str, page: int) -> str:
    return (
        f"{BASE}/search_detail?type=1&toukeiCode={TOUKEI_CODE}&toukeiYear={YEAR}"
        f"&aggregateUnit={UNIT}&serveyId={SERVEY_ID}&statsId={stats_id}&datum={datum}"
        f"&{SEARCH_FLAGS}&download_disp_flg=1&by_prefecture_flg=1&page={page}"
    )


def download_url(stats_id: str, code: str) -> str:
    return f"{BASE}/data?statsId={stats_id}&code={code}&downloadType=2"


def catalogue_tables(detail: str, servey_id: str) -> list[Table]:
    """The tables of one survey in the catalogue, in the order the page lists them.

    Each table is a row with its name and date, then two child rows: the 80 km mesh units
    and the prefectures. The prefecture row carries `by_prefecture_flg=1`.
    """
    page = unescape(detail)
    pattern = re.compile(
        r'<span class="stat-title-has-child"[^>]*>\s*(?P<name>[^<]+?)\s*</span>'
        r"(?:(?!stat-title-has-child).)*?"
        rf"serveyId={re.escape(servey_id)}&statsId=(?P<stats>T\d+)&datum=(?P<datum>\d+)\""
        r"(?:(?!stat-title-has-child).)*?"
        rf"serveyId={re.escape(servey_id)}&statsId=(?P=stats)&datum=(?P=datum)&by_prefecture_flg=1\""
        r"[^>]*>\s*都道府県\s*</a>\s*<span class=\"stat-date\"[^>]*>\s*(?P<date>[\d-]+)\s*</span>",
        re.S,
    )
    return [
        Table(m["stats"], m["datum"], re.sub(r"\s+", " ", m["name"]), m["date"])
        for m in pattern.finditer(page)
    ]


def listing_files(detail: str) -> list[ListedFile]:
    page = unescape(detail)
    out = []
    for article in re.findall(r"<article.*?</article>", page, re.S):
        items = [
            text(x)
            for x in re.findall(
                r"<li class=\"stat-resorce_list-detail-item[^>]*>(.*?)</li>", article, re.S
            )
        ]
        link = re.search(r"data\?statsId=(T\d+)&code=(\w+)&downloadType=2", article)
        if link and len(items) >= 3:
            out.append(ListedFile(link[1], link[2], items[1], items[2]))
    return out


def listing_pages(paginate: str) -> int:
    found = re.search(r"/\s*(\d+)\s*ページ", text(paginate))
    return int(found[1]) if found else 1


def inspect_zip(data: bytes, stats_id: str, code: str) -> ZipInfo:
    """Check a downloaded zip: one `tbl<id>H<code>.txt` in cp932 CSV, a header naming the table,
    a Japanese description line, and every data row as wide as the header. Raises NotATable."""
    if data[:4] != b"PK\x03\x04":
        raise NotATable(f"not a zip ({len(data)} bytes, starts {data[:30]!r})")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = [n for n in z.namelist() if not n.endswith("/")]
        want = f"tbl{stats_id}{UNIT}{code}.txt"
        if names != [want]:
            raise NotATable(f"expected [{want!r}], got {names}")
        raw = z.read(want)
    try:
        rows = list(csv.reader(io.StringIO(raw.decode("cp932"), newline="")))
    except UnicodeDecodeError as err:
        raise NotATable(f"{want} is not cp932: {err}") from err
    if len(rows) < 2:
        raise NotATable(f"{want} has {len(rows)} lines")
    columns = rows[0]
    if columns[:4] != ["KEY_CODE", "HTKSYORI", "HTKSAKI", "GASSAN"]:
        raise NotATable(f"unexpected header start {columns[:4]}")
    if not all(c.startswith(stats_id) for c in columns[4:]) or len(columns) < 5:
        raise NotATable(f"header does not name table {stats_id}")
    bad = [i for i, r in enumerate(rows, 1) if len(r) != len(columns)]
    if bad:
        raise NotATable(
            f"{len(bad)} lines are not {len(columns)} fields wide, first at line {bad[0]}"
        )
    return ZipInfo(want, len(rows) - 2, columns)


def same_values(a: bytes, a_id: str, b: bytes, b_id: str) -> bool:
    """Whether two table files differ only in the table id of their header line."""
    head_a, _, rest_a = a.partition(b"\n")
    head_b, _, rest_b = b.partition(b"\n")
    return head_a.replace(a_id.encode(), b_id.encode()) == head_b and rest_a == rest_b


def parse_table(
    data: bytes, stats_id: str, code: str
) -> tuple[list[str], list[str], list[list[str]]]:
    """(column ids, their Japanese labels, data rows) of a downloaded zip, every value as the
    string the file holds (`*` is the source's mark for a hidden value). Raises NotATable."""
    inspect_zip(data, stats_id, code)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        (name,) = [n for n in z.namelist() if not n.endswith("/")]
        rows = list(csv.reader(io.StringIO(z.read(name).decode("cp932"), newline="")))
    return rows[0], [c.strip("　 ") for c in rows[1]], rows[2:]

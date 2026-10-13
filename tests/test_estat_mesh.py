import io
import zipfile
from pathlib import Path

import estat_mesh as m
import pytest

FIX = Path(__file__).parent / "fixtures"


def read(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


def test_catalogue_lists_six_tables_per_datum():
    tables = m.catalogue_tables(read("catalogue_1km.html"), "S002005112020")
    assert len(tables) == 12
    assert [t.stats_id for t in tables if t.datum == "2000"] == [
        "T001100", "T001107", "T001171", "T001179", "T001180", "T001181",
    ]  # fmt: skip
    assert [t.stats_id for t in tables if t.datum == "2011"] == [
        "T001140", "T001143", "T001188", "T001189", "T001190", "T001191",
    ]  # fmt: skip


def test_catalogue_table_carries_name_and_prefecture_date():
    first = m.catalogue_tables(read("catalogue_1km.html"), "S002005112020")[0]
    assert first.name == "人口及び世帯 （JGD2000）"
    assert first.prefecture_updated == "2025-10-09"


def test_catalogue_ignores_other_surveys():
    assert m.catalogue_tables(read("catalogue_1km.html"), "S999999999999") == []


def test_listing_gives_code_name_date_per_prefecture():
    rows = m.listing_files(read("listing_page3.html"))
    assert [r.code for r in rows] == ["41", "42", "43", "44", "45", "46", "47"]
    assert rows[0].name == "41 佐賀県"
    assert rows[0].updated == "2025-10-09"
    assert rows[0].stats_id == "T001100"


def test_listing_pages():
    assert m.listing_pages(read("paginate_page1.html")) == 3
    assert m.listing_pages(read("paginate_page3.html")) == 3
    assert m.listing_pages("") == 1


def test_download_url():
    assert m.download_url("T001100", "22") == (
        "https://www.e-stat.go.jp/gis/statmap-search/data?statsId=T001100&code=22&downloadType=2"
    )


def test_listing_url_asks_for_the_prefecture_listing_page():
    url = m.listing_url("T001100", "2011", 2)
    assert "by_prefecture_flg=1" in url and "page=2" in url
    assert "statsId=T001100" in url and "datum=2011" in url
    assert "mesh_data_flg=1" in url and "download_disp_flg=1" in url


def zip_of(name: str, payload: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(name, payload)
    return buf.getvalue()


def test_inspect_reads_one_txt_and_counts_rows():
    sample = (FIX / "sample_T001100.txt").read_bytes()
    info = m.inspect_zip(zip_of(f"tblT001100{m.UNIT}22.txt", sample), "T001100", "22")
    assert info.member == f"tblT001100{m.UNIT}22.txt"
    assert info.rows == 3  # five lines: header, description, three data rows
    assert info.columns[0] == "KEY_CODE" and info.columns[4] == "T001100001"


def test_inspect_rejects_html_and_wrong_names():
    with pytest.raises(m.NotATable):
        m.inspect_zip(b"<html>error</html>", "T001100", "22")
    with pytest.raises(m.NotATable):
        m.inspect_zip(zip_of("other.txt", b"KEY_CODE\r\n"), "T001100", "22")


def test_inspect_rejects_a_header_that_is_not_the_requested_table():
    bad = b"KEY_CODE,HTKSYORI,HTKSAKI,GASSAN,T009999001\r\n,,,,x\r\n"
    with pytest.raises(m.NotATable):
        m.inspect_zip(zip_of("tblT001100S22.txt", bad), "T001100", "22")


def test_inspect_rejects_ragged_rows():
    sample = (FIX / "sample_T001100.txt").read_bytes().rstrip(b"\r\n") + b"\r\n1,2\r\n"
    with pytest.raises(m.NotATable):
        m.inspect_zip(zip_of(f"tblT001100{m.UNIT}22.txt", sample), "T001100", "22")


def test_same_values_ignores_the_table_id_in_the_header():
    a = b"KEY_CODE,T001100001\r\n,x\r\n1,5\r\n"
    b = b"KEY_CODE,T001140001\r\n,x\r\n1,5\r\n"
    c = b"KEY_CODE,T001140001\r\n,x\r\n1,6\r\n"
    assert m.same_values(a, "T001100", b, "T001140")
    assert not m.same_values(a, "T001100", c, "T001140")


def make_zip(stats_id: str, code: str, body: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(f"tbl{stats_id}{m.UNIT}{code}.txt", body.encode("cp932"))
    return buf.getvalue()


def test_parse_table_keeps_values_as_strings_and_strips_label_padding():
    body = (
        "KEY_CODE,HTKSYORI,HTKSAKI,GASSAN,T0011001\n"
        ",,,,　人口（総数）\n"
        "51377598,0,,,*\n"
        "51377599,2,51377598,,12\n"
    )
    ids, labels, rows = m.parse_table(make_zip("T001100", "22", body), "T001100", "22")
    assert ids[4:] == ["T0011001"]
    assert labels[4:] == ["人口（総数）"]
    assert rows == [["51377598", "0", "", "", "*"], ["51377599", "2", "51377598", "", "12"]]

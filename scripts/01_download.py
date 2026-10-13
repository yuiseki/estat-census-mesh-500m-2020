"""Download the 2020 census 1 km grid-square statistics (e-Stat statistical GIS) by prefecture.

Reads the catalogue for the survey, lists the 47 prefecture files of each of its twelve tables
(six tables, JGD2000 and JGD2011), downloads each zip, checks it, and records it in
data/raw/<version>/MANIFEST.json. A file already in the manifest whose sha256 still matches is
not fetched again. The version is the UTC date of the first run; --version resumes another.
"""

import argparse
import datetime as dt
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import estat_mesh as m

ROOT = Path(__file__).parents[1]
UA = "estat-census-mesh-2020/0.1 (+https://github.com/yuiseki/estat-census-mesh-2020)"
PAUSE = 1.0
CODES = [f"{i:02d}" for i in range(1, 48)]


def log(msg: str) -> None:
    print(f"[{dt.datetime.now():%H:%M:%S}] {msg}", flush=True)


class Pushback(RuntimeError):
    """The server refused (403 or 429): stop rather than retry."""


def get(url: str, tries: int = 3) -> tuple[bytes, dict[str, str]]:
    for attempt in range(1, tries + 1):
        time.sleep(PAUSE)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read(), {k.lower(): v for k, v in r.headers.items()}
        except urllib.error.HTTPError as err:
            if err.code in (403, 429):
                raise Pushback(f"HTTP {err.code} for {url}") from err
            log(f"HTTP {err.code} for {url} (try {attempt}/{tries})")
        except (urllib.error.URLError, TimeoutError) as err:
            log(f"{err} for {url} (try {attempt}/{tries})")
        time.sleep(5 * attempt)
    raise RuntimeError(f"gave up on {url}")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part")
    part.write_bytes(data)
    part.replace(path)


def detail(url: str, raw_dir: Path, name: str) -> tuple[str, str]:
    """The `detail` and `paginate` fragments of a search_detail answer; the JSON is kept."""
    body, _ = get(url)
    write_atomic(raw_dir / "listings" / name, body)
    obj = json.loads(body)
    return obj["detail"], obj.get("paginate", "")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default=dt.datetime.now(dt.UTC).strftime("%Y-%m-%d"))
    ap.add_argument("--only", help="a statsId, to fetch one table")
    args = ap.parse_args()
    raw = ROOT / "data" / "raw" / args.version
    manifest_path = raw / "MANIFEST.json"
    manifest = (
        json.loads(manifest_path.read_text())
        if manifest_path.exists()
        else {"survey": m.SERVEY_ID, "files": {}, "failed": {}}
    )

    def save() -> None:
        write_atomic(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=1).encode())

    cat, _ = detail(m.catalogue_url(), raw, "catalogue.json")
    tables = m.catalogue_tables(cat, m.SERVEY_ID)
    if len(tables) != 12:
        log(f"catalogue lists {len(tables)} tables, expected 12")
        return 2
    manifest["tables"] = {
        f"{t.stats_id}-{t.datum}": {"name": t.name, "prefecture_updated": t.prefecture_updated}
        for t in tables
    }
    save()
    manifest["failed"] = {}
    for t in tables:
        if args.only and t.stats_id != args.only:
            continue
        listed: dict[str, m.ListedFile] = {}
        page, pages = 1, 1
        while page <= pages:
            frag, pag = detail(
                m.listing_url(t.stats_id, t.datum, page), raw, f"{t.stats_id}_{page}.json"
            )
            pages = m.listing_pages(pag)
            listed |= {f.code: f for f in m.listing_files(frag)}
            page += 1
        if sorted(listed) != CODES:
            log(f"{t.stats_id}: listing has {len(listed)} files, not the 47 prefectures")
            manifest["failed"][t.stats_id] = "listing is not 47 prefectures"
            continue
        for code in CODES:
            f = listed[code]
            key = f"{t.stats_id}/tbl{t.stats_id}{m.UNIT}{code}.zip"
            path = raw / m.UNIT / key
            have = manifest["files"].get(key)
            if have and path.exists() and sha256(path.read_bytes()) == have["sha256"]:
                continue
            url = m.download_url(t.stats_id, code)
            try:
                data, headers = get(url)
                info = m.inspect_zip(data, t.stats_id, code)
            except (m.NotATable, RuntimeError) as err:
                log(f"FAILED {key}: {err}")
                manifest["failed"][key] = str(err)
                save()
                continue
            write_atomic(path, data)
            manifest["files"][key] = {
                "url": url,
                "datum": t.datum,
                "table": t.name,
                "prefecture": f.name,
                "listed_updated": f.updated,
                "bytes": len(data),
                "sha256": sha256(data),
                "last_modified": headers.get("last-modified"),
                "fetched_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
                "member": info.member,
                "rows": info.rows,
                "columns": len(info.columns),
            }
            save()
            log(f"{key}  {len(data):,} bytes  {info.rows:,} rows")
    save()
    failed = len(manifest["failed"])
    log(f"{len(manifest['files'])} files, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Pushback as err:
        log(f"STOPPED: {err}")
        sys.exit(3)

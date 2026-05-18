#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["requests", "platformdirs"]
# ///
"""
Collect LLM metadata from multiple sources into a local XDG cache.

Sources (each runnable independently):
  hf     Hugging Face Hub API — paginated JSON, filtered to text-generation
  epoch  Epoch AI "Notable AI Models" dataset (CSV)
  aa     Artificial Analysis (JSON if ARTIFICIAL_ANALYSIS_API_KEY is set,
         otherwise the public HTML models page)

Examples:
  ./collect.py hf
  ./collect.py epoch
  ./collect.py all --force

Raw responses are written atomically under:
  $XDG_CACHE_HOME/localai-kith-2025/raw/<source>/<date>/...

Re-running on the same day is a no-op unless --force is given.
"""

import argparse
import datetime
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlencode

import requests
from platformdirs import user_cache_dir

APP_NAME = "localai-kith-2025"
UA = f"{APP_NAME}/0.1 (+https://github.com/miku/localai-kith-2025)"


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write `data` to `path` atomically via a sibling .tmp file + os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)


def fetch_cached(url: str, path: Path, *, headers=None, force=False, timeout=60) -> Path:
    """GET `url` once and cache the body at `path`. Skip if already cached."""
    if path.exists() and not force:
        print(f"  cached: {path}", file=sys.stderr)
        return path
    print(f"  GET {url}", file=sys.stderr)
    r = requests.get(url, headers={"User-Agent": UA, **(headers or {})}, timeout=timeout)
    r.raise_for_status()
    atomic_write_bytes(path, r.content)
    return path


# --- Hugging Face -----------------------------------------------------------

HF_API = "https://huggingface.co/api/models"
HF_WEB = "https://huggingface.co/models"
HF_TAGS_API = "https://huggingface.co/api/models-tags-by-type"

# HF doesn't expose a total via its public API (X-Total-Count is advertised in
# access-control-expose-headers but never actually set). The website renders
# the figure into the page as HTML-entity-escaped JSON, e.g.
#   &quot;numTotalItems&quot;:2884775
_HF_COUNT_RE = re.compile(r"&quot;numTotalItems&quot;:(\d+)")


def _hf_count_from_html(params: dict) -> int | None:
    """One GET to huggingface.co/models?<params>, parse numTotalItems."""
    url = f"{HF_WEB}?{urlencode(params)}" if params else HF_WEB
    print(f"  GET {url}", file=sys.stderr)
    r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
    r.raise_for_status()
    m = _HF_COUNT_RE.search(r.text)
    return int(m.group(1)) if m else None


def fetch_huggingface_count(pipeline_tag: str | None = None) -> int | None:
    """Best-effort: read numTotalItems from the rendered /models HTML page."""
    return _hf_count_from_html({"pipeline_tag": pipeline_tag} if pipeline_tag else {})


HF_DERIVATION_RELS = ("finetune", "quantized", "adapter", "merge")


def _hf_record_relations(tags: list[str]) -> tuple[set[str], bool]:
    """Inspect a record's tags; return (relations_set, has_plain_base_model).

    Mirrors normalize._parse_hf_base_model but keeps all relations (a single
    record can carry multiple, e.g. quantized merge).
    """
    rels: set[str] = set()
    plain = False
    for t in tags:
        if not t.startswith("base_model:"):
            continue
        parts = t.split(":")
        if len(parts) >= 3 and parts[1] in HF_DERIVATION_RELS:
            rels.add(parts[1])
        elif len(parts) == 2:
            plain = True
    return rels, plain


def summarize_huggingface_derivations(cache_dir: Path, date: str,
                                      pipeline_tag: str = "text-generation") -> dict:
    """Walk cached raw pages for <date>/<pipeline_tag> and tally lineage."""
    src_dir = cache_dir / "raw" / "huggingface" / date
    pages = sorted(src_dir.glob(f"models-{pipeline_tag}-page-*.json"))
    if not pages:
        sys.exit(f"no cached pages for pipeline_tag={pipeline_tag} at {src_dir}")
    total = 0
    standalone = 0
    derived = 0
    rel_counts = {r: 0 for r in HF_DERIVATION_RELS}
    plain_only = 0  # has base_model:<id> but no relation-bearing tag
    multi_rel = 0
    combo_counts: dict[tuple, int] = {}
    for p in pages:
        with open(p) as f:
            batch = json.load(f)
        for rec in batch:
            total += 1
            rels, plain = _hf_record_relations(rec.get("tags") or [])
            if not rels and not plain:
                standalone += 1
                continue
            derived += 1
            for r in rels:
                rel_counts[r] += 1
            if rels:
                key = tuple(sorted(rels))
                combo_counts[key] = combo_counts.get(key, 0) + 1
                if len(rels) > 1:
                    multi_rel += 1
            else:
                plain_only += 1
    return {
        "date": date,
        "pipeline_tag": pipeline_tag,
        "total": total,
        "standalone": standalone,
        "derived": derived,
        "rel_counts": rel_counts,
        "plain_only": plain_only,
        "multi_rel": multi_rel,
        "combo_counts": combo_counts,
    }


_SINCE_RE = re.compile(r"^(\d+)([dwmy])$")


def parse_since(spec: str) -> datetime.date:
    """Parse YYYY-MM-DD or a relative spec like 30d / 4w / 6m / 1y."""
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", spec):
        return datetime.date.fromisoformat(spec)
    m = _SINCE_RE.fullmatch(spec)
    if not m:
        raise ValueError(f"--since: expected YYYY-MM-DD or Nd/Nw/Nm/Ny, got {spec!r}")
    n, unit = int(m.group(1)), m.group(2)
    days = {"d": 1, "w": 7, "m": 30, "y": 365}[unit] * n
    return datetime.date.today() - datetime.timedelta(days=days)


def top_huggingface_by_downloads(cache_dir: Path, date: str, *,
                                 pipeline_tag: str = "text-generation",
                                 limit: int = 20,
                                 since: datetime.date | None = None) -> list[dict]:
    """Rank cached records by `downloads`. Returns the top `limit` rows.

    If `since` is set, drop records whose createdAt is older than `since`.
    """
    src_dir = cache_dir / "raw" / "huggingface" / date
    pages = sorted(src_dir.glob(f"models-{pipeline_tag}-page-*.json"))
    if not pages:
        sys.exit(f"no cached pages for pipeline_tag={pipeline_tag} at {src_dir}")
    rows = []
    since_str = since.isoformat() if since else None
    for p in pages:
        with open(p) as f:
            batch = json.load(f)
        for rec in batch:
            created = (rec.get("createdAt") or "")[:10]
            if since_str and (not created or created < since_str):
                continue
            rels, plain = _hf_record_relations(rec.get("tags") or [])
            if rels:
                lineage = "+".join(sorted(rels))
            elif plain:
                lineage = "derived"
            else:
                lineage = "-"
            rows.append({
                "id": rec.get("id"),
                "downloads": rec.get("downloads") or 0,
                "likes": rec.get("likes") or 0,
                "release_date": created or "-",
                "lineage": lineage,
            })
    rows.sort(key=lambda r: r["downloads"], reverse=True)
    return rows[:limit]


def fetch_huggingface_derivation_counts(base_id: str, *, delay: float = 0.5) -> dict[str, int | None]:
    """Per-relation derivation counts for a given base model id.

    Uses the website filter `?other=base_model:<rel>:<id>` (one HTTP GET per
    relation type, four total). The API itself doesn't expose a wildcard
    filter for base_model:*, so this is the cheapest authoritative path.
    """
    counts: dict[str, int | None] = {}
    for rel in HF_DERIVATION_RELS:
        counts[rel] = _hf_count_from_html({"other": f"base_model:{rel}:{base_id}"})
        time.sleep(delay)
    return counts


def fetch_huggingface_pipeline_tags() -> list[dict]:
    """Return the canonical list of pipeline_tag entries from HF.

    Each entry has keys: id, label, type, subType (e.g. nlp, cv, audio, ...).
    """
    print(f"  GET {HF_TAGS_API}", file=sys.stderr)
    r = requests.get(HF_TAGS_API, headers={"User-Agent": UA}, timeout=30)
    r.raise_for_status()
    return r.json().get("pipeline_tag", [])


def fetch_huggingface_pipeline_tag_counts(cache_dir: Path, tag_ids: list[str],
                                          *, force=False, delay=1.0) -> dict[str, int | None]:
    """Return {tag_id: count}, one HTTP request per tag. Cached per-day.

    The cache file is rewritten atomically after each fetch, so a Ctrl-C
    keeps partial progress and the next run resumes the remaining tags.
    """
    date = datetime.date.today().isoformat()
    out = cache_dir / "raw" / "huggingface" / date / "pipeline-tag-counts.json"
    counts: dict[str, int | None] = {}
    if out.exists() and not force:
        with open(out) as f:
            counts = json.load(f)
    pending = [t for t in tag_ids if force or t not in counts]
    print(f"  fetching counts for {len(pending)}/{len(tag_ids)} tag(s)", file=sys.stderr)
    for i, tid in enumerate(pending, 1):
        n = fetch_huggingface_count(pipeline_tag=tid)
        counts[tid] = n
        atomic_write_bytes(out, (json.dumps(counts, sort_keys=True, indent=2) + "\n").encode())
        print(f"  [{i}/{len(pending)}] {tid}: {n}", file=sys.stderr)
        if i < len(pending):
            time.sleep(delay)
    return counts


def fetch_huggingface(cache_dir: Path, *, force=False, max_pages=20,
                      page_size=100, delay=1.0, pipeline_tag="text-generation") -> Path:
    """
    List models from the HF Hub API, sorted by downloads.

    Paginates via the RFC 5988 Link header (HF deprecated ?skip=). Each page
    is cached as two files: the JSON body and a .next companion holding the
    next-page URL (or null at end-of-stream), so re-runs resume without
    re-fetching. Default 1.0s delay keeps us under the anonymous limit
    (~1000 req / 5min).
    """
    date = datetime.date.today().isoformat()
    out_dir = cache_dir / "raw" / "huggingface" / date
    headers = {"User-Agent": UA}
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    initial_params = {
        "pipeline_tag": pipeline_tag,
        "sort": "downloads",
        "direction": "-1",
        "limit": page_size,
        "full": "true",  # include cardData, tags, license, etc.
    }
    url = f"{HF_API}?{urlencode(initial_params)}"

    page = 0
    total = 0
    while url and page < max_pages:
        page_path = out_dir / f"models-{pipeline_tag}-page-{page:03d}.json"
        next_path = out_dir / f"models-{pipeline_tag}-page-{page:03d}.next"
        if page_path.exists() and next_path.exists() and not force:
            with open(page_path) as f:
                batch = json.load(f)
            with open(next_path) as f:
                next_url = json.load(f)
            print(f"  cached: {page_path} ({len(batch)} models)", file=sys.stderr)
        else:
            print(f"  GET {url}", file=sys.stderr)
            r = requests.get(url, headers=headers, timeout=60)
            r.raise_for_status()
            atomic_write_bytes(page_path, r.content)
            next_url = r.links.get("next", {}).get("url")
            atomic_write_bytes(next_path, json.dumps(next_url).encode())
            batch = r.json()
            time.sleep(delay)
        total += len(batch)
        if not batch:
            break
        url = next_url
        page += 1
    print(f"  hf: {total} models across {page} page(s) in {out_dir}", file=sys.stderr)
    return out_dir


# --- Epoch AI ---------------------------------------------------------------

# Epoch publishes "Notable AI Models" as CSV; URL is taken from the Download
# link on https://epoch.ai/data/notable-ai-models. Adjust if they move it.
EPOCH_CSV_URL = "https://epoch.ai/data/notable_ai_models.csv"


def fetch_epoch(cache_dir: Path, *, force=False) -> Path:
    date = datetime.date.today().isoformat()
    out = cache_dir / "raw" / "epoch" / f"{date}-notable_ai_models.csv"
    return fetch_cached(EPOCH_CSV_URL, out, force=force)


# --- Artificial Analysis ----------------------------------------------------

AA_API_URL = "https://api.artificialanalysis.ai/v2/data/llms/models"
AA_HTML_URL = "https://artificialanalysis.ai/models"


def fetch_artificial_analysis(cache_dir: Path, *, force=False) -> Path:
    """
    Use the official API when ARTIFICIAL_ANALYSIS_API_KEY is set; otherwise
    fall back to caching the public HTML page (their Next.js bundle embeds
    model data in a __NEXT_DATA__ JSON blob that downstream parsers can read).
    """
    date = datetime.date.today().isoformat()
    api_key = os.environ.get("ARTIFICIAL_ANALYSIS_API_KEY")
    if api_key:
        out = cache_dir / "raw" / "artificial_analysis" / f"{date}-models.json"
        return fetch_cached(AA_API_URL, out, headers={"x-api-key": api_key}, force=force)
    print("  aa: no ARTIFICIAL_ANALYSIS_API_KEY set, caching HTML page", file=sys.stderr)
    out = cache_dir / "raw" / "artificial_analysis" / f"{date}-models.html"
    return fetch_cached(AA_HTML_URL, out, force=force)


# --- dispatch ---------------------------------------------------------------

SOURCES = {
    "hf": fetch_huggingface,
    "epoch": fetch_epoch,
    "aa": fetch_artificial_analysis,
}


def main():
    default_cache = Path(user_cache_dir(APP_NAME))
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", choices=list(SOURCES) + ["all"])
    parser.add_argument("-f", "--force", action="store_true", help="re-download even if cached")
    parser.add_argument("--cache-dir", type=Path, default=default_cache,
                        help=f"cache dir (default: {default_cache})")
    parser.add_argument("--hf-max-pages", type=int, default=20)
    parser.add_argument("--hf-page-size", type=int, default=100)
    parser.add_argument("--hf-delay", type=float, default=1.0)
    parser.add_argument("--hf-pipeline-tag", default="text-generation",
                        help="HF pipeline_tag filter (use 'all' or empty to disable)")
    parser.add_argument("--count", action="store_true",
                        help="print total record count from the source (hf only) and exit")
    parser.add_argument("--list-pipeline-tags", action="store_true",
                        help="print HF's canonical list of pipeline_tag values and exit (hf only)")
    parser.add_argument("--with-counts", action="store_true",
                        help="with --list-pipeline-tags: fetch a model count per tag (52 extra HTTP requests, cached per day)")
    parser.add_argument("--list-derivations", nargs="+", metavar="BASE_ID",
                        help="HF base model id(s) — show finetune/quant/adapter/merge counts (hf only)")
    parser.add_argument("--summarize-derivations", action="store_true",
                        help="tally lineage across cached HF raw pages (hf only)")
    parser.add_argument("--top", type=int, metavar="N", nargs="?", const=20,
                        help="list top N models by downloads from cached HF pages (hf only; default 20)")
    parser.add_argument("--since", metavar="SPEC",
                        help="filter --top to records released on/after SPEC (YYYY-MM-DD or 30d/4w/6m/1y)")
    parser.add_argument("--date", help="snapshot date for cache-walking flags (default: latest)")
    args = parser.parse_args()

    if args.count:
        if args.source != "hf":
            sys.exit("--count is only supported for source=hf")
        tag = None if args.hf_pipeline_tag in ("all", "") else args.hf_pipeline_tag
        n = fetch_huggingface_count(pipeline_tag=tag)
        if n is None:
            sys.exit("could not parse numTotalItems from HF /models page")
        print(n)
        return

    if args.list_derivations:
        if args.source != "hf":
            sys.exit("--list-derivations is only supported for source=hf")
        rels = HF_DERIVATION_RELS
        name_w = max(len(b) for b in args.list_derivations)
        header = f"{'base':<{name_w}}  " + "  ".join(f"{r:>10}" for r in rels) + f"  {'total':>10}"
        print(header)
        print("-" * len(header))
        for base in args.list_derivations:
            counts = fetch_huggingface_derivation_counts(base, delay=args.hf_delay)
            cells = [counts.get(r) for r in rels]
            total = sum(c for c in cells if c is not None)
            row = (f"{base:<{name_w}}  "
                   + "  ".join(f"{('-' if c is None else f'{c:,}'):>10}" for c in cells)
                   + f"  {total:>10,}")
            print(row)
        return

    def _resolve_hf_date(date_arg):
        if date_arg:
            return date_arg
        root = args.cache_dir / "raw" / "huggingface"
        if not root.is_dir():
            sys.exit(f"no HF raw cache at {root}")
        dates = sorted(p.name for p in root.iterdir() if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.name))
        if not dates:
            sys.exit(f"no HF snapshots in {root}")
        return dates[-1]

    if args.top is not None:
        if args.source != "hf":
            sys.exit("--top is only supported for source=hf")
        tag = args.hf_pipeline_tag if args.hf_pipeline_tag not in ("all", "") else "text-generation"
        date = _resolve_hf_date(args.date)
        since = parse_since(args.since) if args.since else None
        rows = top_huggingface_by_downloads(args.cache_dir, date,
                                            pipeline_tag=tag, limit=args.top, since=since)
        lin_w = max((len(r["lineage"]) for r in rows), default=8)
        header = f"# HF top {len(rows)} by downloads  pipeline_tag={tag}  date={date}"
        if since:
            header += f"  since={since.isoformat()}"
        print(header)
        print(f"{'rank':>4}  {'downloads':>13}  {'likes':>7}  {'released':<10}  {'lineage':<{lin_w}}  id")
        for i, r in enumerate(rows, 1):
            print(f"{i:>4}  {r['downloads']:>13,}  {r['likes']:>7,}  "
                  f"{r['release_date']:<10}  {r['lineage']:<{lin_w}}  {r['id']}")
        return

    if args.summarize_derivations:
        if args.source != "hf":
            sys.exit("--summarize-derivations is only supported for source=hf")
        tag = args.hf_pipeline_tag if args.hf_pipeline_tag not in ("all", "") else "text-generation"
        date = _resolve_hf_date(args.date)
        s = summarize_huggingface_derivations(args.cache_dir, date, pipeline_tag=tag)
        total = s["total"]
        def pct(n): return f"{n / total * 100:5.1f}%" if total else "  -  "
        print(f"HF pipeline_tag={s['pipeline_tag']}  date={s['date']}  records={total:,}")
        print()
        print("  Lineage classification (per record):")
        print(f"    standalone (no base_model tag)        {s['standalone']:>10,}  ({pct(s['standalone'])})")
        print(f"    derived (>=1 base_model tag)          {s['derived']:>10,}  ({pct(s['derived'])})")
        print()
        print("  Relation tag occurrences (per record; a record may have several):")
        for r in HF_DERIVATION_RELS:
            n = s["rel_counts"][r]
            print(f"    {r:<37} {n:>10,}  ({pct(n)})")
        print(f"    {'plain base_model:<id> only':<37} {s['plain_only']:>10,}  ({pct(s['plain_only'])})")
        print(f"    {'records with >1 relation':<37} {s['multi_rel']:>10,}  ({pct(s['multi_rel'])})")
        if s["combo_counts"]:
            print()
            print("  Top relation combinations:")
            for combo, n in sorted(s["combo_counts"].items(), key=lambda kv: -kv[1])[:10]:
                print(f"    {('+'.join(combo)):<37} {n:>10,}")
        return

    if args.list_pipeline_tags:
        if args.source != "hf":
            sys.exit("--list-pipeline-tags is only supported for source=hf")
        tags = fetch_huggingface_pipeline_tags()
        counts: dict[str, int | None] = {}
        if args.with_counts:
            counts = fetch_huggingface_pipeline_tag_counts(
                args.cache_dir, [t["id"] for t in tags],
                force=args.force, delay=args.hf_delay)
        id_w = max((len(t["id"]) for t in tags), default=0)
        sub_w = max((len(t.get("subType") or "") for t in tags), default=0)
        for t in sorted(tags, key=lambda x: (x.get("subType") or "", x["id"])):
            row = f"{t['id']:<{id_w}}  {(t.get('subType') or ''):<{sub_w}}"
            if args.with_counts:
                n = counts.get(t["id"])
                row += f"  {('-' if n is None else f'{n:>10,}')}"
            row += f"  {t.get('label', '')}"
            print(row)
        print(f"# {len(tags)} pipeline tags", file=sys.stderr)
        return

    sources = list(SOURCES) if args.source == "all" else [args.source]
    for s in sources:
        print(f"[{s}] cache_dir={args.cache_dir}", file=sys.stderr)
        if s == "hf":
            fetch_huggingface(args.cache_dir, force=args.force,
                              max_pages=args.hf_max_pages,
                              page_size=args.hf_page_size,
                              delay=args.hf_delay,
                              pipeline_tag=args.hf_pipeline_tag)
        else:
            SOURCES[s](args.cache_dir, force=args.force)


if __name__ == "__main__":
    main()

#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pandas", "lxml", "requests", "tabulate"]
# ///

import argparse
import datetime
import re
import sys
from io import StringIO

import lxml.html
import pandas as pd
import requests

MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


def normalize_date(raw, default_year):
    if pd.isna(raw):
        return raw
    s = re.sub(r"\[[^\]]*\]", "", str(raw)).strip()
    month = day = year = None
    for tok in re.findall(r"[A-Za-z]+|\d+", s):
        key = tok[:3].title()
        if key in MONTHS:
            month = MONTHS[key]
        elif tok.isdigit():
            n = int(tok)
            if n >= 1900:
                year = n
            elif day is None:
                day = n
    if month is None:
        return s
    if year is None:
        year = default_year
    if day is None:
        return f"{year:04d}-{month:02d}"
    return f"{year:04d}-{month:02d}-{day:02d}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Wikipedia's list of large language models")
    parser.add_argument("-a", "--all", action="store_true", help="list all models, not just free/open ones")
    args = parser.parse_args()

    page = "https://en.wikipedia.org/wiki/List_of_large_language_models"
    text = requests.get(page, headers={"User-agent": "Mozilla/5.0"}).text
    tree = lxml.html.fromstring(text)

    cols = ["Name", "Release date[b]", "Developer", "License[c]"]
    matches = []
    for h3 in tree.xpath("//h3[@id]"):
        year_id = h3.get("id", "")
        if not year_id.isdigit():
            continue
        tables = h3.xpath("./following::table[1]")
        if not tables:
            continue
        df = pd.read_html(StringIO(lxml.html.tostring(tables[0]).decode()))[0]
        if not all(c in df.columns for c in cols):
            continue
        df = df[cols].copy()
        df["Release date[b]"] = df["Release date[b]"].map(
            lambda v, y=int(year_id): normalize_date(v, y))
        matches.append(df)
    if not matches:
        raise ValueError(f"no per-year tables on: {page}")
    df = pd.concat(matches, ignore_index=True)
    print("\n".join(df.columns.tolist()), file=sys.stderr)

    with open(f"{datetime.date.today()}-wikipedia-list-of-llm.md", "w") as f:
        proprietary_labels = [
            "Proprietary",
            "Unreleased",
            "Proprietary[57]",
            "Non-commercial research[d]",
        ]
        out = df
        if not args.all:
            out = out[~out["License[c]"].isin(proprietary_labels)]
        out["Developer"] = out["Developer"].str.slice(0, 12)
        out["License[c]"] = out["License[c]"].str.slice(0, 20)
        out.reset_index(drop=True, inplace=True)
        out.to_markdown(f)
        f.write("\n")

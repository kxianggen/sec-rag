"""Download recent 10-K filings for a list of tickers from SEC EDGAR."""

import json
import time
from pathlib import Path

import requests

HEADERS = {"User-Agent": "Jayson xianggen13@gmail.com"}
TICKERS = ["NVDA", "AMD", "INTC", "MU", "AVGO", "QCOM", "MRVL"]
YEARS = 3
RAW = Path("data/raw")


def get_json(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    time.sleep(0.2)
    return r.json()


def ticker_to_cik():
    data = get_json("https://www.sec.gov/files/company_tickers.json")
    return {e["ticker"]: e["cik_str"] for e in data.values()}


def list_10ks(cik, limit):
    padded = str(cik).zfill(10)
    url = f"https://data.sec.gov/submissions/CIK{padded}.json"
    recent = get_json(url)["filings"]["recent"]

    out = []
    for i, form in enumerate(recent["form"]):
        if form == "10-K":
            out.append({
                "accession": recent["accessionNumber"][i],
                "filed": recent["filingDate"][i],
                "period_end": recent["reportDate"][i],
                "document": recent["primaryDocument"][i],
            })
            if len(out) == limit:
                break
    return out


def main():
    cik_map = ticker_to_cik()
    index = []

    for ticker in TICKERS:
        cik = cik_map[ticker]
        folder = RAW / ticker
        folder.mkdir(parents=True, exist_ok=True)

        for filing in list_10ks(cik, YEARS):
            acc = filing["accession"].replace("-", "")
            url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{filing['document']}"
            dest = folder / f"{filing['period_end']}.html"

            if dest.exists():
                print(f"skip   {ticker} {filing['period_end']}")
            else:
                r = requests.get(url, headers=HEADERS, timeout=60)
                r.raise_for_status()
                time.sleep(0.2)
                dest.write_text(r.text, encoding="utf-8")
                print(f"saved  {ticker} {filing['period_end']}  {dest.stat().st_size:,} bytes")

            filing["ticker"] = ticker
            filing["url"] = url
            filing["path"] = str(dest)
            index.append(filing)

    (RAW / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(f"\n{len(index)} filings indexed")


if __name__ == "__main__":
    main()
"""Read-only Domemae (supply) product list collector. Python 3.9+ stdlib only."""
import argparse
import csv
import datetime as dt
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ENDPOINT = "https://www.domeggook.com/ssl/api/"
FIELDS = ["keyword", "no", "title", "price", "unitQty", "sellerId", "sellerNick",
          "deliveryWho", "deliveryFee", "deliveryAdd", "fromOversea",
          "businessOnly", "adultOnly", "supplyActive", "url", "thumb"]

def parse_items(data):
    root = data.get("domeggook", data) if isinstance(data, dict) else {}
    if not isinstance(root, dict):
        raise ValueError("Unexpected API response format")
    if root.get("error") or root.get("errors"):
        raise ValueError("API reported an error (check access/parameters)")
    listing = root.get("list", {})
    if not isinstance(listing, dict) or "item" not in listing:
        raise ValueError("API response is missing list.item")
    items = listing["item"]
    if items is None:
        items = []
    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list):
        raise ValueError("Unexpected list.item format")
    rows = []
    for item in items:
        if not isinstance(item, dict):
            continue
        deli = item.get("deli") if isinstance(item.get("deli"), dict) else {}
        market = item.get("market") if isinstance(item.get("market"), dict) else {}
        def val(value):
            if value is None:
                return ""
            return str(value).lower() if isinstance(value, bool) else str(value)
        rows.append({
            "no": val(item.get("no")), "title": val(item.get("title")),
            "price": val(item.get("price")), "unitQty": val(item.get("unitQty")),
            "sellerId": val(item.get("id")), "sellerNick": val(item.get("nick")),
            "deliveryWho": val(deli.get("who")), "deliveryFee": val(deli.get("fee")),
            "deliveryAdd": val(deli.get("add")), "fromOversea": val(deli.get("fromOversea")),
            "businessOnly": val(item.get("comOnly")), "adultOnly": val(item.get("adultOnly")),
            "supplyActive": val(market.get("supply")), "url": val(item.get("url")),
            "thumb": val(item.get("thumb"))
        })
    return rows

def get_page(keyword, aid, size, page, timeout=30):
    params = {"ver":"4.1", "mode":"getItemList", "aid":aid, "market":"supply",
              "om":"json", "kw":keyword, "sz":size, "pg":page}
    url = ENDPOINT + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent":"DomemaeProfitAnalyzer/0.2"})
    # Do not log the URL: it contains the API key.
    with urllib.request.urlopen(request, timeout=timeout) as result:
        content = result.read()
    return json.loads(content.decode("utf-8-sig"))

def collect(keyword, aid, limit):
    rows, pages, seen = [], [], set()
    page = 1
    while len(rows) < limit:
        batch = min(100, limit - len(rows))
        response = get_page(keyword, aid, batch, page)
        chunk = parse_items(response)
        pages.append(response)
        for item in chunk:
            if item["no"] in seen:
                continue
            seen.add(item["no"])
            rows.append({"keyword": keyword, **item})
            if len(rows) >= limit:
                break
        print(f"{keyword}: page {page}, received {len(chunk)}, unique {len(rows)}", flush=True)
        if not chunk or len(chunk) < batch:
            break
        page += 1
        if page > 10:
            raise ValueError("Safety cap: exceeded 10 pages")
        time.sleep(0.5)
    return rows, pages

def main():
    p = argparse.ArgumentParser(description="Domemae supply list collector")
    p.add_argument("--keyword", action="append", required=True,
                   help="Repeat for multiple search keywords")
    p.add_argument("--limit", type=int, default=30,
                   help="Maximum products per keyword (1-100)")
    p.add_argument("--output", default="output")
    args = p.parse_args()
    if not 1 <= args.limit <= 100:
        p.error("--limit must be between 1 and 100")
    if len(args.keyword) > 5 or any(not s.strip() or len(s) > 60 for s in args.keyword):
        p.error("Provide 1-5 nonempty keywords, max 60 characters each")
    aid = os.environ.get("DOMEMAE_API_KEY", "").strip()
    if not aid:
        p.error("DOMEMAE_API_KEY secret/environment variable is required")
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    all_rows, all_pages = [], []
    for kw in args.keyword:
        rows, pages = collect(kw.strip(), aid, args.limit)
        all_rows.extend(rows)
        all_pages.append({"keyword": kw, "pages": pages})
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    with (out / f"domemae_items_{stamp}.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(all_rows)
    # Remove the key if it is unexpectedly echoed within the upstream API response.
    safe_pages = json.loads(json.dumps(all_pages, ensure_ascii=False).replace(aid, "[REDACTED]"))
    (out / f"domemae_raw_{stamp}.json").write_text(
        json.dumps(safe_pages, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Collected {len(all_rows)} rows from {len(args.keyword)} keyword(s).")
    print("Reminder: supplier prices are NOT proven resale margins.")

if __name__ == "__main__":
    try:
        main()
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        print("Network/API request failed. Check API permission, key, and connection.", file=sys.stderr)
        sys.exit(1)
    except (ValueError, json.JSONDecodeError):
        print("API response/parameters invalid. Inspect official API documentation.", file=sys.stderr)
        sys.exit(1)

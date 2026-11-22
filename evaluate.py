"""Join manually verified market prices to supplier detail candidates by product number.
This does NOT infer comparable products or consumer demand.
"""
import argparse,csv,datetime,json
from pathlib import Path
from discover import margin

MARKET_FIELDS=["no","marketplace","competitor_url","market_sale_price",
 "market_shipping_collected","platform_fee_pct","other_cost","checked_at","comparison_note"]
NEEDED=("marketplace","competitor_url","checked_at")

def read_csv(path):
    with Path(path).open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

def evaluate(supplier,market):
    listings={r["no"]:r for r in market if r.get("no")}
    results=[]
    for row in supplier:
        r={**row}
        check=listings.get(row.get("no"),{})
        for key in MARKET_FIELDS:r[key]=check.get(key,"")
        calc=margin(r)
        r["contribution_profit"]=calc if calc is not None else ""
        if not all(check.get(k) for k in NEEDED):
            r["profit_status"]="market_evidence_missing"
        elif r.get("shipping_type") not in ("고정배송비","") or r.get("shipping_fee") in ("",None):
            r["profit_status"]="shipping_manual_review"
            r["contribution_profit"]=""
        elif calc is None:
            r["profit_status"]="incomplete_cost_inputs"
        else:
            r["profit_status"]="provisional_margin_requires_exact_match_review"
        results.append(r)
    return results

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--supplier",required=True)
    p.add_argument("--market",required=True)
    p.add_argument("--output",default="output")
    args=p.parse_args()
    supplier=read_csv(args.supplier);market=read_csv(args.market)
    results=evaluate(supplier,market)
    path=Path(args.output);path.mkdir(parents=True,exist_ok=True)
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    keys=list(dict.fromkeys(k for row in results for k in row.keys()))
    target=path/f"market_margin_review_{stamp}.csv"
    with target.open("w",encoding="utf-8-sig",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader();writer.writerows(results)
    summary={"items":len(results),
        "provisional_margins":sum(r["profit_status"]=="provisional_margin_requires_exact_match_review" for r in results)}
    print(json.dumps(summary,ensure_ascii=False))
if __name__=="__main__":main()

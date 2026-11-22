"""Prepare verified-supplier candidates for human Naver/Coupang market review.

No seller account or third-party API key necessary. No scraping.
"""
import argparse,csv,json,re
from pathlib import Path
from urllib.parse import quote
from collections import Counter,defaultdict

RISK_WORDS=("배터리","전기","의료","어린이","유아","식품","화장품","살균",
            "농약","충전기","완구","유리","도자기","전자담배")
FIELDS=["item_no","category","item_name","supplier_price","supplier_shipping",
        "supplier_stock_snapshot","supplier_url","marketplace","market_search_url",
        "market_comparable_url","match_status","same_model_option_evidence",
        "observed_sale_price","buyer_shipping_fee","seller_fee_pct","payment_fee_pct",
        "seller_coupon_cost","ads_per_order","return_reserve","other_variable_cost",
        "legal_rights_status","demand_indicator","demand_source","demand_period",
        "review_complaint_signals","observed_at","analyst_notes","result_status"]
def load(path):
    with open(path,encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))
def build(catalog,details,limit=25):
    base={r["no"]:dict(r) for r in catalog if r.get("no")}
    for row in details:
        no=row.get("no")
        if no in base:
            # Prevent sparse detail rows from overwriting valid titles/URLs.
            base[no].update({k:v for k,v in row.items() if v not in ("",None)})
    groups=defaultdict(list)
    for r in base.values():
        if r.get("details_status")!="loaded":continue
        try:
            cost=int(r["supply_price_1"])
            freight=int(r["shipping_fee"])
        except (KeyError,ValueError,TypeError):continue
        if not 3000<=cost<=40000 or freight<0:continue
        if r.get("fromOversea")=="true" or r.get("adultOnly")=="true":continue
        if r.get("supplyActive")=="false" or r.get("image_license")!="true":continue
        if any(x in r.get("title","") for x in RISK_WORDS):continue
        groups[r.get("category") or "기타"].append(r)
    for v in groups.values():
        v.sort(key=lambda r:(r.get("shipping_type")!="고정배송비",r.get("deliveryAdd")!="false",int(r["supply_price_1"])))
    chosen=[]
    while len(chosen)<limit and any(groups.values()):
        for category in sorted(groups):
            if groups[category] and len(chosen)<limit:
                chosen.append(groups[category].pop(0))
    rows=[]
    for item in chosen:
        search=re.sub(r"\[[^]]+\]","",item["title"]).strip()[:75]
        for platform in ("naver","coupang"):
            link=("https://search.shopping.naver.com/search/all?query=" if platform=="naver"
                else "https://www.coupang.com/np/search?q=")+quote(search)
            row=dict.fromkeys(FIELDS,"")
            row.update(item_no=item["no"],category=item["category"],item_name=item["title"],
                       supplier_price=item["supply_price_1"],
                       supplier_shipping=item["shipping_fee"],
                       supplier_stock_snapshot=item.get("inventory",""),
                       supplier_url=item.get("url",""),marketplace=platform,
                       market_search_url=link,match_status="unverified",
                       legal_rights_status="needs_review",
                       result_status="MARKET_EVIDENCE_REQUIRED")
            rows.append(row)
    return rows,{"supplier_items":len(base),"detailed_items":sum(r.get("details_status")=="loaded" for r in base.values()),
                 "candidate_items":len(chosen),"platform_observation_rows":len(rows),
                 "category_distribution":dict(Counter(r["category"] for r in chosen)),
                 "verified_market_prices":0,"verified_profit":0}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--catalog",required=True)
    p.add_argument("--details",required=True)
    p.add_argument("--limit",type=int,default=25)
    p.add_argument("--output",default="output/research")
    a=p.parse_args()
    if not 1<=a.limit<=100:p.error("limit must be 1-100")
    rows,summary=build(load(a.catalog),load(a.details),a.limit)
    out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    with (out/"market_research_queue.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
    (out/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False))
if __name__=="__main__":main()

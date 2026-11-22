"""Small, bounded Domemae market-readiness experiment (supply-side only).

Four independent search profiles; no promise that ranked items are profitable.
Each detail query is read-only and capped. No product listing or order calls.
"""
import argparse,csv,datetime as dt,json,os,time
from collections import Counter,defaultdict
from pathlib import Path
from collect import parse_items
from discover import api,detail_object,detail_values,number,nested,flag

# These are pilot hypotheses, not 'winning' categories.
KEYWORDS={
  "생활/욕실":["욕실 정리","욕실 수납"],
  "생활/청소":["청소 도구","청소 브러쉬"],
  "생활/세탁":["세탁 용품","세탁망"],
  "수납":["수납함","서랍 정리"]
}
# A strict query first; a relaxed control tests coverage loss.
PROFILES=[
    ("strict",{"sgd":"true","fdl":"true","lwp":"true","dfos":"false"}),
    ("quality_control",{"sgd":"true","fdl":"true","dfos":"false"}),
]
OUTPUT_FIELDS=["no","hypothesis_group","keywords","profiles","title","url","sellerId",
  "list_price","list_shipping","unit_qty","from_overseas","adult_only",
  "supply_active","list_lowest_price_flag","detail_status","supply_price_1",
  "shipping_fee","shipping_type","inventory","supplier_satisfaction",
  "supplier_reviews","supplier_good","popular_code","popular_name",
  "native_min","native_max","native_sole","native_supply_lowest",
  "return_shipping_fee","actual_category","model","manufacturer",
  "image_license","certification_flag","native_comparison_status",
  "flags","evidence_score","review_status","review_reasons",
  "market_price_evidence","demand_evidence","contribution_profit"]

def list_query(aid,kw,params,count):
    q={"ver":"4.1","mode":"getItemList","market":"supply","kw":kw,
       "so":"ha","sz":count,"pg":1,**params}
    return parse_items(api(aid,q))
def safe_int(v):return number(v)
def eligible(r):
    if r.get("supplyActive")!="true" or r.get("adultOnly")=="true" or r.get("fromOversea")=="true":
        return False
    unit=safe_int(r.get("unitQty"))
    price=safe_int(r.get("price"))
    return unit==1 and price is not None and 3000<=price<=40000
def score(r):
    p=safe_int(r.get("price")) or 0
    freight=safe_int(r.get("deliveryFee"))
    s=0
    if r.get("lwp")=="true":s+=3
    if 6000<=p<=25000:s+=2
    if freight is not None and freight<=3500:s+=1
    if r.get("deliveryAdd")=="false":s+=1
    if any(k in r.get("title","") for k in ("어린이","유아","배터리","의료","식품","화장품","살균","농약","충전기","완구")):s-=5
    return s
def pick(rows,limit):
    groups=defaultdict(list)
    for r in rows:groups[r["hypothesis_group"]].append(r)
    for v in groups.values():v.sort(key=lambda r:(-score(r),r["no"]))
    chosen=[]
    while len(chosen)<limit and any(groups.values()):
        for cat in sorted(groups):
            if groups[cat] and len(chosen)<limit:
                chosen.append(groups[cat].pop(0))
    return chosen
def inspect(r):
    result={
      "no":r["no"],"hypothesis_group":r["hypothesis_group"],
      "keywords":"|".join(sorted(r["keywords"])),"profiles":"|".join(sorted(r["profiles"])),
      "title":r.get("title",""),"url":r.get("url",""),"sellerId":r.get("sellerId",""),
      "list_price":r.get("price",""),"list_shipping":r.get("deliveryFee",""),
      "unit_qty":r.get("unitQty",""),"from_overseas":r.get("fromOversea",""),
      "adult_only":r.get("adultOnly",""),"supply_active":r.get("supplyActive",""),
      "list_lowest_price_flag":r.get("lwp",""),"detail_status":"not_checked",
      "market_price_evidence":"","demand_evidence":"","contribution_profit":"",
      "flags":"","evidence_score":score(r),
      "review_status":"REVIEW_REQUIRED","review_reasons":"detail_pending"
    }
    return result
def update_with_detail(row,obj):
    d=detail_values(obj)
    for key,from_key in {
        "supply_price_1":"supply_price_1","shipping_fee":"shipping_fee",
        "shipping_type":"shipping_type","inventory":"inventory",
        "supplier_satisfaction":"seller_satisfaction","supplier_reviews":"seller_reviews",
        "supplier_good":"seller_good","popular_code":"native_popular_code",
        "popular_name":"native_popular_name","native_min":"native_price_min",
        "native_max":"native_price_max","native_sole":"native_price_sole",
        "native_supply_lowest":"native_price_supply_lowest",
        "return_shipping_fee":"return_shipping_fee","actual_category":"actual_category",
        "model":"model","manufacturer":"manufacturer",
        "image_license":"image_license","certification_flag":"certification_flag",
        "native_comparison_status":"native_price_status"
    }.items():
        v=d.get(from_key)
        row[key]="" if v is None else str(v)
    row["detail_status"]="loaded" if d.get("supply_price_1") is not None else "price_review"
    reasons=[]
    if row["detail_status"]!="loaded":reasons.append("supply_cost_missing")
    if row["native_min"]=="":reasons.append("native_comparison_not_available")
    if row["return_shipping_fee"]=="":reasons.append("return_fee_unverified")
    if row["shipping_fee"]=="":reasons.append("shipping_fee_unverified")
    if not str(row["image_license"]).lower() in ("true","1","yes"):reasons.append("image_rights_review")
    if any(w in row["title"] for w in ("어린이","유아","식품","의료","배터리","화장품","살균","완구")):reasons.append("regulation_review")
    row["review_reasons"]="|".join(reasons+["retail_price_not_verified","consumer_demand_not_verified"])
    row["flags"]="|".join(reasons)
    # Strictly no selling approval until current same-option retail price and costs are verified.
    row["review_status"]="REVIEW_REQUIRED"
    return row
def run(aid,out,limit,per_search=80):
    if not 1<=limit<=120:raise ValueError("detail max=120")
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    combined={};errors=[];coverage=[];calls=0
    for group,words in KEYWORDS.items():
        for word in words:
            for label,filters in PROFILES:
                calls+=1
                try:
                    items=list_query(aid,word,filters,per_search)
                    coverage.append({"group":group,"keyword":word,"profile":label,"returned":len(items)})
                    for item in items:
                        no=item.get("no")
                        if not no:continue
                        if no not in combined:
                            combined[no]={**item,"hypothesis_group":group,"keywords":set(),"profiles":set()}
                        combined[no]["keywords"].add(word)
                        combined[no]["profiles"].add(label)
                        # Store a true strict-match signal even if discovered in relaxed profile first.
                        if label=="strict":combined[no]["strict_verified"]=True
                except Exception as e:
                    errors.append({"stage":"list","group":group,"profile":label,"exception":type(e).__name__})
                    coverage.append({"group":group,"keyword":word,"profile":label,"returned":None})
                time.sleep(.15)
    eligible_rows=[r for r in combined.values() if eligible(r)]
    # Only strict matches in primary queue. If too few, report shortage, never silently relax.
    strict_rows=[r for r in eligible_rows if r.get("strict_verified")]
    chosen=pick(strict_rows,limit)
    output=[]
    for r in chosen:
        row=inspect(r)
        calls+=1
        try:
            obj=detail_object(api(aid,{"ver":"4.6","mode":"getItemView","no":r["no"]}))
            if str(nested(obj,"basis","no"))!=r["no"]:raise ValueError("detail product ID mismatch")
            row=update_with_detail(row,obj)
        except Exception as e:
            row["detail_status"]="api_review"
            row["review_reasons"]="detail_error_"+type(e).__name__
            errors.append({"stage":"detail","item_no":r["no"],"exception":type(e).__name__})
        output.append(row)
        time.sleep(.15)
    with (out/"candidates_detail.csv").open("w",encoding="utf-8-sig",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=OUTPUT_FIELDS,extrasaction="ignore")
        writer.writeheader();writer.writerows(output)
    with (out/"coverage.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["group","keyword","profile","returned"]);w.writeheader();w.writerows(coverage)
    summary={"utc":dt.datetime.now(dt.timezone.utc).isoformat(),"api_calls":calls,
             "list_calls":len(coverage),"details_attempted":len(output),
             "details_loaded":sum(r["detail_status"]=="loaded" for r in output),
             "unique_listings":len(combined),"eligible_listing_items":len(eligible_rows),
             "strict_eligible_items":len(strict_rows),
             "native_price_min_available":sum(r["native_min"]!="" for r in output),
             "return_shipping_fee_available":sum(r["return_shipping_fee"]!="" for r in output),
             "seller_satisfaction_available":sum(r["supplier_satisfaction"]!="" for r in output),
             "verified_retail_prices":0,"verified_contribution":0,
             "categories":dict(Counter(r["hypothesis_group"] for r in output)),
             "errors":errors,"warning":"Internal popular sorting is not real end-customer demand. PriceCompare may be outdated/not same option. No margins inferred."}
    (out/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in summary.items() if k not in ("errors",)},ensure_ascii=False),flush=True)
    return summary
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--details",type=int,default=100)
    p.add_argument("--output",default="output/pilot")
    p.add_argument("--per-search",type=int,default=80)
    a=p.parse_args()
    if not 1<=a.details<=120 or not 10<=a.per_search<=100:p.error("detail cap 120, per search 10-100")
    aid=os.environ.get("DOMEMAE_API_KEY","").strip()
    if not aid:p.error("Missing repository API secret")
    run(aid,a.output,a.details,a.per_search)
if __name__=="__main__":main()

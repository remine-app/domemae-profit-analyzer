"""Broad supplier discovery; output is NOT proof of sale price, margin or demand."""
import argparse,csv,datetime,json,os,re,time,urllib.parse,urllib.request
from pathlib import Path
from collect import parse_items, ENDPOINT

# Provisional discovery segments, not verified profitable categories.
SEGMENTS={
 "수납": ["수납함","서랍 정리","옷장 정리"],
 "생활": ["청소 도구","욕실 정리","세탁 용품"],
 "주방": ["주방 정리","주방 소품"],
 "자동차": ["자동차 수납","세차 용품"],
 "반려동물": ["반려동물 용품","강아지 산책"],
 "사무": ["데스크 정리","사무용품"],
 "여행": ["여행 파우치","캠핑 정리"],
 "DIY": ["공구 수납","가구 보호"]
}
REVIEW_WORDS=("배터리","충전기","영유아","어린이","의료","건강기능","식품","화장품","살균","농약","완구")
COLUMNS=("category keyword no title price unitQty sellerId deliveryWho deliveryFee deliveryAdd "
"fromOversea adultOnly supplyActive url flags screen_score details_status supply_price_1 "
"supply_price_rule inventory supply_unit resale_min shipping_type shipping_fee shipping_rule "
"merge_delivery shipping_days image_license seller_reviews tax_status detail_status "
"market_sale_price market_shipping_collected platform_fee_pct other_cost contribution_profit profit_status").split()

def number(v):
    try:
        s=str(v).replace(",","").strip()
        return int(s) if re.fullmatch(r"-?\d+",s) else None
    except (ValueError,TypeError): return None

def unit_price(v):
    n=number(v)
    if n is not None:return n
    if isinstance(v,str):
        for part in v.split("|"):
            pair=part.split("+",1)
            if len(pair)==2 and number(pair[0])==1:return number(pair[1])
    return None

def nested(data,*keys):
    for key in keys:
        if not isinstance(data,dict):return None
        data=data.get(key)
    return data

def flag(row):
    flags=[]
    if row.get("fromOversea")=="true":flags.append("overseas")
    if row.get("adultOnly")=="true":flags.append("adult")
    if row.get("supplyActive")=="false":flags.append("inactive")
    if any(k in row.get("title","") for k in REVIEW_WORDS):flags.append("regulation_review")
    if number(row.get("price")) is None:flags.append("unknown_price")
    if number(row.get("deliveryFee")) is None:flags.append("shipping_review")
    if number(row.get("unitQty")) not in (None,1):flags.append("min_qty_review")
    return flags

def priority(row):
    """Operations-only priority, never predicted demand or profit."""
    p=number(row.get("price")); f=number(row.get("deliveryFee"))
    score=0
    if p is not None:score+=3 if 6000<=p<=35000 else (1 if 3000<=p<=60000 else 0)
    if f is not None and f<=3500:score+=2
    if row.get("deliveryAdd")=="false":score+=1
    if number(row.get("unitQty"))==1:score+=1
    return score-3*len(flag(row))

def api(aid,params):
    params={"aid":aid,"om":"json",**params}
    url=ENDPOINT+"?"+urllib.parse.urlencode(params)
    request=urllib.request.Request(url,headers={"User-Agent":"DomemaeProfitAnalyzer/0.3"})
    # Do not print URL or upstream exception: URL includes secret.
    with urllib.request.urlopen(request,timeout=40) as response:
        return json.loads(response.read().decode("utf-8-sig"))

def detail_object(data):
    root=data.get("domeggook",data) if isinstance(data,dict) else data
    if isinstance(root,dict) and "basis" in root:return root
    if isinstance(root,dict):
        for key in ("item","data"):
            value=root.get(key)
            if isinstance(value,dict) and "basis" in value:return value
    raise ValueError("unexpected detail response")

def detail_values(obj):
    p=nested(obj,"price") or {}
    shipping=nested(obj,"deli","supply") or nested(obj,"deli","dome") or {}
    return {
      "supply_price_1":unit_price(p.get("supply")),
      "supply_price_rule":str(p.get("supply","")),
      "inventory":number(nested(obj,"qty","inventory")),
      "supply_unit":number(nested(obj,"qty","supplyUnit")),
      "resale_min":number(nested(obj,"price","resale","minumum")),
      "shipping_type":str(shipping.get("type","")),
      "shipping_fee":number(shipping.get("fee")),
      "shipping_rule":str(shipping.get("tbl","")),
      "merge_delivery":str(nested(obj,"deli","merge","enable") or ""),
      "shipping_days":number(nested(obj,"deli","periodDeli")),
      "image_license":nested(obj,"desc","license","usable"),
      "seller_reviews":number(nested(obj,"seller","score","cnt")),
      "tax_status":str(nested(obj,"basis","tax") or ""),
      "detail_status":str(nested(obj,"basis","status") or "")
    }

def round_robin(rows,limit):
    by_cat={}
    for row in rows:by_cat.setdefault(row["category"],[]).append(row)
    for group in by_cat.values():group.sort(key=lambda r:(-r["screen_score"],r["no"]))
    result=[]
    while len(result)<limit and any(by_cat.values()):
        for group in by_cat.values():
            if group and len(result)<limit:result.append(group.pop(0))
    return result

def margin(row):
    # Unknown market prices are NOT replaced with guesses.
    vals=[number(row.get(k)) for k in ("market_sale_price","market_shipping_collected",
          "supply_price_1","shipping_fee","other_cost")]
    try:fee=float(row.get("platform_fee_pct"))
    except (TypeError,ValueError):return None
    if any(v is None or v<0 for v in vals) or not 0<=fee<=100:return None
    sale,ship_received,cost,ship_cost,other=vals
    return round((sale+ship_received)*(1-fee/100)-cost-ship_cost-other)

def write_csv(file,rows):
    with file.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=COLUMNS,extrasaction="ignore")
        w.writeheader();w.writerows(rows)

def main():
    p=argparse.ArgumentParser(description="Diversified supplier discovery")
    p.add_argument("--per-search",type=int,default=100)
    p.add_argument("--detail-limit",type=int,default=30)
    p.add_argument("--request-cap",type=int,default=75)
    p.add_argument("--output",default="output")
    args=p.parse_args()
    if not (10<=args.per_search<=200 and 0<=args.detail_limit<=100 and 1<=args.request_cap<=100):
        p.error("limits: per-search 10-200, detail-limit 0-100, request-cap 1-100")
    aid=os.environ.get("DOMEMAE_API_KEY","").strip()
    if not aid:p.error("DOMEMAE_API_KEY missing")
    output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
    unique={};errors=[];requests=0
    # Broad discovery: 18 keywords x two sort orders = 36 listing calls.
    for category,keywords in SEGMENTS.items():
        for kw in keywords:
            for sort in ("ha","da"):
                if requests>=args.request_cap:break
                requests+=1
                try:
                    data=api(aid,{"ver":"4.1","mode":"getItemList","market":"supply",
                                  "kw":kw,"sz":args.per_search,"pg":1,"so":sort})
                    incoming=parse_items(data)
                    for item in incoming:
                        item_no=item.get("no")
                        if not item_no or item_no in unique:continue
                        row={"category":category,"keyword":kw,**item}
                        row["flags"]="|".join(flag(row))
                        row["screen_score"]=priority(row)
                        row["details_status"]="not_checked"
                        row["profit_status"]="market_price_required"
                        unique[item_no]=row
                    print(f"{category}/{kw}/{sort}: {len(incoming)} results; unique {len(unique)}",flush=True)
                except Exception as ex:
                    errors.append({"step":"list","category":category,"keyword":kw,
                                   "type":type(ex).__name__})
                    print("list request failed (no credentials logged)",flush=True)
                time.sleep(.2)
    rows=list(unique.values());candidates=round_robin(rows,args.detail_limit)
    for row in candidates:
        if requests>=args.request_cap:break
        requests+=1
        try:
            detail=detail_object(api(aid,{"ver":"4.6","mode":"getItemView","no":row["no"]}))
            if str(nested(detail,"basis","no"))!=row["no"]:
                raise ValueError("detail product number mismatch")
            row.update(detail_values(detail))
            row["details_status"]="loaded" if row["supply_price_1"] is not None else "price_review"
        except Exception as ex:
            row["details_status"]="manual_review"
            errors.append({"step":"detail","item_no":row["no"],"type":type(ex).__name__})
        time.sleep(.2)
    for row in rows:row["contribution_profit"]=margin(row)
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    write_csv(output/f"catalog_{stamp}.csv",rows)
    write_csv(output/f"detail_candidates_{stamp}.csv",candidates)
    report={"utc":stamp,"api_calls":requests,"unique_products":len(rows),
            "detail_success":sum(r["details_status"]=="loaded" for r in candidates),
            "detail_review":sum(r["details_status"] in ("manual_review","price_review") for r in candidates),
            "profit_calculated":sum(r["contribution_profit"] is not None for r in rows),
            "errors":errors,"note":"No market demand or margins confirmed. Screen score is operational only."}
    (output/f"summary_{stamp}.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="errors"},ensure_ascii=False),flush=True)

if __name__=="__main__":main()

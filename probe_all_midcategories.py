"""All mid-level Domemae category probe from a real getCat inventory census.

Per 2nd-level branch: ONE read-only supply getItemList request with broad, explicit
filters. header.numberOfItems counts observed matching listings, NOT selling
eligibility or distinct verified SKUs. Top-ranked sample is not random.
"""
import argparse,csv,json,os,time,datetime as dt
from collections import Counter,defaultdict
from pathlib import Path
from discover import api,number
from collect import parse_items

COLUMNS=["root","midcategory","code","root_census_count","mid_census_count",
         "filter_match_header","returned_sample","basic_sample_screen","sample_invalid_title",
         "sample_shipping_over_3500","sample_shipping_additional",
         "sample_regulation_review","sample_adult","sample_overseas","request_status","error_type"]
SAMPLE=["category_code","category_root","midcategory","item_no","title","price",
        "delivery_fee","unit_qty","supplier","url","screening_flags"]
RISK=("배터리","충전기","영유아","어린이","의료","건강기능","식품","화장품","살균",
      "농약","완구","전기","발열","마사지","안전","전자담배","가스")
def readcsv(path):
    with open(path,encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def code_root(v):return v.split("_")[0]
def roots_lookup(rows):
    return {code_root(r["category_id"]):r for r in rows if r.get("depth")=="1"}
def eligible_sample(r):
    if r.get("supplyActive")!="true":return False
    if r.get("adultOnly")=="true" or r.get("fromOversea")=="true":return False
    if len(r.get("title","").strip())<3:return False
    price=number(r.get("price"));shipping=number(r.get("deliveryFee"))
    if price is None or not 3000<=price<=40000:return False
    if shipping is None or shipping>3500:return False
    if number(r.get("unitQty"))!=1:return False
    if any(k in r.get("title","") for k in RISK):return False
    return True
def probe(aid,rows,out,max_categories=198,per_category=12):
    parents=roots_lookup(rows)
    mids=[r for r in rows if r.get("depth")=="2" and r.get("category_id","").count("_")==4]
    mids=sorted(mids,key=lambda r:(code_root(r["category_id"]),r["category_id"]))
    if len(mids)>max_categories:raise ValueError("safety limit: too many categories, no requests made")
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    summary_rows=[];samples=[];count_status=Counter()
    for r in mids:
        root=parents.get(code_root(r["category_id"]),{})
        c=r["category_id"]
        stat={"root":root.get("category_name",""),"midcategory":r["category_name"],
              "code":c,"root_census_count":root.get("listed_count",""),
              "mid_census_count":r.get("listed_count","")}
        try:
            response=api(aid,{"ver":"4.1","mode":"getItemList","market":"supply",
                              "ca":c,"mnp":3000,"mxp":40000,"mnq":1,"mxq":1,
                              "dfos":"false","so":"ha","sz":per_category,"pg":1})
            rootdata=response.get("domeggook",response)
            header=rootdata.get("header",{}) if isinstance(rootdata,dict) else {}
            count=number(header.get("numberOfItems"))
            items=parse_items(response) if rootdata.get("list",{}).get("item") is not None else []
            flags=[]
            for item in items:
                p=number(item.get("price"));fee=number(item.get("deliveryFee"))
                fs=[]
                if len(item.get("title","").strip())<3:fs.append("name_unusable")
                if fee is None or fee>3500:fs.append("high_or_unknown_shipping")
                if item.get("deliveryAdd")=="true":fs.append("shipping_increases_with_quantity")
                if any(t in item.get("title","") for t in RISK):fs.append("regulation_review")
                if item.get("adultOnly")=="true":fs.append("adult")
                if item.get("fromOversea")=="true":fs.append("overseas")
                flags.append(fs)
                samples.append({"category_code":c,"category_root":stat["root"],
                    "midcategory":r["category_name"],"item_no":item.get("no",""),
                    "title":item.get("title",""),"price":item.get("price",""),
                    "delivery_fee":item.get("deliveryFee",""),"unit_qty":item.get("unitQty",""),
                    "supplier":item.get("sellerId",""),"url":item.get("url",""),
                    "screening_flags":"|".join(fs)})
            stat.update({"filter_match_header":count if count is not None else "",
              "returned_sample":len(items),"basic_sample_screen":sum(eligible_sample(x) for x in items),
              "sample_invalid_title":sum("name_unusable" in x for x in flags),
              "sample_shipping_over_3500":sum("high_or_unknown_shipping" in x for x in flags),
              "sample_shipping_additional":sum("shipping_increases_with_quantity" in x for x in flags),
              "sample_regulation_review":sum("regulation_review" in x for x in flags),
              "sample_adult":sum("adult" in x for x in flags),
              "sample_overseas":sum("overseas" in x for x in flags),
              "request_status":"ok","error_type":""})
            count_status["ok"]+=1
        except Exception as ex:
            stat.update({"request_status":"failed","error_type":type(ex).__name__})
            count_status["failed"]+=1
        summary_rows.append(stat)
        if len(summary_rows)%20==0:print("processed categories:",len(summary_rows),flush=True)
        time.sleep(.12)
    def write(name,cols,items):
        with (out/name).open("w",encoding="utf-8-sig",newline="") as f:
            w=csv.DictWriter(f,fieldnames=cols,extrasaction="ignore");w.writeheader();w.writerows(items)
    write("whole_category_filter_counts.csv",COLUMNS,summary_rows)
    write("midcategory_ranked_sample.csv",SAMPLE,samples)
    report={"timestamp_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
       "category_tree_midlevels":len(mids),"list_calls_attempted":len(summary_rows),
       "queries_ok":count_status["ok"],"queries_failed":count_status["failed"],
       "sample_rows":len(samples),"sample_basic_operational_pass":sum(eligible_sample(
          {"supplyActive":"true","adultOnly":"false","fromOversea":"false",
           "title":x["title"],"price":x["price"],"deliveryFee":x["delivery_fee"],"unitQty":x["unit_qty"]}) for x in samples),
       "filtered_count_sum_across_independent_midlevel_searches":sum(int(x["filter_match_header"]) for x in summary_rows if str(x.get("filter_match_header","")).isdigit()),
       "root_breakdown":[{"root":root,"midlevels":sum(x["root"]==root for x in summary_rows),
          "query_ok":sum(x["root"]==root and x["request_status"]=="ok" for x in summary_rows),
          "filtered_listing_count_sum":sum(int(x["filter_match_header"]) for x in summary_rows if x["root"]==root and str(x.get("filter_match_header","")).isdigit()),
          "sample_items":sum(x["category_root"]==root for x in samples),
          "sample_basic_pass":sum(x["category_root"]==root and not x["screening_flags"] and number(x["delivery_fee"]) is not None and number(x["delivery_fee"])<=3500 for x in samples)}
          for root in sorted({x["root"] for x in summary_rows})],
       "verified_salable_skus":0,
       "missing_evidence":["exact_option_cost","image_license","product_certification",
                           "seller_return_terms","actual_market_price","marketplace_fee",
                           "expected_return_loss","verified_sales"],
       "interpretation":"Filter header count is an inventory search count, not count of saleable products. Category-level counts can overlap and ranked top samples are NOT random."
    }
    (out/"whole_category_summary.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="root_breakdown"},ensure_ascii=False),flush=True)
    return report
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--census",required=True)
    p.add_argument("--output",default="output/whole_market")
    args=p.parse_args()
    aid=os.environ.get("DOMEMAE_API_KEY","").strip()
    if not aid:p.error("DOMEMAE_API_KEY secret required")
    probe(aid,readcsv(args.census),args.output)
if __name__=="__main__":main()

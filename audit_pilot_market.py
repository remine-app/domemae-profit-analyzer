"""Audit Domemae gross price room against pre-existing NAVER Shopping Insight signals.

Supplier platform's priceCompare.min is NOT verified identical-option retail price.
Shopping Insight is a relative click index, never realized sales.
"""
import argparse,csv,json
from collections import Counter,defaultdict
from pathlib import Path
FIELDS=["no","hypothesis_group","actual_category","title","url","detail_status",
        "supply_price","shipping_fee","shipping_type","native_price_min",
        "indicative_room_before_fees","price_evidence_grade","naver_keyword",
        "naver_trend_points","demand_evidence_grade","return_shipping_fee",
        "supplier_reviews","seller_satisfaction","manual_priority","review_reasons"]
KEYWORD_MAP={"수납":"수납함","생활/욕실":"욕실","생활/청소":"청소","생활/세탁":"세탁"}

def intval(v):
    try:return int(str(v).strip().replace(",",""))
    except (TypeError,ValueError):return None
def audit(rows,naver):
    trends=defaultdict(list)
    for report in naver.get("reports",[]):
        if report.get("status")!="ok":continue
        for item in report.get("data",[]):
            kw=item.get("keyword_group")
            if kw and item.get("relative_click_index") is not None:
                trends[kw].append(item)
    result=[]
    for item in rows:
        group=item.get("hypothesis_group","")
        key=KEYWORD_MAP.get(group,"")
        supply=intval(item.get("supply_price_1"))
        freight=intval(item.get("shipping_fee"))
        external=intval(item.get("native_min"))
        room=external-supply-freight if None not in (external,supply,freight) else None
        reasons=[]
        if room is None:reasons.append("cost_or_supplier_comparison_missing")
        elif room<=0:reasons.append("nonpositive_indicative_room")
        elif room<3000:reasons.append("thin_indicative_room_before_fees")
        if item.get("shipping_type")!="고정배송비":reasons.append("non_fixed_shipping")
        if not item.get("seller_satisfaction"):reasons.append("seller_satisfaction_unavailable")
        if not item.get("model"):reasons.append("exact_model_missing")
        if not item.get("certification_flag"):reasons.append("certification_unverified")
        if not item.get("return_shipping_fee"):reasons.append("return_cost_missing")
        if len(trends.get(key,[]))<8:reasons.append("weak_naver_series")
        reasons+=["current_same_option_retail_price_missing","platform_fees_and_returns_unverified"]
        priority=("PRICE_CHECK_FIRST" if room is not None and room>=3000 and item.get("shipping_type")=="고정배송비"
                  else "LOW_PRICE_ROOM" if room is not None and room<=0
                  else "REVIEW_ONLY")
        out={
            "no":item.get("no",""),"hypothesis_group":group,"actual_category":item.get("actual_category",""),
            "title":item.get("title",""),"url":item.get("url",""),
            "detail_status":item.get("detail_status",""),"supply_price":item.get("supply_price_1",""),
            "shipping_fee":item.get("shipping_fee",""),"shipping_type":item.get("shipping_type",""),
            "native_price_min":item.get("native_min",""),
            "indicative_room_before_fees":"" if room is None else room,
            "price_evidence_grade":"SUPPLIER_PRICE_COMPARE_ONLY",
            "naver_keyword":key,"naver_trend_points":len(trends.get(key,[])),
            "demand_evidence_grade":"CATEGORY_CLICK_PROXY_NOT_SALES",
            "return_shipping_fee":item.get("return_shipping_fee",""),
            "supplier_reviews":item.get("supplier_reviews",""),
            "seller_satisfaction":item.get("supplier_satisfaction",""),
            "manual_priority":priority,"review_reasons":"|".join(reasons)
        }
        result.append(out)
    result.sort(key=lambda r:({"PRICE_CHECK_FIRST":0,"REVIEW_ONLY":1,"LOW_PRICE_ROOM":2}[r["manual_priority"]],
                              -(r["indicative_room_before_fees"] if isinstance(r["indicative_room_before_fees"],int) else -99999),r["no"]))
    return result
def main():
    p=argparse.ArgumentParser();p.add_argument("--candidates",required=True);p.add_argument("--naver",required=True)
    p.add_argument("--output",default="output/review")
    a=p.parse_args()
    with open(a.candidates,encoding="utf-8-sig",newline="") as f:rows=list(csv.DictReader(f))
    with open(a.naver,encoding="utf-8") as f:naver=json.load(f)
    out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    result=audit(rows,naver)
    with (out/"product_due_diligence_queue.csv").open("w",encoding="utf-8-sig",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS);writer.writeheader();writer.writerows(result)
    summary={"rows":len(result),"priority":dict(Counter(r["manual_priority"] for r in result)),
             "naver_series_count":dict(Counter({kw:sum(1 for rep in naver.get("reports",[]) for data in rep.get("data",[]) if data.get("keyword_group")==kw) for kw in KEYWORD_MAP.values()})),
             "verified_retail_price":0,"verified_margin":0,
             "next":"Confirm exact market item model/option, customer price and shipping with URL + timestamp; check channel fees, rights, returns."}
    (out/"due_diligence_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False))
if __name__=="__main__":main()

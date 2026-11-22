"""Conservative platform-by-platform evidence comparison.

Only an exact model+option match with sourced cost assumptions can yield a
provisional contribution margin. Never interpret click indices as sales.
"""
import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

PLATFORMS=("naver","coupang")
MARKET_COLUMNS=[
  "no","platform","competitor_url","observed_at","match_status","match_evidence",
  "sale_price","buyer_shipping_fee","marketplace_fee_pct","payment_fee_pct",
  "supplier_cost","supplier_shipping_cost","coupon_seller_cost","ad_cost",
  "return_reserve","other_variable_cost","demand_signal","demand_source_url",
  "demand_period","demand_type","review_risks","compliance_status","notes"
]
REPORT_COLUMNS=[
  "no","platform","decision","decision_reasons","provisional_contribution",
  "provisional_margin_pct","cost_breakdown_complete","competitor_url",
  "demand_signal","demand_type","demand_source_url","review_risks"
]

def decimal(value):
    from decimal import Decimal, InvalidOperation
    try:
        s=str(value).strip().replace(",","")
        if not s:return None
        n=Decimal(s)
        return n if n.is_finite() and n>=0 else None
    except (InvalidOperation,ValueError,TypeError):
        return None

def check(row):
    from decimal import Decimal
    reasons=[]
    platform=row.get("platform","").strip().lower()
    if platform not in PLATFORMS:
        return {"decision":"INVALID_PLATFORM","decision_reasons":"platform_not_supported",
                "provisional_contribution":"","provisional_margin_pct":"",
                "cost_breakdown_complete":"false"}
    if row.get("compliance_status")!="verified":
        reasons.append("legal_or_rights_unverified")
    if row.get("match_status")!="exact_verified" or not row.get("match_evidence","").strip():
        reasons.append("exact_model_and_option_match_unverified")
    if not row.get("competitor_url","").startswith(("https://","http://")) or not row.get("observed_at",""):
        reasons.append("market_price_evidence_missing")
    fields=["sale_price","buyer_shipping_fee","marketplace_fee_pct","payment_fee_pct",
            "supplier_cost","supplier_shipping_cost","coupon_seller_cost",
            "ad_cost","return_reserve","other_variable_cost"]
    values={k:decimal(row.get(k)) for k in fields}
    missing=[k for k,v in values.items() if v is None]
    if missing:reasons.append("cost_inputs_incomplete:"+",".join(missing))
    if values["marketplace_fee_pct"] is not None and values["marketplace_fee_pct"]>100:
        reasons.append("invalid_marketplace_fee")
    if values["payment_fee_pct"] is not None and values["payment_fee_pct"]>100:
        reasons.append("invalid_payment_fee")
    if not row.get("demand_source_url","").startswith(("https://","http://")) or not row.get("demand_period",""):
        reasons.append("demand_evidence_missing")
    if row.get("demand_type")=="verified_sales" and not row.get("demand_source_url",""):
        reasons.append("sales_claim_without_source")
    if reasons:
        return {"decision":"REVIEW","decision_reasons":"|".join(reasons),
                "provisional_contribution":"","provisional_margin_pct":"",
                "cost_breakdown_complete":str(not missing).lower()}
    gross=values["sale_price"]+values["buyer_shipping_fee"]
    if gross==0:
        return {"decision":"REVIEW","decision_reasons":"zero_gross_revenue",
                "provisional_contribution":"","provisional_margin_pct":"",
                "cost_breakdown_complete":"true"}
    fees=gross*(values["marketplace_fee_pct"]+values["payment_fee_pct"])/Decimal(100)
    costs=sum((values[k] for k in ("supplier_cost","supplier_shipping_cost",
            "coupon_seller_cost","ad_cost","return_reserve","other_variable_cost")),Decimal(0))
    profit=gross-fees-costs
    margin=profit/gross*100
    return {"decision":"PROVISIONAL_COMPARE" if profit>0 else "NEGATIVE_MARGIN",
            "decision_reasons":"requires_vat_and_operational_confirmation" if profit>0 else "negative_contribution",
            "provisional_contribution":str(profit.quantize(Decimal("1"))),
            "provisional_margin_pct":str(margin.quantize(Decimal("0.01"))),
            "cost_breakdown_complete":"true"}

def compare(rows):
    result=[]
    for row in rows:
        result.append({**{k:row.get(k,"") for k in REPORT_COLUMNS},**check(row)})
    by_no=defaultdict(dict)
    for row in result:by_no[row["no"]][row["platform"]]=row
    for group in by_no.values():
        if len(group)<2:continue
        a,b=group.get("naver"),group.get("coupang")
        if a and b and a["decision"]=="PROVISIONAL_COMPARE" and b["decision"]=="PROVISIONAL_COMPARE":
            from decimal import Decimal
            winner="naver" if Decimal(a["provisional_contribution"])>Decimal(b["provisional_contribution"]) else "coupang" if Decimal(b["provisional_contribution"])>Decimal(a["provisional_contribution"]) else "tie"
            a["decision_reasons"]+="|paired_better_platform="+winner
            b["decision_reasons"]+="|paired_better_platform="+winner
    return result

def read(path):
    with open(path,encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def write(path,rows,fields):
    with open(path,"w",encoding="utf-8-sig",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore")
        writer.writeheader();writer.writerows(rows)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--queue",required=True,help="screening market_research_queue.csv")
    parser.add_argument("--observations",help="manually validated observations CSV")
    parser.add_argument("--output",default="output/market")
    args=parser.parse_args()
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    supplier=read(args.queue)
    if args.observations:
        observed=read(args.observations)
        result=compare(observed)
        write(out/"dual_platform_comparison.csv",result,REPORT_COLUMNS)
        summary={"observations":len(result),"provisional":sum(r["decision"]=="PROVISIONAL_COMPARE" for r in result),
                 "negative":sum(r["decision"]=="NEGATIVE_MARGIN" for r in result),
                 "review":sum(r["decision"]=="REVIEW" for r in result)}
    else:
        rows=[]
        for item in supplier:
            for platform in PLATFORMS:
                row={k:"" for k in MARKET_COLUMNS}
                row["no"]=item.get("no","")
                row["platform"]=platform
                row["supplier_cost"]=item.get("supplier_price","")
                row["supplier_shipping_cost"]=item.get("supplier_shipping","")
                rows.append(row)
        write(out/"market_observation_template.csv",rows,MARKET_COLUMNS)
        summary={"supplier_candidates":len(supplier),"observation_rows":len(rows),
                 "message":"Observation template only; no market-price or demand evidence supplied"}
    (out/"market_comparison_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False))

if __name__=="__main__":main()

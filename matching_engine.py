"""Evidence-gated supplier <> marketplace matching and screening.

Never infer sales, exact identity, rights or profit from a similar title.
Works with licensed market observations imported as CSV (manual by default).
Python 3.9+ stdlib.
"""
import argparse,csv,json,re,unicodedata
from collections import Counter,defaultdict
from decimal import Decimal,InvalidOperation
from pathlib import Path

CRITICAL=("인증","KC","식품","의료","의약","어린이","유아","배터리","살균","살충",
          "충전","전기","화장품","건강기능","상표","저작권")
QUALITY=("유리","파손","사이즈","호환","차종","색상","불량","반품")
STOP={"무료배송","정품","국내","당일","특가","추천","상품","초특가","인기"}
OBS_COLS=["marketplace","market_item_id","market_title","market_brand","market_model",
          "market_gtin","market_option","market_quantity","market_url",
          "market_price","market_shipping","observed_at","source_type",
          "demand_source","demand_type","demand_period","demand_value",
          "complaint_signal","notes"]
SUPPLY_COLS=["source","source_id","title","brand","model","gtin","option",
             "quantity","supply_price","shipping_fee","min_order","stock",
             "active","rights_verified","compliance_verified","return_policy_verified",
             "fulfillment_sla_verified","supplier_url","seller_id","observed_at"]
RESULT_COLS=["source","source_id","supplier_title","supplier_url","marketplace",
             "market_title","market_url","identity_grade","identity_evidence",
             "risk_flags","gate","gate_reasons","market_price","market_shipping",
             "supplier_price","supplier_shipping","demand_type","demand_value",
             "demand_source","complaint_signal","gross_spread_before_fees",
             "verified_contribution","decision"]
def get_decimal(v):
    try:
        val=Decimal(str(v).strip().replace(",",""))
        return val if val.is_finite() and val>=0 else None
    except (InvalidOperation,ValueError,TypeError):return None
def yes(v):
    return str(v).strip().lower() in {"1","true","yes","y","verified"}
def norm(value):
    return unicodedata.normalize("NFKC",str(value or "")).casefold().strip()
def tokens(value):
    return {t for t in re.findall(r"[a-z0-9]+|[가-힣]+",norm(value)) if len(t)>1 and t not in STOP}
def identity(s,m):
    """Exact ID/model/option evidence only. Titles are discovery suggestions."""
    sg,mg=norm(s.get("gtin")),norm(m.get("market_gtin"))
    sb,mb=norm(s.get("brand")),norm(m.get("market_brand"))
    sm,mm=norm(s.get("model")),norm(m.get("market_model"))
    so,mo=norm(s.get("option")),norm(m.get("market_option"))
    sq,mq=norm(s.get("quantity")),norm(m.get("market_quantity"))
    conflicts=[]
    for name,a,b in (("gtin",sg,mg),("brand",sb,mb),("model",sm,mm),
                     ("option",so,mo),("quantity",sq,mq)):
        if a and b and a!=b:conflicts.append(name)
    if conflicts:return "CONFLICT","different_"+",".join(conflicts)
    if not so or not mo or not sq or not mq:
        return "REVIEW","option_or_quantity_unverified"
    if sg and mg and sg==mg:return "EXACT_CANDIDATE","same_gtin_option_quantity"
    if sb and mb and sm and mm and sb==mb and sm==mm:
        return "EXACT_CANDIDATE","same_brand_model_option_quantity"
    a,b=tokens(s.get("title")),tokens(m.get("market_title"))
    overlap=len(a&b)/max(1,len(a|b))
    return ("SIMILAR","title_overlap_%.2f"%overlap) if overlap>=0.45 else ("UNMATCHED","insufficient_identity")

def risk(s,m):
    title=str(s.get("title") or "")
    flags=[]
    if any(x.casefold() in title.casefold() for x in CRITICAL):flags.append("regulated_or_rights_review")
    if any(x.casefold() in title.casefold() for x in QUALITY):flags.append("return_or_fit_review")
    if not yes(s.get("active")):flags.append("availability_unverified")
    for field in ("rights_verified","compliance_verified","return_policy_verified","fulfillment_sla_verified"):
        if not yes(s.get(field)):flags.append(field+"_missing")
    if not m.get("complaint_signal"):flags.append("complaint_evidence_missing")
    return flags

def evaluate(s,m):
    grade,evidence=identity(s,m)
    flags=risk(s,m)
    reasons=[]
    if grade!="EXACT_CANDIDATE":reasons.append("identity_not_exact")
    if not m.get("market_url") or not m.get("observed_at"):reasons.append("price_source_missing")
    if m.get("source_type") not in ("manual_public_page","licensed_feed","official_api"):
        reasons.append("source_provenance_missing")
    if not m.get("demand_source") or not m.get("demand_type") or not m.get("demand_period"):
        reasons.append("demand_not_verified")
    if flags:reasons.append("risk_review_pending")
    cost=get_decimal(s.get("supply_price"))
    freight=get_decimal(s.get("shipping_fee"))
    market=get_decimal(m.get("market_price"))
    buyer_ship=get_decimal(m.get("market_shipping"))
    spread=(market+buyer_ship-cost-freight) if None not in (cost,freight,market,buyer_ship) else None
    if spread is None:reasons.append("price_or_shipping_missing")
    # Crucially: cannot calculate margin without market fee + seller costs + return reserve.
    # These are not available in input observations, so contribution remains unavailable.
    gate="READY_FOR_FEE_AND_RETURN_VALIDATION" if not reasons else "REVIEW"
    return {
        "source":s.get("source",""),"source_id":s.get("source_id",""),
        "supplier_title":s.get("title",""),"supplier_url":s.get("supplier_url",""),
        "marketplace":m.get("marketplace",""),"market_title":m.get("market_title",""),
        "market_url":m.get("market_url",""),"identity_grade":grade,"identity_evidence":evidence,
        "risk_flags":"|".join(flags),"gate":gate,"gate_reasons":"|".join(reasons),
        "market_price":m.get("market_price",""),"market_shipping":m.get("market_shipping",""),
        "supplier_price":s.get("supply_price",""),"supplier_shipping":s.get("shipping_fee",""),
        "demand_type":m.get("demand_type",""),"demand_value":m.get("demand_value",""),
        "demand_source":m.get("demand_source",""),"complaint_signal":m.get("complaint_signal",""),
        "gross_spread_before_fees":str(spread) if spread is not None else "",
        "verified_contribution":"","decision":"NOT_APPROVED"}
def csv_read(path):
    with open(path,encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def csv_write(path,rows,fields):
    with open(path,"w",encoding="utf-8-sig",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore")
        writer.writeheader();writer.writerows(rows)
def dome_to_standard(items):
    result=[]
    for r in items:
        if not r.get("no"):continue
        # List price is a provisional number until detail fields verified.
        price=r.get("supply_price_1") or ""
        fee=r.get("shipping_fee") or ""
        result.append({
            "source":"domemae","source_id":r["no"],"title":r.get("title",""),
            "brand":"","model":"","gtin":"","option":"","quantity":"",
            "supply_price":price,"shipping_fee":fee,
            "min_order":r.get("supply_unit") or r.get("unitQty",""),
            "stock":r.get("inventory",""),"active":r.get("supplyActive",""),
            "rights_verified":r.get("image_license",""),
            "compliance_verified":"","return_policy_verified":"","fulfillment_sla_verified":"",
            "supplier_url":r.get("url",""),"seller_id":r.get("sellerId",""),
            "observed_at":""})
    return result
def suggestions(suppliers,markets,limit=500):
    idx=defaultdict(list)
    for m in markets:
        for token in tokens(m.get("market_title")):idx[token].append(m)
    outputs=[];seen=set()
    for s in suppliers:
        candidates=Counter()
        for token in tokens(s.get("title")):
            for m in idx.get(token,[]):candidates[id(m)]+=1
        for marker,_ in candidates.most_common(20):
            # index is a discovery accelerator; it does not confer identity.
            match=next(m for m in markets if id(m)==marker)
            k=(s["source"],s["source_id"],match.get("marketplace"),match.get("market_item_id"),match.get("market_url"))
            if k in seen:continue
            seen.add(k);outputs.append(evaluate(s,match))
            if len(outputs)>=limit:return outputs
    return outputs
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--domemae-catalog",required=True)
    p.add_argument("--market-observations",help="Allowed/sourced market observations CSV")
    p.add_argument("--output",default="output/matching")
    a=p.parse_args()
    out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    suppliers=dome_to_standard(csv_read(a.domemae_catalog))
    csv_write(out/"normalized_suppliers.csv",suppliers,SUPPLY_COLS)
    if a.market_observations:
        markets=csv_read(a.market_observations)
        matches=suggestions(suppliers,markets)
        csv_write(out/"match_review.csv",matches,RESULT_COLS)
    else:
        markets=[];matches=[]
        csv_write(out/"market_observation_template.csv",[],OBS_COLS)
        csv_write(out/"match_review.csv",[],RESULT_COLS)
    summary={"suppliers":len(suppliers),"market_observations":len(markets),"pairs_for_review":len(matches),
             "verified_contribution_count":0,"sales_verified":0,
             "warning":"No source market evidence supplied means no exact match or margin claims."}
    (out/"matching_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False))
if __name__=="__main__":main()

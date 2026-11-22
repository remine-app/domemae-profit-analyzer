"""Flag category-label mismatches in the two-platform research queue.

A keyword match is merely supporting evidence, never validated category identity.
No prices, sales or demand metrics are inferred.
"""
import argparse,csv,json
from collections import Counter
from pathlib import Path
from urllib.parse import quote

HINTS={
 "반려동물":("강아지","고양이","반려","애견","펫","하네스"),
 "자동차":("자동차","차량","차박","세차","트렁크"),
 "사무":("사무","책상","데스크","문서","서류","마우스","키보드"),
 "주방":("주방","조리","냄비","싱크","식기","칼꽂이"),
 "수납":("수납","정리","선반","보관","서랍"),
 "생활":("청소","욕실","세탁","생활","휴지"),
 "여행":("여행","캠핑","캐리어","여권","파우치"),
 "DIY":("도배","공구","DIY","보양","드릴","테이프")
}
def audit(rows):
    out=[]
    for row in rows:
        name=row.get("item_name","")
        category=row.get("category","")
        possible=[c for c,kw in HINTS.items() if any(k.lower() in name.lower() for k in kw)]
        status=("keyword_supported_not_verified" if category in possible else
                "possible_category_mismatch" if possible else "category_not_verifiable_from_title")
        row=dict(row)
        row["category_audit"]=status
        row["suggested_categories"]="|".join(possible)
        row["manual_review_required"]="yes" if status!="keyword_supported_not_verified" else "no"
        row["identity_match_verified"]="no"
        row["market_price_verified"]="no"
        out.append(row)
    return out
def main():
    p=argparse.ArgumentParser();p.add_argument("--input",required=True);p.add_argument("--output",default="output/audit")
    a=p.parse_args()
    with open(a.input,encoding="utf-8-sig",newline="") as f:
        rows=list(csv.DictReader(f))
    output=audit(rows);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    fields=list(dict.fromkeys(k for r in output for k in r))
    with (out/"audited_market_queue.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(output)
    seen={}
    for r in output:seen[r.get("item_no")]=r
    summary={"supplier_products":len(seen),"platform_rows":len(output),
             "category_signal_by_product":dict(Counter(x["category_audit"] for x in seen.values())),
             "verified_market_prices":0,"verified_sales":0,
             "disclaimer":"Category title hints are not validated labels or sales evidence."}
    (out/"audit_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False))
if __name__=="__main__":main()

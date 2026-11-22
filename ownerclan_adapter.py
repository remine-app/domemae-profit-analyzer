"""Ownerclan seller GraphQL read-only adapter. Python stdlib, default offline.

Source: Ownerclan Seller Manual v0.11.0 (2020-10-21), and current public
Ownerclan API docs. Verify live schema and permissions before production.
"""
import argparse,csv,json,os,sys,urllib.request,urllib.error
from pathlib import Path
from matching_engine import SUPPLY_COLS

GRAPHQL="https://api.ownerclan.com/v1/graphql"
AUTH="https://auth.ownerclan.com/auth"
QUERY="""query OwnerclanSearch($count: Int!, $q: String!) {
  allItems(first: $count, search: $q, openmarketSellable: true) {
    pageInfo { hasNextPage endCursor }
    edges { node {
      key name model production price shippingFee shippingType status
      returnable noReturnReason guaranteedShippingPeriod
      openmarketSellable adultOnly pricePolicy fixedPrice
      options { optionAttributes { name value } price quantity }
    }}
  }
}"""
def normalize(doc):
    root=doc.get("data",{}).get("allItems")
    if not isinstance(root,dict):raise ValueError("Missing allItems data")
    if doc.get("errors"):raise ValueError("GraphQL errors returned")
    rows=[]
    for edge in root.get("edges",[]):
        node=edge.get("node") or {}
        if not node.get("key"):continue
        opts=node.get("options") or [{}]
        for ix,opt in enumerate(opts):
            attrs=opt.get("optionAttributes") or []
            opt_name="|".join(str(a.get("name",""))+":"+str(a.get("value","")) for a in attrs)
            price=opt.get("price")
            if price is None:price=node.get("price")
            row={
                "source":"ownerclan","source_id":str(node["key"])+":"+str(ix),
                "title":node.get("name",""),"brand":node.get("production",""),
                "model":node.get("model",""),"gtin":"",
                "option":opt_name,"quantity":"1",
                "supply_price":price if price is not None else "",
                "shipping_fee":node.get("shippingFee",""),
                "min_order":"","stock":opt.get("quantity",""),
                "active":"true" if node.get("status")=="available" and node.get("openmarketSellable") is True else "false",
                "rights_verified":"","compliance_verified":"",
                "return_policy_verified":"","fulfillment_sla_verified":"",
                "supplier_url":"","seller_id":"",
                "observed_at":"",
            }
            rows.append(row)
    return rows
def request_json(url,body,headers=None):
    req=urllib.request.Request(url,method="POST",data=json.dumps(body,ensure_ascii=False).encode("utf-8"),
                               headers={"Content-Type":"application/json",**(headers or {})})
    with urllib.request.urlopen(req,timeout=25) as resp:
        return json.loads(resp.read().decode("utf-8-sig"))
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--keyword",default="수납함")
    p.add_argument("--limit",type=int,default=20)
    p.add_argument("--execute",action="store_true")
    p.add_argument("--output",default="output/ownerclan")
    a=p.parse_args()
    if not 1<=a.limit<=50:p.error("Single call capped at 50 products")
    if not a.keyword or len(a.keyword)>60:p.error("keyword 1-60 characters")
    out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    if not a.execute:
        (out/"dry_run_query.json").write_text(json.dumps({
            "query":QUERY,"variables":{"count":a.limit,"q":a.keyword},
            "note":"Zero external requests. API seller account authorization still required."},
            ensure_ascii=False,indent=2),encoding="utf-8")
        print("DRY RUN: no credentials needed, no external call")
        return
    username=os.environ.get("OWNERCLAN_SELLER_ID")
    password=os.environ.get("OWNERCLAN_SELLER_PASSWORD")
    if not username or not password:p.error("GitHub Actions Secrets OWNERCLAN_SELLER_ID / OWNERCLAN_SELLER_PASSWORD required")
    if os.environ.get("OWNERCLAN_API_APPROVED")!="YES":
        p.error("Set OWNERCLAN_API_APPROVED=YES only after confirming Seller API access/terms")
    try:
        auth=request_json(AUTH,{"service":"ownerclan","userType":"seller","username":username,"password":password})
        token=auth.get("token") or auth.get("access_token")
        if not token:raise ValueError("Authentication response token key requires schema check")
        response=request_json(GRAPHQL,{"query":QUERY,"variables":{"count":a.limit,"q":a.keyword}},
                              {"Authorization":"Bearer "+token})
        rows=normalize(response)
        with (out/"ownerclan_suppliers.csv").open("w",encoding="utf-8-sig",newline="") as f:
            w=csv.DictWriter(f,fieldnames=SUPPLY_COLS,extrasaction="ignore");w.writeheader();w.writerows(rows)
        (out/"summary.json").write_text(json.dumps({"records":len(rows),
            "note":"Seller API raw items; compliance, image rights, returns, delivery costs need verification"},
            ensure_ascii=False,indent=2),encoding="utf-8")
        print("Read-only Ownerclan API query completed:",len(rows),"option rows")
    except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError,ValueError,KeyError) as ex:
        print("Ownerclan API authorization/response failed:",type(ex).__name__,
              "(no token, URL or upstream error body logged)",file=sys.stderr)
        raise SystemExit(1)
if __name__=="__main__":main()

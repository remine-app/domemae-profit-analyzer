"""Read-only total category census; no keywords, no sales/return/margin claims.
Official GET getCat v2.0 market=domeme; getCategoryList v1.0. Two requests.
"""
import json,os,sys,urllib.parse,urllib.request,urllib.error
from pathlib import Path
from datetime import datetime,timezone
ENDPOINT="https://www.domeggook.com/ssl/api/"
def request(aid,parameters):
    query=urllib.parse.urlencode({"aid":aid,"om":"json",**parameters})
    req=urllib.request.Request(ENDPOINT+"?"+query,headers={"User-Agent":"DomemaeProfitAnalyzer/0.9"})
    with urllib.request.urlopen(req,timeout=40) as response:
        raw=response.read(10000000)
    parsed=json.loads(raw.decode("utf-8-sig"))
    # Reject unexpected API errors; do not log request URLs containing API key.
    if not isinstance(parsed,dict) or parsed.get("error") or parsed.get("errors"):
        raise ValueError("API error or unexpected response")
    return parsed
def records(response):
    """API's JSON may use numbered text keys and @number metadata keys."""
    root=response.get("domeggook",response)
    values=root.get("items",{}) if isinstance(root,dict) else {}
    raw=values.get("item",[]) if isinstance(values,dict) else values
    if isinstance(raw,dict) and any(k.startswith("@") for k in raw):
        out=[]
        for key,value in raw.items():
            if not str(key).isdigit():continue
            attr=raw.get("@"+key,{})
            if not isinstance(attr,dict):continue
            out.append({"category_name":str(value),"category_id":str(attr.get("id","")),
                        "category_no":str(attr.get("no","")),
                        "depth":str(attr.get("depth","")),
                        "listed_count":str(attr.get("itemCnt",""))})
        return out
    if isinstance(raw,dict):raw=[raw]
    if not isinstance(raw,list):return []
    return [{"category_name":str(x.get("name","")),
             "category_id":str(x.get("id","")),"category_no":str(x.get("no","")),
             "depth":str(x.get("depth","")),"listed_count":str(x.get("itemCnt",""))}
            for x in raw if isinstance(x,dict)]
def main():
    import csv
    aid=os.environ.get("DOMEMAE_API_KEY","").strip()
    if not aid:
        print("Missing DOMEMAE_API_KEY")
        return 2
    out=Path("output/census");out.mkdir(parents=True,exist_ok=True)
    report={"market":"domeme","calls_attempted":0,"timestamp_utc":datetime.now(timezone.utc).isoformat(),
            "note":"Category counts may be hierarchical and must not be summed across parent and child categories."}
    try:
        report["calls_attempted"]+=1
        category_data=request(aid,{"ver":"2.0","mode":"getCat","market":"domeme"})
        report["getCat_root_keys"]=list(category_data.keys())
        report["getCat_rows"]=len(records(category_data))
        report["getCat_error"]="none"
        import csv
        with (out/"category_counts.csv").open("w",encoding="utf-8-sig",newline="") as f:
            w=csv.DictWriter(f,fieldnames=["category_name","category_id","category_no","depth","listed_count"])
            w.writeheader();w.writerows(records(category_data))
        # Keep statistics, not a truncated or invalid JSON file.
        category_records=records(category_data)
        report["root_categories"]=[r for r in category_records if r["depth"]=="1"]
        report["category_count_total"]=len(category_records)
        report["leaf_count"]=sum(r["category_id"].endswith("_00") is False for r in category_records)
        report["count_warning"]="Counts include parent-child hierarchy; sum only direct root categories, after confirming listing interpretation."
    except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError,ValueError,KeyError) as e:
        report["getCat_error"]=type(e).__name__
        print("getCat query failed:",type(e).__name__,file=sys.stderr)
    try:
        report["calls_attempted"]+=1
        tree=request(aid,{"ver":"1.0","mode":"getCategoryList"})
        report["getCategoryList_root_keys"]=list(tree.keys())
        report["getCategoryList_error"]="none"
        # Tree is fetched only for schema verification; no giant raw artifact.
        report["category_tree_top_keys"]=list(tree.get("domeggook",{}).get("items",{}).keys())[:10]
    except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError,ValueError,KeyError) as e:
        report["getCategoryList_error"]=type(e).__name__
        print("getCategoryList failed:",type(e).__name__,file=sys.stderr)
    (out/"census_summary.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))
    return 0 if report.get("getCat_error")=="none" else 1
if __name__=="__main__":raise SystemExit(main())

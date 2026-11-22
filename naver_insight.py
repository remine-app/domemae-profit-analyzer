"""NAVER API HUB Shopping Insight, manual and quota-conservative.
No automatic recurring calls. A Shopping Insight ratio measures relative clicks, not sales.
"""
import argparse,datetime as dt,json,os,sys,urllib.request,urllib.error
from pathlib import Path

ENDPOINT="https://naverapihub.apigw.ntruss.com/shopping/v1/category/keywords"
def make_payload(category,keywords,days=28,now=None):
    if not category.isdigit() or not 6<=len(category)<=12:
        raise ValueError("NAVER shopping category code is required")
    if not 1<=len(keywords)<=5 or any(not k.strip() or len(k)>60 for k in keywords):
        raise ValueError("Provide 1-5 nonempty keywords (up to 60 characters)")
    today=now or dt.date.today()
    return {"startDate":(today-dt.timedelta(days=days-1)).isoformat(),
            "endDate":today.isoformat(),"timeUnit":"date","category":category,
            "keyword":[{"name":k,"param":[k]} for k in keywords]}
def safe_trends(response):
    if not isinstance(response,dict) or not isinstance(response.get("results"),list):
        raise ValueError("Unexpected API response structure")
    records=[]
    for group in response["results"]:
        for x in group.get("data",[]):
            records.append({"keyword_group":group.get("title",""),
                            "date":x.get("period",""),"relative_click_index":x.get("ratio")})
    return records
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--category",required=True,help="NAVER Shopping category code, not supplier category")
    parser.add_argument("--keyword",action="append",required=True)
    parser.add_argument("--days",type=int,choices=(7,28),default=28)
    parser.add_argument("--output",default="output/naver")
    parser.add_argument("--execute",action="store_true",help="Explicitly authorize ONE API request")
    a=parser.parse_args()
    payload=make_payload(a.category,a.keyword,a.days)
    out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    if not a.execute:
        (out/"dry_run_request.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
        print("DRY RUN ONLY: zero external calls, check category and keyword before execution")
        return
    if os.environ.get("NAVER_FREE_ONLY_ACK")!="YES":
        parser.error("Must acknowledge current 0-KRW plan and quotas in GitHub workflow")
    key_id=os.environ.get("NAVER_API_HUB_CLIENT_ID","")
    key=os.environ.get("NAVER_API_HUB_CLIENT_SECRET","")
    if not (key_id and key):parser.error("Missing NAVER API HUB credentials")
    body=json.dumps(payload,ensure_ascii=False).encode("utf-8")
    request=urllib.request.Request(ENDPOINT,data=body,method="POST",headers={
        "X-NCP-APIGW-API-KEY-ID":key_id,"X-NCP-APIGW-API-KEY":key,
        "Content-Type":"application/json","User-Agent":"DomemaeProfitAnalyzer/0.5"})
    try:
        with urllib.request.urlopen(request,timeout=20) as response:
            raw=json.loads(response.read().decode("utf-8-sig"))
    except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError):
        print("NAVER API call failed; check Application permissions, parameters, and limit without exposing credentials",file=sys.stderr)
        sys.exit(1)
    records=safe_trends(raw)
    (out/"shopping_insight.json").write_text(json.dumps({
        "source":"NAVER API HUB Shopping Insight","unit":"relative_search_click_index_NOT_sales",
        "request":payload,"data":records},ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"One API request completed. {len(records)} daily trend observations. NOT sales figures.")
if __name__=="__main__":main()

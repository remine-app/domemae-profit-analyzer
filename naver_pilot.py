"""Bounded one-time Naver Shopping Insight 2-category pilot.

2 requests total, no API credentials or upstream raw bodies written.
Indices describe relative clicks, NOT transaction volumes.
"""
import datetime as dt
import json
import os
from pathlib import Path
import sys
import urllib.request
import urllib.error
from naver_insight import ENDPOINT,make_payload,safe_trends

GROUPS=[
    ("가구인테리어","50000004",["수납","수납함","수납바구니","서랍정리함"]),
    ("생활건강","50000008",["청소","욕실","정리","세탁"]),
]
OUT=Path("output/naver_pilot")
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    key_id=os.environ.get("NAVER_API_HUB_CLIENT_ID","").strip()
    key=os.environ.get("NAVER_API_HUB_CLIENT_SECRET","").strip()
    if not key_id or not key:
        print("NAVER API HUB Secrets missing")
        return 2
    end=dt.datetime.now(dt.timezone.utc).date()-dt.timedelta(days=1)
    reports=[]
    all_success=True
    for name,category,keywords in GROUPS:
        # Independent per-category normalization: DO NOT compare absolute scores between categories.
        body=make_payload(category,keywords,28,now=end)
        body["startDate"]=(end-dt.timedelta(days=83)).isoformat()
        body["timeUnit"]="week"
        req=urllib.request.Request(ENDPOINT,method="POST",
            data=json.dumps(body,ensure_ascii=False).encode("utf-8"),
            headers={"X-NCP-APIGW-API-KEY-ID":key_id,
                     "X-NCP-APIGW-API-KEY":key,
                     "Content-Type":"application/json",
                     "User-Agent":"DomemaeProfitAnalyzer/0.6"})
        report={"group":name,"category":category,"keywords":keywords,
                "period_start":body["startDate"],"period_end":body["endDate"],
                "unit":"weekly_relative_click_index_NOT_sales"}
        try:
            with urllib.request.urlopen(req,timeout=25) as response:
                result=json.loads(response.read().decode("utf-8-sig"))
            samples=safe_trends(result)
            report["status"]="ok"
            report["samples"]=len(samples)
            report["data"]=samples
            report["trend_quality"]=("insufficient" if len(samples)<8 else "needs_source_review")
            print(name,"API success",len(samples),"weekly observations")
        except urllib.error.HTTPError as exc:
            report.update(status="http_error",http_status=exc.code)
            all_success=False
            print(name,"HTTP",exc.code,file=sys.stderr)
        except (urllib.error.URLError,TimeoutError,ValueError,json.JSONDecodeError) as exc:
            report.update(status="error",error_type=type(exc).__name__)
            all_success=False
            print(name,"response error",type(exc).__name__,file=sys.stderr)
        reports.append(report)
    result={"requests_attempted":len(GROUPS),"pricing":"check_current_free_allowance_in_NCP_console",
            "interpretation":"relative shopping click indicators, not sales/market share",
            "reports":reports}
    (OUT/"pilot_results.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    return 0 if all_success else 1
if __name__=="__main__":raise SystemExit(main())

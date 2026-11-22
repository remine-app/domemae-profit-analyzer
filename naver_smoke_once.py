"""One-time API HUB connection check: exactly one request, never logs secrets.

This is NOT a sales volume or product-level margin validation.
"""
import datetime as dt
import json
import os
from pathlib import Path
import sys
import urllib.request
import urllib.error

from naver_insight import ENDPOINT, make_payload, safe_trends

CATEGORY="50000004"  # NAVER Shopping furniture/interior, test category only
KEYWORDS=["수납함","수납바구니","서랍정리함"]
OUT=Path("output/naver_smoke")
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    key_id=os.environ.get("NAVER_API_HUB_CLIENT_ID","").strip()
    secret=os.environ.get("NAVER_API_HUB_CLIENT_SECRET","").strip()
    if not key_id or not secret:
        print("Missing GitHub Actions secrets: NAVER_API_HUB_CLIENT_ID / NAVER_API_HUB_CLIENT_SECRET")
        return 2
    # Last fully completed UTC calendar day, not an unclosed current day.
    end=dt.datetime.now(dt.timezone.utc).date()-dt.timedelta(days=1)
    payload=make_payload(CATEGORY,KEYWORDS,28,now=end)
    request=urllib.request.Request(ENDPOINT,method="POST",
        data=json.dumps(payload,ensure_ascii=False).encode("utf-8"),
        headers={"X-NCP-APIGW-API-KEY-ID":key_id,
                 "X-NCP-APIGW-API-KEY":secret,
                 "Content-Type":"application/json",
                 "User-Agent":"DomemaeProfitAnalyzer/0.5"})
    status={"request_count":1,"source":"NAVER API HUB Shopping Insight",
            "category_id":CATEGORY,"keywords":KEYWORDS,
            "date_start":payload["startDate"],"date_end":payload["endDate"],
            "meaning":"relative_click_index_not_sales"}
    try:
        with urllib.request.urlopen(request,timeout=25) as response:
            data=json.loads(response.read().decode("utf-8-sig"))
        points=safe_trends(data)
        status.update({"state":"success","observations":len(points),"data":points})
        print("NAVER API HUB connection SUCCESS, trend observations:",len(points))
        return_code=0
    except urllib.error.HTTPError as ex:
        status.update({"state":"http_error","http_status":ex.code})
        print("NAVER API HUB error HTTP",ex.code,"(check app API permissions / secret / category)",file=sys.stderr)
        return_code=1
    except (urllib.error.URLError,TimeoutError,ValueError,json.JSONDecodeError) as ex:
        status.update({"state":"connection_or_response_error","error_type":type(ex).__name__})
        print("NAVER connection/response check failed",type(ex).__name__,file=sys.stderr)
        return_code=1
    finally:
        # No upstream error bodies, Authorization values, or headers written.
        (OUT/"connection_status.json").write_text(
            json.dumps(status,ensure_ascii=False,indent=2),encoding="utf-8")
    return return_code
if __name__=="__main__":
    raise SystemExit(main())

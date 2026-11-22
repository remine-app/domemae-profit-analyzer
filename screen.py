"""Offline, conservative supply-screening; not a sales/demand prediction."""
import argparse,csv,json,re
from collections import Counter
from pathlib import Path

RISK=('의료','식품','건강기능','완구','유아','어린이','전기','배터리','충전','화장품','살균','소독','농약')
FRAGILE=('유리','도자기','거울','액자','크리스탈')
FIT=('사이즈','호환','케이스','커버','필름','신발','의류')
FIELDS=('no category title supplier_price supplier_shipping inventory status flags next_action demand_evidence '
'market_match market_price market_shipping platform_fee_pct refund_reserve other_cost contribution_profit '
'supplier_url competitor_url checked_at notes').split()

def load(path):
    with open(path,encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def save(path,rows):
    with open(path,'w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS,extrasaction='ignore');w.writeheader();w.writerows(rows)
def num(v):
    if v is None or isinstance(v,bool):return None
    value=str(v).strip().replace(',','')
    return float(value) if re.fullmatch(r'\d+(?:\.\d+)?',value) else None
def screening(row):
    title=row.get('title') or ''
    flags=[]
    if any(x in title for x in RISK):flags.append('certification_review')
    if any(x in title for x in FRAGILE):flags.append('fragile_review')
    if any(x in title for x in FIT):flags.append('compatibility_review')
    if row.get('fromOversea','').lower()=='true':flags.append('overseas')
    if row.get('adultOnly','').lower()=='true':flags.append('age_restricted')
    if row.get('supplyActive','').lower()=='false':flags.append('inactive')
    supply=num(row.get('supply_price_1')) or num(row.get('price'))
    shipping=num(row.get('shipping_fee'))
    if shipping is None:shipping=num(row.get('deliveryFee'))
    if supply is None:flags.append('unknown_cost')
    if shipping is None:flags.append('unknown_shipping')
    if row.get('details_status')!='loaded':flags.append('detail_missing')
    if str(row.get('image_license','')).lower() not in ('true','yes','1','y'):flags.append('image_rights_unverified')
    stage=('HOLD' if any(x in flags for x in ('age_restricted','inactive')) else
           'REVIEW' if any(x in flags for x in ('certification_review','unknown_cost','unknown_shipping','detail_missing','image_rights_unverified')) else
           'MARKET_CHECK')
    return dict(no=row.get('no',''),category=row.get('category',''),title=title,
                supplier_price='' if supply is None else int(supply),
                supplier_shipping='' if shipping is None else int(shipping),
                inventory=row.get('inventory',''),status=stage,flags='|'.join(flags),
                next_action='공급·권리 확인' if stage!='MARKET_CHECK' else '시장가격·수요 확인',
                supplier_url=row.get('url',''))
def provisional_margin(row):
    if row.get('market_match')!='exact_verified' or not row.get('competitor_url') or not row.get('checked_at'):return None
    keys=('market_price','market_shipping','supplier_price','supplier_shipping','platform_fee_pct','refund_reserve','other_cost')
    nums=[num(row.get(k)) for k in keys]
    if any(x is None for x in nums):return None
    sale,ship_revenue,cost,ship_cost,fee,refund,other=nums
    if fee>100:return None
    return round((sale+ship_revenue)*(1-fee/100)-cost-ship_cost-refund-other)
def process(catalog,details,out,limit):
    merged={r['no']:r for r in catalog if r.get('no')}
    for r in details:
        if r.get('no') in merged:merged[r['no']]={**merged[r['no']],**r}
    rows=[screening(r) for r in merged.values()]
    groups={}
    for r in rows:groups.setdefault(r['category'],[]).append(r)
    for group in groups.values():group.sort(key=lambda r:(r['status']!='MARKET_CHECK',r['status']!='REVIEW',r['no']))
    chosen=[]
    while len(chosen)<limit and any(groups.values()):
        for category in sorted(groups):
            if groups[category] and len(chosen)<limit:chosen.append(groups[category].pop(0))
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    save(out/'supplier_screening.csv',rows)
    save(out/'market_research_queue.csv',chosen)
    result={'supplier_items':len(rows),'details_loaded':sum(r.get('details_status')=='loaded' for r in merged.values()),
            'stages':dict(Counter(r['status'] for r in rows)),'market_price_verified':0,'profit_verified':0,
            'note':'Not a selling approval; market demand and actual contribution profit are not verified.'}
    (out/'screening_summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result
def main():
    p=argparse.ArgumentParser();p.add_argument('--catalog',required=True);p.add_argument('--details',required=True)
    p.add_argument('--output',default='output');p.add_argument('--shortlist',type=int,default=80)
    a=p.parse_args()
    if not 1<=a.shortlist<=500:p.error('shortlist must be between 1 and 500')
    print(json.dumps(process(load(a.catalog),load(a.details),a.output,a.shortlist),ensure_ascii=False))
if __name__=='__main__':main()

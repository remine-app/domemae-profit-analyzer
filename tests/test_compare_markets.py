import unittest
from compare_markets import check,compare
class MarketTests(unittest.TestCase):
 def base(self):
  return dict(no='1',platform='naver',match_status='exact_verified',
    match_evidence='same manufacturer model and option checked',
    competitor_url='https://example.com/p',observed_at='2026-11-22',
    compliance_status='verified',sale_price='20000',buyer_shipping_fee='0',
    marketplace_fee_pct='3',payment_fee_pct='2',supplier_cost='10000',
    supplier_shipping_cost='3000',coupon_seller_cost='0',ad_cost='500',
    return_reserve='1000',other_variable_cost='500',demand_source_url='https://example.com/analytics',
    demand_period='28d',demand_type='click_trend')
 def test_complete_provisional(self):
  r=check(self.base())
  self.assertEqual(r['decision'],'PROVISIONAL_COMPARE')
  self.assertEqual(r['provisional_contribution'],'4000')
 def test_missing_cost_never_estimated(self):
  r=self.base();r.pop('return_reserve')
  self.assertEqual(check(r)['decision'],'REVIEW')
 def test_unverified_identity_blocks_margin(self):
  r=self.base();r['match_status']='similar'
  self.assertEqual(check(r)['provisional_contribution'],'')
 def test_negative_margin(self):
  r=self.base();r['supplier_cost']='19999'
  self.assertEqual(check(r)['decision'],'NEGATIVE_MARGIN')
 def test_both_platforms(self):
  a=self.base();b={**a,'platform':'coupang','marketplace_fee_pct':'10'}
  result=compare([a,b])
  self.assertIn('paired_better_platform=naver',result[0]['decision_reasons'])

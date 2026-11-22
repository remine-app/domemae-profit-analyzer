import unittest
from audit_pilot_market import audit
class PilotAuditTests(unittest.TestCase):
 def test_price_comparison_is_not_verified_margin(self):
  item={'no':'1','hypothesis_group':'생활/청소','title':'정리함','supply_price_1':'10000',
   'shipping_fee':'3000','shipping_type':'고정배송비','native_min':'18000',
   'detail_status':'loaded'}
  naver={'reports':[{'status':'ok','data':[{'keyword_group':'청소','relative_click_index':50}]}]}
  r=audit([item],naver)[0]
  self.assertEqual(r['manual_priority'],'PRICE_CHECK_FIRST')
  self.assertEqual(r['indicative_room_before_fees'],5000)
  self.assertEqual(r['price_evidence_grade'],'SUPPLIER_PRICE_COMPARE_ONLY')
  self.assertIn('current_same_option_retail_price_missing',r['review_reasons'])
 def test_missing_shipping_cannot_be_accepted(self):
  item={'no':'2','hypothesis_group':'수납','native_min':'17000','supply_price_1':'11000','shipping_type':'수량별비례'}
  r=audit([item],{'reports':[]})[0]
  self.assertEqual(r['indicative_room_before_fees'],'')
  self.assertNotEqual(r['manual_priority'],'PRICE_CHECK_FIRST')

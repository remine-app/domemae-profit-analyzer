import unittest
from screen import screening, provisional_margin
class ScreeningTests(unittest.TestCase):
    def test_no_detail_is_unverified(self):
        r=screening({'no':'1','title':'간단 수납함','price':'5000','deliveryFee':'3000'})
        self.assertEqual(r['status'],'REVIEW')
    def test_risky_product_flags(self):
        r=screening({'no':'2','title':'어린이 완구','price':'10000','deliveryFee':'3000','details_status':'loaded','image_license':'true'})
        self.assertIn('certification_review',r['flags'])
    def test_no_fake_profit(self):
        self.assertIsNone(provisional_margin({'market_price':'20000','supplier_price':'10000'}))
    def test_margin_math(self):
        r={'market_match':'exact_verified','competitor_url':'https://example.com','checked_at':'2026-11-22',
           'market_price':'20000','market_shipping':'0','supplier_price':'10000','supplier_shipping':'3000',
           'platform_fee_pct':'10','refund_reserve':'1000','other_cost':'500'}
        self.assertEqual(provisional_margin(r),3500)

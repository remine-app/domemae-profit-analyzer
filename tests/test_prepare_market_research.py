import unittest
from prepare_market_research import build
class PrepareMarketResearchTests(unittest.TestCase):
    def test_balanced_and_sourced_no_market_assumptions(self):
        a={'no':'1','category':'생활','title':'수납 바구니','price':'10000','shipping_fee':'3000',
           'details_status':'loaded','image_license':'true','supply_price_1':'10000','supplyActive':'true'}
        b={'no':'2','category':'사무','title':'케이블 보관함','price':'9000','shipping_fee':'3000',
           'details_status':'loaded','image_license':'true','supply_price_1':'9000','supplyActive':'true'}
        rows,s=build([a,b],[],2)
        self.assertEqual(len(rows),4)
        self.assertEqual({r['marketplace'] for r in rows},{'naver','coupang'})
        self.assertTrue(all(r['match_status']=='unverified' for r in rows))
        self.assertTrue(all(r['observed_sale_price']=='' for r in rows))
    def test_empty_detail_does_not_delete_title(self):
        a={'no':'1','category':'생활','title':'수납 바구니','supply_price_1':'10000',
           'shipping_fee':'3000','image_license':'true','details_status':'not_checked'}
        d={'no':'1','title':'','details_status':'loaded'}
        rows,_=build([a],[d],1)
        self.assertIn('수납 바구니',rows[0]['item_name'])
    def test_safety_skip(self):
        a={'no':'1','category':'생활','title':'어린이 배터리 완구','supply_price_1':'10000',
           'shipping_fee':'3000','image_license':'true','details_status':'loaded'}
        rows,_=build([a],[],2)
        self.assertEqual(rows,[])

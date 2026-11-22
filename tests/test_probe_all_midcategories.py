import unittest
from probe_all_midcategories import eligible_sample,roots_lookup
class WholeMarketTests(unittest.TestCase):
 def test_title_missing_rejects(self):
  r={'supplyActive':'true','adultOnly':'false','fromOversea':'false','title':'',
     'price':'12000','unitQty':'1','deliveryFee':'3000'}
  self.assertFalse(eligible_sample(r))
 def test_basic_filter_not_proof(self):
  r={'supplyActive':'true','adultOnly':'false','fromOversea':'false','title':'수납 바구니',
     'price':'12000','unitQty':'1','deliveryFee':'3000'}
  self.assertTrue(eligible_sample(r))
 def test_root_map(self):
  a=roots_lookup([{'category_id':'12_00_00_00_00','depth':'1','category_name':'생활용품'},
                  {'category_id':'12_01_00_00_00','depth':'2','category_name':'기타'}])
  self.assertEqual(a['12']['category_name'],'생활용품')

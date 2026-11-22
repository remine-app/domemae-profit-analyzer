import unittest
from discover import detail_values
class NativeCompetitivenessTests(unittest.TestCase):
 def test_fields(self):
  obj={"price":{"supply":"1+6500|10+6000"},
       "seller":{"score":{"avg":"98","cnt":"12"},"good":True},
       "popular":{"code":2,"name":"전체"},
       "priceCompare":{"min":12000,"max":18500,"sole":False,"supply":True},
       "return":{"deliAmt":3500,"deliAmtDouble":True},
       "category":{"current":{"name":"생활용품"}},
       "detail":{"model":"M-001","manufacturer":"제조사","safetyCert":{"cert":"N"}}}
  r=detail_values(obj)
  self.assertEqual(r["supply_price_1"],6500)
  self.assertEqual(r["seller_satisfaction"],98)
  self.assertEqual(r["native_price_min"],12000)
  self.assertEqual(r["native_price_max"],18500)
  self.assertEqual(r["return_shipping_fee"],3500)
  self.assertEqual(r["actual_category"],"생활용품")
  self.assertEqual(r["model"],"M-001")
  self.assertEqual(r["native_price_status"],"supplier_platform_price_comparison_not_verified_retail")
 def test_missing_indicators_not_zero(self):
  r=detail_values({"price":{"supply":9000}})
  self.assertIsNone(r["native_price_min"])
  self.assertIsNone(r["return_shipping_fee"])
  self.assertEqual(r["native_price_status"],"no_supplier_price_comparison")

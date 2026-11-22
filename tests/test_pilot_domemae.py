import unittest
from pilot_domemae import eligible,score,pick,inspect,update_with_detail
class PilotTests(unittest.TestCase):
 def row(self,no="1",group="생활/욕실"):
  return {"no":no,"hypothesis_group":group,"keywords":{"욕실 정리"},"profiles":{"strict"},"title":"욕실 정리함",
          "price":"12000","deliveryFee":"3000","unitQty":"1","adultOnly":"false",
          "fromOversea":"false","supplyActive":"true","lwp":"true"}
 def test_eligible(self):
  self.assertTrue(eligible(self.row()))
  row=self.row();row["unitQty"]="10"
  self.assertFalse(eligible(row))
 def test_only_details_not_profit(self):
  row=inspect(self.row())
  self.assertEqual(row["contribution_profit"],"")
  self.assertEqual(row["review_status"],"REVIEW_REQUIRED")
 def test_real_native_fields(self):
  row=inspect(self.row())
  detail={"basis":{"no":"1"},"price":{"supply":"1+9000"},"deli":{"supply":{"fee":"3000"}},
          "priceCompare":{"min":17000,"max":19000},"return":{"deliAmt":5000},
          "seller":{"score":{"avg":"95","cnt":"19"}}}
  res=update_with_detail(row,detail)
  self.assertEqual(res["detail_status"],"loaded")
  self.assertEqual(res["native_min"],"17000")
  self.assertEqual(res["return_shipping_fee"],"5000")
  self.assertEqual(res["contribution_profit"],"")
 def test_round_robin(self):
  rows=[self.row("1","수납"),self.row("2","생활/욕실"),self.row("3","수납")]
  self.assertEqual(len(pick(rows,2)),2)

import unittest
from ownerclan_adapter import normalize
class OwnerclanTests(unittest.TestCase):
 def test_final_option_price_not_increment(self):
  payload={"data":{"allItems":{"edges":[{"node":{
   "key":"W1","name":"수납함","model":"A1","production":"A",
   "price":10000,"shippingFee":3000,"status":"available","openmarketSellable":True,
   "options":[{"optionAttributes":[{"name":"색","value":"검정"}],"price":11500,"quantity":4},
              {"optionAttributes":[{"name":"색","value":"흰색"}],"price":10000,"quantity":2}]
  }}]}}}
  rows=normalize(payload)
  self.assertEqual(len(rows),2)
  self.assertEqual(rows[0]['supply_price'],11500)
  self.assertEqual(rows[1]['stock'],2)
  self.assertEqual(rows[0]['rights_verified'],'')
  self.assertEqual(rows[0]['active'],'true')
 def test_restricted_market_not_approved(self):
  doc={"data":{"allItems":{"edges":[{"node":{"key":"W2","openmarketSellable":False,"status":"available","options":[]}}]}}}
  self.assertEqual(normalize(doc)[0]['active'],'false')
 def test_bad_response(self):
  with self.assertRaises(ValueError):normalize({"errors":[{"message":"Denied"}]})

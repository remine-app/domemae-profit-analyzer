import unittest
import discover

class DiscoveryTests(unittest.TestCase):
    def test_tier_price(self):
        self.assertEqual(discover.unit_price("1+3800|20+3500"),3800)
        self.assertIsNone(discover.unit_price("10+3500"))
        self.assertEqual(discover.unit_price("4,200"),4200)
    def test_detail_fields(self):
        data={"basis":{"status":"판매중","no":"111"},"price":{"supply":"1+10000|20+9000"},
              "qty":{"inventory":"3","supplyUnit":"1"},
              "deli":{"supply":{"type":"고정배송비","fee":"3000"},"merge":{"enable":"y"}},
              "desc":{"license":{"usable":True}}}
        row=discover.detail_values(data)
        self.assertEqual(row["supply_price_1"],10000)
        self.assertEqual(row["shipping_fee"],3000)
        self.assertTrue(row["image_license"])
    def test_missing_market_price(self):
        self.assertIsNone(discover.margin({"supply_price_1":10000,"shipping_fee":3000}))
    def test_profit(self):
        row={"market_sale_price":20000,"market_shipping_collected":0,"supply_price_1":10000,
             "shipping_fee":3000,"platform_fee_pct":10,"other_cost":1000}
        self.assertEqual(discover.margin(row),4000)
    def test_category_diversity(self):
        rows=[{"category":"A","screen_score":5,"no":str(i)} for i in range(5)]+[
            {"category":"B","screen_score":1,"no":"x"}]
        self.assertEqual({r["category"] for r in discover.round_robin(rows,2)},{"A","B"})
    def test_unrecognized_detail(self):
        with self.assertRaises(ValueError):discover.detail_object({"unknown":"response"})
if __name__=="__main__":unittest.main()

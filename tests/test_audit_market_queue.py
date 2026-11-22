import unittest
from audit_market_queue import audit
class MarketCategoryAuditTests(unittest.TestCase):
 def test_wrong_pet_label_flagged(self):
  rows=audit([{"item_no":"1","item_name":"일반 핸드폰 미니백 RD-12341","category":"반려동물"}])
  self.assertNotEqual(rows[0]["category_audit"],"keyword_supported_not_verified")
  self.assertEqual(rows[0]["market_price_verified"],"no")
 def test_keyword_does_not_mean_verified(self):
  rows=audit([{"item_no":"2","item_name":"강아지 산책 가방","category":"반려동물"}])
  self.assertEqual(rows[0]["category_audit"],"keyword_supported_not_verified")
  self.assertEqual(rows[0]["identity_match_verified"],"no")

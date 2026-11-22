import unittest
from unittest.mock import patch
import collect

class CollectorTests(unittest.TestCase):
    def test_parse_single_item(self):
        payload = {"domeggook": {"list": {"item": {"no": "42", "title": "Cable tidy",
            "price": "2000", "deli": {"fee": "3000"}, "market": {"supply": True}}}}}
        rows = collect.parse_items(payload)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["no"], "42")
        self.assertEqual(rows[0]["deliveryFee"], "3000")
        self.assertEqual(rows[0]["supplyActive"], "true")
    def test_parse_list(self):
        data = {"list": {"item": [{"no": 1}, {"no": 2}]}}
        self.assertEqual(len(collect.parse_items(data)), 2)
    def test_no_item_field_rejected(self):
        with self.assertRaises(ValueError):
            collect.parse_items({"list": {}})
    def test_error_rejected_without_echoing_secret(self):
        with self.assertRaisesRegex(ValueError, "API reported an error"):
            collect.parse_items({"error": "secret-should-not-echo"})
if __name__ == "__main__":
    unittest.main()

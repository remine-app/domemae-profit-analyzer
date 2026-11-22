import unittest,datetime
from naver_insight import make_payload,safe_trends
class InsightTests(unittest.TestCase):
 def test_payload(self):
  p=make_payload('50000000',['정리함'],7,datetime.date(2026,11,22))
  self.assertEqual(p['startDate'],'2026-11-16')
  self.assertEqual(p['keyword'],[{'name':'정리함','param':['정리함']}])
 def test_rejects_category_label(self):
  with self.assertRaises(ValueError): make_payload('생활용품',['정리함'])
 def test_safe_parse(self):
  d={'results':[{'title':'정리함','data':[{'period':'2026-11-21','ratio':54.1}]}]}
  self.assertEqual(safe_trends(d)[0]['relative_click_index'],54.1)

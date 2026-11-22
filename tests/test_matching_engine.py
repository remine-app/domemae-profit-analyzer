import unittest
from matching_engine import identity,evaluate,dome_to_standard,suggestions
class IdentityTests(unittest.TestCase):
 def sample(self):
  s={'source':'domemae','source_id':'1','title':'ABC 모델123 수납함 검정',
     'gtin':'1234567890123','option':'검정','quantity':'1','active':'true'}
  m={'marketplace':'coupang','market_item_id':'11','market_title':'ABC 모델123 수납함 블랙',
     'market_gtin':'1234567890123','market_option':'검정','market_quantity':'1'}
  return s,m
 def test_exact_identity_candidate_not_selling_approval(self):
  s,m=self.sample()
  self.assertEqual(identity(s,m)[0],'EXACT_CANDIDATE')
  self.assertEqual(evaluate(s,m)['decision'],'NOT_APPROVED')
 def test_option_difference_blocks(self):
  s,m=self.sample();m['market_option']='화이트'
  self.assertEqual(identity(s,m)[0],'CONFLICT')
 def test_gtin_different_blocks(self):
  s,m=self.sample();m['market_gtin']='9999999999999'
  self.assertEqual(identity(s,m)[0],'CONFLICT')
 def test_title_alone_never_exact(self):
  s,m=self.sample();s['gtin']='';m['market_gtin']=''
  self.assertNotEqual(identity(s,m)[0],'EXACT_CANDIDATE')
 def test_missing_option_blocks(self):
  s,m=self.sample();s.pop('option')
  self.assertEqual(identity(s,m)[0],'REVIEW')
 def test_missing_market_data_never_margin(self):
  s,m=self.sample();r=evaluate(s,m)
  self.assertEqual(r['verified_contribution'],'')
 def test_supplier_detail_missing_does_not_hallucinate_cost(self):
  rows=dome_to_standard([{'no':'1','title':'수납함','price':'9000','deliveryFee':'3000'}])
  self.assertEqual(rows[0]['supply_price'],'')
 def test_suggestions_are_review_only(self):
  s,m=self.sample();res=suggestions([s],[m])
  self.assertTrue(res)
  self.assertEqual(res[0]['decision'],'NOT_APPROVED')

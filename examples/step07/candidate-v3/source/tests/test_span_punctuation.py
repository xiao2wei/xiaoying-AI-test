import unittest
from policy_agent.evaluation import align_span
class SpanPunctuationTests(unittest.TestCase):
 def test_terminal_punctuation_only(self):
  self.assertEqual(align_span('共同签字后报销。',['共同签字后报销，即按规定办理。']),'共同签字后报销')
 def test_no_word_or_numeric_fuzzy_repair(self):
  self.assertEqual(align_span('1万元。',['10万元，另有要求。']),'1万元。')
  self.assertEqual(align_span('不能报销。',['可以报销，即按规定办理。']),'不能报销。')

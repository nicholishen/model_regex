import unittest
import pickle
from mnr import ModelNumberRegex


class TestModelNumberRegex(unittest.TestCase):

    m = ModelNumberRegex()

    def test_match_cases(self):
        """Testing cases that should return True"""
        cases = (
            ('*DD2B080ACV3', 'XDD2B080ACV3',),
            ('G(*)(T,X,M)(*)B(*)', 'G123',),
            ('AB/CD/EF123*(*)(C,D,E)F-9,10', 'CD123',),
            ('9,10', '9',),
            ('58PH*090-(A,C,E)--0**14', '58PHX090C--0XX14',),
            ('C(A,C,D,E)36B34+TDR', 'CE36B',),
            ('FC/MC/PC32A+TXV', 'PC32A',),
            ('CH33-50/60C+TDR', 'CH3360C',),
            ('L*48/60Z9', 'LX60Z',),
            ('L85UF1V104/118F14', 'L85UF',),
            ('CR33-30/36A+TDR+TXV', 'CR33-36A',),
            ('CF/CM/CU24A+TXV', 'CF2',),
        )
        results = [self.m.transform(case[0]).match(case[1]) for case in cases]
        self.assertNotIn(False, results)

    def test_not_match_cases(self):
        """Testing cases that should return False"""

        cases = (
            ('*DD2B080ACV3', 'XDD2B081ACV3',),
            ('G(*)(T,X,M)(*)B(*)', 'X123',),
            ('AB/CD/EF123*(*)(C,D,E)F-9,10', 'FK123',),
            ('9,10', '8',),
            ('58PH*090-(A,C,E)--0**14', '58PHX090C--0XX17',),
            ('C(A,C,D,E)36B34+TDR', 'CE36B36',),
            ('FC/MC/PC32A+TXV', 'PX32A',),
            ('CH33-50/60C+TDR', 'CX3360C',),
            ('L*48/60Z9', 'LX60Z6',),
            ('L85UF1V104/118F14', 'L85UF2',),
            ('CR33-30/36A+TDR+TXV', 'CR33-36B',),
            ('CF/CM/CU24A+TXV', 'CF25',),
        )
        results = [self.m.transform(case[0]).match(case[1]) for case in cases]
        self.assertNotIn(True, results)

    def test_raise_on_malformed_mn(self):
        with self.assertRaises(Exception):
            mf = 'ABC123(A,BC'
            matcher = ModelNumberRegex(mf)
            print(matcher)

    def test_pickle_and_attributes(self):
        matcher1 = ModelNumberRegex('ABC123*')
        pkl = pickle.dumps(matcher1)
        matcher2 = pickle.loads(pkl)
        r1 = (matcher1.pattern, matcher1.model_number, matcher1._chunks,)
        r2 = (matcher2.pattern, matcher2.model_number, matcher2.chunks,)

        self.assertEqual(r1, r2)

    def test_regex_chunks(self):
        matcher = self.m.transform('*U1(CD,DK,TT)**--16')
        self.assertEqual(tuple, type(matcher.chunks))
        self.assertEqual(6, len(matcher.chunks))

    #########################################################
    # Rulset tests
    #########################################################

    def test_rule0(self):
        matcher = self.m.transform('ABC123/345DEF')
        self.assertEqual(r'ABC(123|345)DEF', matcher.pattern)

    def test_rule1_rule3(self):
        t = '(1,2,3)'
        self.assertEqual('(1|2|3)', self.m.transform(t).pattern)
        t = 'AB,CD,EF'
        self.assertEqual('(AB|CD|EF)', self.m.transform(t).pattern)
        t = 'AB/CD/EF'
        self.assertEqual('(AB|CD|EF)', self.m.transform(t).pattern)

    def test_rule2(self):
        self.assertEqual('123',
                         self.m.transform('123(A,B)').chunks[0].pattern
                         )
        self.assertEqual('123',
                         self.m.transform('123***').chunks[0].pattern
                         )

    def test_rule4(self):
        self.assertEquals(r'\w123', self.m.transform('*123').pattern)
        self.assertEquals(r'123\w+', self.m.transform('123*').pattern)

    def test_rule5(self):
        self.assertEquals(r'-?-?-?123', self.m.transform('---123').pattern)

    def test_rule6(self):

        self.assertEquals(r'(\w{1,5})', self.m.transform('(*)').pattern)


if __name__ == '__main__':
    unittest.main()

#
# Copyright (c) 2018 by nicholishen.  All rights reserved.
#
# This version of the mnr library can be redistributed under CC BY-NC 4.0 licence.
# For any other use, please contact nicholishen (https://github.com/nicholishen)

r"""Support for mnr: A library for tranforming HVAC model numbers 
into regex for comparison.

H.V.A.C. manufacturers (MFR) submit model-numbers (variable in nature) to the AHRI
in order to certify equipment efficiency ratings. The AHRI then takes the 
model-numbers (MN) submitted by the MFR and includes them in a certification 
database (as submitted by MFR). Since all MFR have a different MN nomenclature they 
have to submit a model number in a pseudo-regex format so that minor variations in 
MNs will still fall into the proper equipment category. Data congruency 
issues have arrisen since the AHRI doesn't enforce strict standards for these MN 
sumittals and MFR are submitting these 'pseudo-regex's' using whatever methods 
their private internal policies stiplate. The following is an example 
of the aforementioned challenge:
    (AB|BC|CD)123\w{1,5}  how it should be submitted (regex-compliant)
    (AB,BC,CD)123*        how MFR 'A' submits it (umm, not bad)
    AB/BC/CD123***        how MFR 'B' submits it (could you guys just do like 'A'?)
    ...
    'L83UF1V57/72E12'     (wtf)

MNR cuts through the confusion and converts these shitty-re's into the beautiful re's 
they were meant to be. Additionally, this module provides the unique ability to 
match partial-model-numbers to a full regex using a reverse-regex match. This is a 
necessary feature for db filtering since a partial MN query should yield a match in a 
field that contains the full MN regex. So in otherwords, instead of matching a partial
re to a full string, we're actually matching a partial string to a full re. 

_Example MFR model-number nomenclature:
    https://www.lennox.com/lib/legacy-res/pdfs/lennox_model_and_serial_nomenclature.pdf

Examples:
    legit_query = 'TAB123Z4X'
    shitty_model_number = '*AB,CD123(X1,Y1,Z1)4*'
    matcher = ModelNumberRegex(shitty_model_number)
    if matcher.is_match(legit_query):
        print(f'{legit_query} matches up with {shitty_model_number}')

    matcher = ModelNumberRegex()
    is_a_match = matcher.transform(shitty_model_number).is_match(legit_query)

TODO:
    * Make MNR.transform return an object instead of regex string.
    * Make MNR.match return object instead of bool.
"""

import re
from collections import namedtuple


PatternChunk = namedtuple('PatternChunk', 'pattern size')


class ModelNumberRegex(object):
    """Converts HVAC model-number's shitty-re to good-re
    Attributes:
        chunks (:obj:`list` of :obj:`tuple`): The new regex split into chunks
            via PatternChunk namedtuples.
        pattern (str): The full pattern of the new regex.
    """

    def __init__(self, model_number: str=None):
        """ 
        Initializes the original model number if set in the constructor. 
        Patterns are compiled once to reduce overhead and set as instance 
        objects so they can be easily pickled. 
        Args:
            model_number (:obj: `str`, optional) The shitty-re to be 'compiled'
        """
        self._chunks = tuple()
        self._model_number = model_number
        self._pattern0 = re.compile(r'\d{2,3}/\d{2,3}')
        self._pattern1 = re.compile(r'^(?:\w{1,3},)+')
        self._pattern1_sub1 = re.compile(r'^\w{1,2},\w{1,2}$')
        self._pattern2 = re.compile(r'^\w+')
        self._pattern3 = re.compile(r'^\((?:\w{1,3},?)+\)')
        self._pattern4 = re.compile(r'^\*+')
        self._pattern4_sub1 = re.compile(r'^\*$')
        self._pattern5 = re.compile(r'^-+')
        self._pattern6 = re.compile(r'^\(\*\)')
        if model_number:
            self.transform()

    def __str__(self):
        return f'{self.model_number} -> {self.pattern}'

    def __repr__(self):
        return f'<ModelNumberRegex object: {self.model_number}>'

    @property
    def model_number(self) -> str:
        """str: Returns the model-number in its original shitty form."""
        return self._model_number

    @property
    def chunks(self):
        return self._chunks

    def transform(self, model_number: str=None) -> 'ModelNumberRegex':
        """self: Converts mfr psuedo-regex model-numbers to real-regex and 
        stores them for rapid reverse matches; returns the new regex. 

        Works by parsing the shitty-re from left to right by chunking 
        the variable compents according to the rules and trimming the 
        remaining string until nothing is left.
        Think of it like a pac-man parser: this is pacman -> :V
        :V '(A,B,C)123' -> []
               :V '123' -> ['(A|B|C)']
                     :V -> ['(A|B|C)', '123']

        Args:
            model_number (:obj: `str`, optional) The shitty-re to be 'compiled'
        Returns:
            ModelNumberRegex - self
        """

        # check if model number has been properly set or raise
        if model_number:
            self._model_number = model_number

        if not self._model_number:
            raise AttributeError('No model number specified')

        if not isinstance(self._model_number, str):
            raise ValueError('Model number must be string')

        # split off equipment modification options.
        # we only want the primary option
        self._rem_str = self._model_number.split('+')[0]

        def _rule0():
            """This will capture and replace 2-3 digit options that 
            are nested in the string and separated by a slash. These
            are then replaced with a [mimic] rulset for options so it
            can then be processed down-stream as normal so the regex
            chunk will be added in the corrent sequence. 
            Example: 
                XXXXX123/456XX -> XXXXX(123,456)XX
            """
            # match_obj = re.search(r'\d{2,3}/\d{2,3}', self._rem_str)
            match_obj = self._pattern0.search(self._rem_str)
            if match_obj is not None:
                group = match_obj.group()
                span = match_obj.span()
                left = self._rem_str[:span[0]]
                right = self._rem_str[span[1]:]
                group = '({})'.format(group.replace('/', ','))
                self._rem_str = left + group + right
        # run rule 0
        _rule0()

        # we can now safely swap slashes for commas
        self._rem_str = self._rem_str.replace('/', ',')
        # clear pattern and set chunks to a new list instead of tuple
        self._chunks = []
        self.pattern = ''

        def _rule1():
            """ Ruleset 1: 
            Replace loose option groups not encapsulated in
            parens. This also includes options with slashes since we replaced
            slahes with commas. 
            Example: 
                AB,BC,CD -> (AB|BC|CD)
            """
            try:
                # pattern = re.match(r'^(\w{1,3},)+', self._rem_str).group()
                pattern = self._pattern1.match(self._rem_str).group()
                options = pattern.split(',')
                begin = sum([len(item) for item in options]) + len(options) - 1
                end = begin + len(options[0])
                # if re.match(r'^(\w{1,2},\w{1,2})$', self._rem_str) is None:
                if self._pattern1_sub1.match(self._rem_str) is None:
                    options[len(options)-1] = self._rem_str[begin:end]
                    self._rem_str = self._rem_str[end:]
                else:
                    options[len(options)-1] = self._rem_str[begin:]
                    self._rem_str = ''
                pattern = '({})'.format('|'.join(options))
                return PatternChunk(pattern, min([len(x) for x in options]))
            except AttributeError:
                return None

        def _rule2():
            """Ruleset #2:
            The meat and potatoes. These are the non-variable constants
            in the shitty expressions.
            Example:
                ABS12(...)
                adds 'ABS12' to the re chunk and trims the remaining string.
            """
            try:
                # pattern = re.match(r'^(\w+)', self._rem_str).group()
                pattern = self._pattern2.match(self._rem_str).group()
                size = len(pattern)
                self._rem_str = self._rem_str[size:]
                return PatternChunk(pattern, size)
            except AttributeError:
                return None

        def _rule3():
            """Ruleset #3:
            Fix (paren) option groups. ...so close...
            Example:
                (AB,CD,EF) -> (AB|CD|EF)
            """
            try:
                # pattern = re.match(r'^\((\w{1,3},?)+\)', self._rem_str).group()
                pattern = self._pattern3.match(self._rem_str).group()
                size = len(pattern.split(',')[0]) - 1
                self._rem_str = self._rem_str[len(pattern):]
                pattern = pattern.replace(',', '|')
                return PatternChunk(pattern, size)
            except AttributeError:
                return None

        def _rule4():
            r"""Ruleset #4:
            Replace * wildcards with \w{1}. \w+ if is last char in
            remaining string.
            Examples:
                *BC123 -> \w -> trimmed=BC123 
                * -> 
            """
            try:
                # pattern = re.match(r'^(\*+)', self._rem_str).group()
                pattern = self._pattern4.match(self._rem_str).group()
                size = len(pattern)
                # second_match = re.match(r'^(\*)$', self._rem_str)
                second_match = self._pattern4_sub1.match(self._rem_str)
                self._rem_str = self._rem_str[size:]
                if second_match:
                    return PatternChunk(pattern.replace('*', r'\w+', 1), size)
                else:
                    return PatternChunk(pattern.replace('*', r'\w'), size)
            except AttributeError:
                return None

        def _rule5():
            """Ruleset #5:
            Make hyphens optional
            Example:
                ---123 -> -?-?-? -> trimmed=123
            """
            try:
                # pattern = re.match(r'^(-+)', self._rem_str).group()
                pattern = self._pattern5.match(self._rem_str).group()
                self._rem_str = self._rem_str[len(pattern):]
                return PatternChunk(pattern.replace('-', '-?'), -1)
            except AttributeError:
                return None

        def _rule6():
            r"""Ruleset #6:
            The wildcard that should be dragged out to pasture and put
            down... 
            Replace (*) with \w{1,5}
            """
            try:
                # pattern = re.match(r'^(\(\*\))', self._rem_str).group()
                pattern = self._pattern6.match(self._rem_str).group()
                self._rem_str = self._rem_str[len(pattern):]
                return PatternChunk(r'(\w{1,5})', -1)
            except AttributeError:
                return None

        # list of rule funcs
        rules = [_rule1, _rule2, _rule3, _rule4, _rule5, _rule6, ]
        # counter in case a rule fails to parse. Breaks to exc on
        # unknown parsing error.
        break_count = 0
        # iterate through the rulsets. trim the remaining string
        # if a func has modified the remaining string the restart
        # the parsing loop
        while self._rem_str:
            for rule in rules:
                res = rule()
                if res is not None:
                    self._chunks.append(res)
                    break_count = 0
                    break
            # debs = self._rem_str
            if break_count > 2:
                raise Exception(
                    f"Couldn't parse the remaining: {self._rem_str}")
            break_count += 1
        if self._rem_str:
            raise Exception('Unknown parsing error.')
        # time to join the full pattern
        self.pattern = ''.join([r.pattern for r in self._chunks])
        # making the chunk sequence immutable
        self._chunks = tuple(self._chunks)
        return self

    def is_match(self, model_to_match: str) -> bool:
        """bool: Compares a model-number to the newly formed regex and
        return the result of the match. Partial strings can be compared.
        Args:
            model_to_match (str): A partial or full model number to match 
                against the transformed regex model. 
        """
        mn = model_to_match
        if not mn:
            return False
        for chunk in self._chunks:
            if chunk.size > len(mn):
                # the length of the chunk exceeds the length of the remaining string to parse
                if re.match(r'^\w+$', chunk.pattern):
                    # no wilcards in chunk so string must match exactly
                    try:
                        m = re.match(mn, chunk.pattern).group()
                        # the remaining string hss been matched to the chunk
                        return True
                    except:
                        # it is definitely not a match
                        return False
                elif re.match(r'^(\((\w+\|)+(\w+)?\))$', chunk.pattern):
                    # we need to check if the chunk is an options group and if
                    # it is then we need to reduce the length of each option to
                    # the length of the remaining string to be parsed and evalute the partial
                    options = chunk.pattern[1: -1].split('|')
                    options = [opt[:-len(mn)] for opt in options]
                    res = mn in options  # res for debug
                    return res
                else:
                    # we cannot compare criteria, defer to outter loop
                    break
            try:
                # alls good with the size of the remaining string to be parsed.
                # is it a match or is it not? No match will throw exception
                m = re.match(chunk.pattern, mn).group()
                # it is a match. trim the remaing string and continue to the next loop iteration
                mn = mn[len(m):]
            except:
                # nomatch
                return False
        # nothing failed so it must be a match
        return True

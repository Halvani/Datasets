__author__ = "Oren Halvani"
__copyright__ = "Copyright 2023, Oren Halvani, Derivation of *** Corpus of German-Language Fiction ***"
__license__ = "Apache 2.0"
__version__ = "1.0.0"
__maintainer__ = "Oren Halvani"
__status__ = "Production"


import os
import re 
import shutil
from pathlib import Path
from enum import Enum
import operator as Operator
from tqdm.auto import tqdm
from pprint import pprint
import numpy as np
import torch
import spacy


try:
    from functools import cache
except:
    from functools import lru_cache
    cache = lru_cache(maxsize=None)


@cache
def get_spacy_nlp(model):
    import spacy
    return spacy.load(model, disable=["parser", "ner"])

@cache
def safe_patterns(model):
    patterns_filepath = Path(os.getcwd(), "modules", "POSNoise_PatternList_De_Ver.1.1.txt")
    return [[t.text.lower() for t in get_spacy_nlp(model)(p)] for p in patterns_filepath.read_text().split("\n")]

abbrev_pos_tags = {"NOUN": "#", "PROPN": "§", "VERB": "Ø", "ADJ": "@", "ADV": "©", "NUM": "µ", "SYM": "$", "X": "¥"}

def posnoise_(text, model):
    tokens = list(get_spacy_nlp(model)(text))
    bitmask = np.zeros(len(tokens), dtype=bool)
    
    for safe_pattern in safe_patterns(model):
        i = 0
        pattern_index = 0
        while i < len(tokens):
            if tokens[i].text.lower() == safe_pattern[pattern_index]:
                pattern_index += 1
                if pattern_index == len(safe_pattern):
                    for j in range(i - len(safe_pattern) + 1, i + 1):
                        bitmask[j] = True
                    pattern_index = 0
            else:
                i -= pattern_index
                pattern_index = 0
            i += 1
            
    for i, token in enumerate(tokens):
        if token.text in {"'m", "'d", "'s", "'t", "'ve", "'ll", "'re", "'ts", "'em", "'Tis"}:
            bitmask[i] = 1
        if token.pos_ == "NUM" and re.match("[^0-9]+", token.text):
            bitmask[i] = 1
            
    return bitmask, tokens


def posnoise(text, model):
    bitmask, tokens = posnoise_(text, model)
    for m, token in reversed(list(zip(bitmask, tokens))):
        if m == 0:
            replace_token = abbrev_pos_tags.get(token.pos_, token.text)
            text = text[0:token.idx] + replace_token + text[(token.idx+len(token.text)):]
    return text

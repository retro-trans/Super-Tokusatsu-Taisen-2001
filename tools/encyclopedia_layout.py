"""Compact encyclopedia labels in the two 128px index columns."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = json.loads((ROOT/'work/ui/encyclopedia/index_labels.en.json').read_text(encoding='utf-8'))


def replacements(table):
    """Key by original string address; never replace matching gameplay text."""
    return {table[int(index)]: pair for index,pair in META['labels'].items()}


def encode(pair, original):
    import insert
    reverse = {code: text for text,code in insert.ENC_ENCYC.items()}
    actual = ''.join(reverse.get(code, '') for code in original)
    assert actual == pair[0], (actual, pair)
    words = insert.encode_line_tokens(insert.TOKEN.findall(pair[1]), {}, insert.ENC_ENCYC)
    span = insert.px_of(pair[1])
    assert span <= META['column_width'], (pair, span)
    return words

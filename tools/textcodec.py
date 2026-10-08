"""Decode game glyph codes to readable text (and back).

Tags used in decoded text:
  \\n        FFFB newline           <p>       FFFC page break (wait for button)
  <name>..</name>   FF33 .. FF30 speaker tag at line start
  <c1> <c2> <c3> </c>  FF31/FF32/FF33 colour on, FF30 colour reset
  [HERO1] FF01  [HERO2] FF02  [HERO3] FF03  [HERO4] FF04  [VAR5] FF05  [VAR6] FF06
  {XXXX}    any other code that has no character
Terminators (FFFE / FFFD) are not part of the text; they are kept as metadata.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from kana_table import TABLE  # noqa: E402

_cm = json.load(open(os.path.join(ROOT, "work", "font", "charmap.json"), encoding="utf-8"))
CHARS = dict(TABLE)
for k, v in _cm["map"].items():
    CHARS[int(k)] = v
UNCERTAIN = set(_cm["uncertain"])
PLACE = {0xFF01: "[HERO1]", 0xFF02: "[HERO2]", 0xFF03: "[HERO3]", 0xFF04: "[HERO4]",
         0xFF05: "[VAR5]", 0xFF06: "[VAR6]"}


def decode(words, mark_uncertain=False):
    out = []
    ws = list(words)
    i = 0
    if ws and ws[0] == 0xFF33 and 0xFF30 in ws:
        k = ws.index(0xFF30)
        out.append("<name>" + decode(ws[1:k], mark_uncertain) + "</name>")
        i = k + 1
        if i < len(ws) and ws[i] == 0xFFFB:
            i += 1
    for w in ws[i:]:
        if w == 0xFFFB:
            out.append("\n")
        elif w == 0xFFFC:
            out.append("<p>")
        elif w == 0xFF30:
            out.append("</c>")
        elif w in (0xFF31, 0xFF32, 0xFF33):
            out.append("<c%d>" % (w - 0xFF30))
        elif w in PLACE:
            out.append(PLACE[w])
        elif w < 0xFF00 and w in CHARS:
            ch = CHARS[w]
            out.append(ch + ("̲" if mark_uncertain and w in UNCERTAIN else ""))
        else:
            out.append("{%04X}" % w)
    return "".join(out)


def speaker_and_body(words):
    ws = list(words)
    if ws and ws[0] == 0xFF33 and 0xFF30 in ws:
        k = ws.index(0xFF30)
        return decode(ws[1:k]), decode(ws[k + 1:])
    return None, decode(ws)

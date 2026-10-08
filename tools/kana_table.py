"""Partial code->char table for codes 0-319 (read from the font atlas).
Kanji (>=320) are filled in by work/font/charmap.json once verified."""
ROW0 = " 0123456789" + "\u2160\u25a1\u2161\u2163\u2164" + "あいうえおかきくけこさしすせそた"
ROW1 = "ちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをんぁぃ"
ROW2 = "ぅぇぉゃゅょっがぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽ"
ROW3 = "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミ"
ROW4 = "ムメモヤユヨラリルレロワヲンァィゥェォャュョッガギグゲゴザジズゼ"
ROW5 = "ゾダヂヅデドバビブベボパピプペポヴABCDEFGHIJKLMNO"
ROW6 = "PQRSTUVWXYZabcdefghijklmnopqrstu"
ROW7 = "vwxyz！？～ー、。，．：；・‥…「」『』［］（）＋－±×÷＝"
# Row 8-9: symbols and UI icons. Icons get bracketed names (kept as-is in translation).
ROW8 = ["》", "☆", "♥", "{drop}", "ヶ", "＜", "＞", "＆", "％", "／", "｜", "‖", "←", "→", "{bar}", "{bar2}",
        "α", "β", "γ", "♂", "♀", "直", "間", "{P}", "{M}", "{AP}", "{S}", "{L}", "{man}", "{sword}", "{c286}", "{c287}"]
ROW9 = ["①", "②", "③", "④", "⑤", "{P2}", "{A2}", "{kai1}", "{kai2}", "ま"] + [""] * 6 + ["★"] + [""] * 6 +        ["{c311}", "{c312}", "{c313}", "{c314}", "{c315}", "{c316}", "{c317}", "Ｖ", "※"]
TABLE = {}
for base, row in enumerate([ROW0, ROW1, ROW2, ROW3, ROW4, ROW5, ROW6, ROW7, ROW8, ROW9]):
    for i, ch in enumerate(row):
        if ch:
            TABLE[base * 32 + i] = ch

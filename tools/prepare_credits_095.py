"""Apply verified credit-name readings; preserve unverified original names."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLAYERS = 'https://www.mobygames.com/game/47280/slayers-royal/credits/playstation/'
PS = 'https://www.mobygames.com/game/13299/sega-ages-2500-vol1-phantasy-star-generation1/credits/ps2/'
READINGS = [
    ('大田雄一', 'Yuichi Ota', PS),
    ('中江真二', 'Shinji Nakae', 'https://www.mobygames.com/person/754810/shinji-nakae/'),
    ('青木健太', 'Kenta Aoki', 'https://srw.wiki.cre.jp/wiki/スタッフ:青木健太'),
    ('宮島浩一', 'Koichi Miyajima', 'https://nanonano.base.ec/p/00001'),
    ('藤井康文', 'Yasufumi Fujii', 'https://ci.nii.ac.jp/author/DA13123987'),
    ('高橋充', 'Mitsuru Takahashi', SLAYERS),
    ('吉川義賢', 'Yoshitaka Yoshikawa', SLAYERS),
    ('海老沼勇介', 'Yusuke Ebinuma', 'https://www.mobygames.com/person/1474187/yusuke-ebinuma/'),
    ('木全和光', 'Kazumitsu Kimata', SLAYERS),
    ('竹内哲也', 'Tetsuya Takeuchi', SLAYERS),
    ('江良奈緒美', 'Naomi Era', PS),
    ('寺澤奈津子', 'Natsuko Terasawa', 'https://www.mobygames.com/game/202744/tales-of-symphonia/credits/ps2/'),
    ('間中哲也', 'Tetsuya Manaka', SLAYERS),
    ('伊東大典', 'Daisuke Ito', PS),
    ('菅井信義', 'Nobuyoshi Sugai', 'https://www.mobygames.com/game/22869/sega-ages-2500-vol6-puzzle-action-bonanza-bros/credits/ps2/'),
]


def main():
    path = ROOT / 'work/translation/en/movies.en.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    before = json.loads(json.dumps(data))
    found = set()
    for page in data['credit_pages']:
        lines = page['body'].split('\n')
        for i, line in enumerate(lines):
            for jp, latin, _ in READINGS:
                if re.sub(r'\s+', '', line) == jp:
                    lines[i] = latin
                    found.add(jp)
                elif line == latin:
                    found.add(jp)
        page['body'] = '\n'.join(lines)
    assert len(found) == len(READINGS), found
    assert data['clips'] == before['clips'], 'Caption wording/timings changed'
    data.update(version='0.9.5', preview_revision=8,
                purpose='Native copyright/title cards and verified English credit names; both ending review movies regenerated')
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    raw = ROOT / 'work/translation/en/movies.json'
    if raw.exists():
        original = json.loads(raw.read_text(encoding='utf-8'))
        for key in ('credit_pages', 'version', 'preview_revision', 'purpose'):
            original[key] = data[key]
        raw.write_text(json.dumps(original, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    remaining = [dict(heading=p['heading'], name=line)
                 for p in data['credit_pages'] for line in p['body'].split('\n')
                 if re.search(r'[\u3040-\u30ff\u3400-\u9fff]', line)]
    report = dict(version='0.9.5', verified_readings=[dict(original=j, english=e, source=s) for j,e,s in READINGS],
                  policy='Retain original proper names until a reading is verified; do not substitute guesses.',
                  remaining_names=remaining,
                  credit_source='https://raido.moe/staff/ps1/ps1_super_tokusatsu_taisen_2001.html')
    (ROOT/'work/translation/en/credits_readings.en.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Updated %d verified names; %d original names awaiting verified readings.' % (len(found),len(remaining)))


if __name__ == '__main__':
    main()

"""Apply the user's Man Spider naming correction consistently.

Dry run by default; --write updates the English text and stripped git copies.
Japanese source fields and historical build records remain untouched.
"""
import json
import sys
from pathlib import Path
import strip_jp

ROOT = Path(__file__).resolve().parents[1]
OLD,NEW = 'Spider Man','Man Spider'


def planned():
    files = [ROOT/'work/glossary/names.json',ROOT/'work/glossary/library.json']
    files += sorted((ROOT/'work/translation/en').rglob('*.json'))
    for path in files:
        if path.name.endswith('.en.json'):
            continue
        text=path.read_text(encoding='utf-8')
        if OLD in text:
            yield path,text,text.replace(OLD,NEW)
    path=ROOT/'work/translation/en/replacements.json'
    before=path.read_text(encoding='utf-8')
    data=json.loads(before)
    pair=[r're:\bSpider[ -]Man\b',NEW]
    if pair not in data['pairs']:
        data['pairs'].append(pair)
        yield path,before,json.dumps(data,ensure_ascii=False,indent=1)+'\n'
    path=ROOT/'docs/library_glossary.md'
    text=path.read_text(encoding='utf-8')
    if OLD in text:
        yield path,text,text.replace(OLD,NEW)


def main():
    changes=list(planned())
    print(('Write' if '--write' in sys.argv else 'Dry run')+': Spider Man -> Man Spider')
    for path,before,after in changes:
        print('%s: %d old-name occurrences'%(path.relative_to(ROOT),before.count(OLD)))
        if path.suffix=='.json':
            json.loads(after)
        if '--write' in sys.argv:
            path.write_text(after,encoding='utf-8')
            if path.suffix=='.json' and path.name!='names.json':
                copy=path.with_name(path.stem+'.en.json')
                copy.write_text(json.dumps(strip_jp.clean(json.loads(after)),ensure_ascii=False,indent=1)+'\n',encoding='utf-8')
    print('%d source files; targeted stripped English copies included.'%len(changes))


if __name__=='__main__':
    main()

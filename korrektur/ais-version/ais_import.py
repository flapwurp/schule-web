"""PROTOTYP: AIS.chat-Ausgabe -> text_<code>.json + korrektur_<code>.json (für kw.py).
  python3 ais_import.py <ausgabe1.txt> [<ausgabe2.txt> …] <lauf-ordner>   (Abschrift und Korrektur dürfen getrennt sein)
Prüft das Format, löst Wortfolgen in Positionen auf und meldet jede Zeile, die nicht passt."""
import sys, json, re, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'werkzeuge')); from resolve import find

SIGNS = {'W', 'A', 'G', 'Sb', 'St', 'R', 'Z', 'Präp', 'Wdh', 'Г'}
MUSTER = set('KOM SVA TEMP VERB ADV ART KOMP ST PRAEP FF WW VW REG RS SB REL WF'.split())

RAND = '.,;:!?"\'()[]'
def finde(toks, phrase):
    """Erst exakt; sonst Satzzeichen am Wortrand ignorieren („happy“ findet „happy.“)."""
    try: return find(toks, phrase, literal=True)
    except ValueError: pass
    occ = 1
    if '#' in phrase: phrase, occ = phrase.rsplit('#', 1); occ = int(occ)
    p = [w.strip(RAND) for w in phrase.split()]; t = [w.strip(RAND) for w in toks]
    hits = [i for i in range(len(t) - len(p) + 1) if t[i:i + len(p)] == p]
    if len(hits) < occ or not p: raise ValueError(phrase)
    s = hits[occ - 1]; return s + 1, s + len(p)

def parse(txt):
    code, sec, text, err, hint, probs = None, None, {}, [], [], []
    for n, raw in enumerate(txt.splitlines(), 1):
        line = raw.strip().strip('`')
        if not line: continue
        m = re.match(r'#+\s*CODE\s+(\S+)', line, re.I)
        if m: code = m.group(1); continue
        m = re.match(r'#+\s*(TEXT|FEHLER|HINWEISE)', line, re.I)
        if m: sec = m.group(1).upper(); continue
        if sec == 'TEXT':
            m = re.match(r'B(\d+)\s*Z(\d+)\s*:\s?(.*)$', line)
            if not m: probs.append(f'Zeile {n}: TEXT-Zeile nicht erkannt: {line[:60]}'); continue
            text.setdefault(m.group(1), {})[str(int(m.group(2)))] = m.group(3).strip()
        elif sec == 'FEHLER':
            p = [x.strip() for x in line.split('|')]
            m = re.match(r'B(\d+)\s*Z(\d+)$', p[0]) if p else None
            if not m or len(p) < 6: probs.append(f'Zeile {n}: Fehlerzeile nicht erkannt: {line[:70]}'); continue
            err.append(dict(b=int(m.group(1)), z=int(m.group(2)), w=p[1], sign=p[2], c=p[3], m=p[4].upper(), conf=p[5].lower()[:1],
                            gap=len(p) > 6 and p[6].lower().startswith('l'), src=n))
        elif sec == 'HINWEISE': hint.append(line)
    return code, text, err, hint, probs

def main_multi(files, wd):
    """Mehrere Dateien, mehrere Codes je Datei: TEXT und FEHLER werden je Code zusammengeführt."""
    blocks = {}
    for f in files:
        parts = re.split(r'(?m)^(?=\s*#+\s*CODE\s)', open(f, encoding='utf-8').read())
        for p in parts:
            code, text, err, hint, probs = parse(p)
            if not code: continue
            B = blocks.setdefault(code, dict(text={}, err=[], hint=[], probs=[]))
            for b, zs in text.items(): B['text'].setdefault(b, {}).update(zs)
            B['err'] += err; B['hint'] += [h for h in hint if h.lower() != 'keine']; B['probs'] += probs
    for code, B in blocks.items():
        if not B['text']: print(f'Code {code}: nur FEHLER, keine Abschrift – übersprungen'); continue
        main(None, wd, (code, B['text'], B['err'], B['hint'], B['probs']))

def main(f, wd, pre=None):
    code, text, err, hint, probs = pre or parse(open(f, encoding='utf-8').read())
    if not code: sys.exit('Kein „### CODE“ gefunden.')
    S = json.load(open(f'{wd}/seiten.json'))
    if code not in S: sys.exit(f'Code {code} ist im Scan nicht vorhanden.')
    json.dump(text, open(f'{wd}/text_{code}.json', 'w'), ensure_ascii=False, indent=0)
    K = []
    for e in err:
        tag = f"B{e['b']} Z{e['z']} »{e['w']}«"
        if e['sign'] not in SIGNS: probs.append(f'{tag}: unbekanntes Zeichen {e["sign"]!r}'); continue
        if e['m'] not in MUSTER: probs.append(f'{tag}: unbekanntes Muster {e["m"]!r} (übernommen)')
        if e['conf'] not in 'seu': e['conf'] = 'e'
        line = text.get(str(e['b']), {}).get(str(e['z']))
        if line is None: probs.append(f'{tag}: Zeile fehlt in TEXT'); continue
        try: w0, w1 = finde(line.split(), e['w'])
        except ValueError: probs.append(f'{tag}: Wortfolge steht nicht in der Zeile'); continue
        k = dict(b=e['b'], pos=[[e['z'], w0, w1]], sign=e['sign'], c=e['c'], m=e['m'], conf=e['conf'])
        if e['gap']: k['gap'] = True
        K.append(k)
    json.dump(K, open(f'{wd}/korrektur_{code}.json', 'w'), ensure_ascii=False)
    print(f'Code {code}: {sum(len(v) for v in text.values())} Zeilen, {len(err)} Fehlerzeilen, {len(K)} übernommen')
    print('Hinweise:', ' / '.join(hint) or 'keine')
    print('Probleme:\n  ' + '\n  '.join(probs) if probs else 'Probleme: keine')

if __name__ == '__main__':
    main_multi(sys.argv[1:-1], sys.argv[-1])

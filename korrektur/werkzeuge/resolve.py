"""Kurzform -> korrektur_<code>.json. Eintrag: (blatt, [(zeile, 'phrase')], sign, c, muster, conf, gap)
Phrase: Tokens wie in der Transkription; [..] markiert die anzustreichenden Tokens; '#n' = n-tes Vorkommen."""
import json, sys
def find(toks, phrase, literal=False):
    occ = 1
    if '#' in phrase: phrase, occ = phrase.rsplit('#', 1); occ = int(occ)
    p = phrase.split(); clean = p if literal else [w.strip('[]') for w in p]
    if not literal and '[' in phrase:
        i0 = next(i for i, w in enumerate(p) if w.startswith('[')); i1 = next(i for i, w in enumerate(p) if w.endswith(']'))
    else: i0, i1 = 0, len(p) - 1
    hits = [i for i in range(len(toks) - len(clean) + 1) if toks[i:i + len(clean)] == clean]
    if len(hits) < occ: raise ValueError(f'nicht gefunden: {phrase!r} in {" ".join(toks)}')
    s = hits[occ - 1]; return s + i0 + 1, s + i1 + 1
def run(o, code, E):
    T = json.load(open(f'{o}/text_{code}.json')); out = []
    for b, pos, sign, c, m, conf, *g in E:
        P = []
        for z, ph in pos:
            w0, w1 = find(T[str(b)][str(z)].split(), ph); P.append([z, w0, w1])
        e = dict(b=b, pos=P, sign=sign, c=c, m=m, conf=conf)
        if g and g[0]: e['gap'] = True
        out.append(e)
    json.dump(out, open(f'{o}/korrektur_{code}.json', 'w'), ensure_ascii=False)

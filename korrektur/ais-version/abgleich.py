"""PROTOTYP: zwei Abschriften desselben Codes vergleichen (z. B. Sonnet 5.5 und GPT-5.5).
  python3 abgleich.py <abschrift1.txt> <abschrift2.txt>
Abweichende Wörter werden als unsicher gemeldet: Dort hat mindestens ein Modell geglättet oder falsch gelesen."""
import sys, re, difflib
def lies(f):
    T = {}; code = None; sec = None
    for l in open(f, encoding='utf-8'):
        m = re.match(r'#+\s*CODE\s+(\S+)', l.strip())
        if m: code = m[1]; sec = None; continue
        m = re.match(r'#+\s*(TEXT|FEHLER|HINWEISE)', l.strip(), re.I)
        if m: sec = m[1].upper(); continue
        if sec != 'TEXT': continue
        m = re.match(r'B(\d+)\s*Z(\d+)\s*:\s?(.*)$', l.strip())
        if m and code: T.setdefault(code, {})[(int(m[1]), int(m[2]))] = m[3].strip()
    return T
def norm(s):  # Anführungszeichen-Stil und Fallunterschied am Wortanfang nach Anführungszeichen sind kein Lesefehler
    return s.replace("'", '"').replace('“', '"').replace('”', '"').replace('‘', '"').replace('’', "'")
A, B = lies(sys.argv[1]), lies(sys.argv[2])
for code in sorted(set(A) & set(B)):
    a, b = A[code], B[code]; n = 0; out = []
    for k in sorted(set(a) | set(b)):
        x, y = norm(a.get(k, '')).split(), norm(b.get(k, '')).split()
        for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, x, y, autojunk=False).get_opcodes():
            if op != 'equal': n += 1; out.append(f'  B{k[0]} Z{k[1]}: {" ".join(x[i1:i2]) or "–"}  |  {" ".join(y[j1:j2]) or "–"}')
    w = sum(len(v.split()) for v in a.values())
    print(f'Code {code}: {n} Abweichungen bei {w} Wörtern'); print('\n'.join(out))

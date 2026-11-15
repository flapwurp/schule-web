"""Werkzeuge für die sprachliche Vorkorrektur (Klausurbögen mit QR/Ankerpunkten oder normales liniertes Papier).
  python3 kw.py einlesen    <scan.pdf> <ordner>                 Klausurbögen: ausrichten, sortieren, Wortfelder, Kontrollbilder
  python3 kw.py frei        <scan.pdf> <ordner>                 Normales liniertes Papier: Seiten entzerren, Lineatur/Rand je Seite,
                                                                Wortfelder, Kontrollbilder, uebersicht_*.png zur Schüler-Zuordnung
  python3 kw.py zuordnen    <ordner> <zuordnung.json>           {"S01": [1,2,3], "S02": [4,5]} Seiten -> Codes/Blätter
  python3 kw.py ausrichten  <ordner> <code>                     Wortfelder automatisch an die Transkription anpassen
                                                                (startet immer von den Rohfeldern; merge/split erst danach)
  python3 kw.py check       <ordner> <code>                     Transkription vs. Wortfelder prüfen
  python3 kw.py merge       <ordner> <code> <blatt> <zeile> <i> Wortfeld i und i+1 verbinden
  python3 kw.py split       <ordner> <code> <blatt> <zeile> <i> [x]  Wortfeld i teilen
  python3 kw.py bild        <ordner> <code> <blatt>             Kontrollbild neu erzeugen
  python3 kw.py zoom        <ordner> <code> <blatt> <z0> <z1>   Zeilen z0..z1 vergrößert (2x) zum Lesen
  python3 kw.py vorschlaege <ordner> <code>                     korrektur_<code>.json -> vorschlaege_<code>.json (+ Prüfliste)
  python3 kw.py paket       <ordner> <ausgabe.pdf>              Vorkorrektur-PDF bauen (braucht meta.json, pool.json)
Dateiformate: siehe SKILL.md.  Version 2026-10-21"""
import sys, os, json, datetime, uuid, cv2, numpy as np, pypdfium2 as pdfium

DPI = 150; MM = DPI / 25.4
CANON = np.float32([[11, 11], [199, 11], [11, 286], [199, 286]]) * MM   # Mittelpunkte der Ankerpunkte
W, H = int(210 * MM), int(297 * MM)

def find_anchors(g):
    h, w = g.shape
    _, bw = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    n, lab, st, cen = cv2.connectedComponentsWithStats(bw)
    exp = (6 * MM) ** 2
    c = [cen[j] for j in range(1, n) if 0.5 * exp < st[j, 4] < 1.6 * exp
         and 0.7 < st[j, 2] / st[j, 3] < 1.4 and st[j, 4] / (st[j, 2] * st[j, 3]) > 0.75]
    if len(c) < 4: return None
    c = np.float32(c); ctr = np.float32([w / 2, h / 2])
    # die vier Punkte, die am weitesten in Richtung jeder Bildecke liegen
    out = []
    for cx, cy in [(0, 0), (w, 0), (0, h), (w, h)]:
        out.append(c[np.argmin(np.hypot(c[:, 0] - cx, c[:, 1] - cy))])
    return np.float32(out)

def decode_qr(img):
    det = cv2.QRCodeDetector()
    x0, x1, y0, y1 = int(160 * MM), int(198 * MM), int(6 * MM), int(44 * MM)
    crop = img[y0:y1, x0:x1]
    for f in (1, 2, 3):
        c = cv2.resize(crop, None, fx=f, fy=f, interpolation=cv2.INTER_CUBIC) if f > 1 else crop
        for pre in (lambda z: z, lambda z: cv2.threshold(z, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]):
            d = det.detectAndDecode(pre(c))[0]
            if d: return d
    return ''

def normalize(g):
    a = find_anchors(g)
    if a is None: return None, '', 'Ankerpunkte nicht gefunden'
    best = None
    for order in ([0, 1, 2, 3], [3, 2, 1, 0]):          # aufrecht oder 180° gedreht
        M = cv2.getPerspectiveTransform(a[order], CANON)
        al = cv2.warpPerspective(g, M, (W, H), borderValue=255)
        q = decode_qr(al)
        if q.startswith('KORR|'): return al, q, 'ok'
        ink = (255 - al[int(12 * MM):int(38 * MM), int(166 * MM):int(192 * MM)]).mean()
        if best is None or ink > best[0]: best = (ink, al)
    return best[1], '', 'QR nicht lesbar (Ausrichtung über Druckbild geschätzt)'

def line_y(k): return (52 + 10 * (k - 1)) * MM          # Lineatur der Vorlage (150 dpi)
X_TEXT0, X_MARGIN = 19.5 * MM, 157.5 * MM

def geo_vorlage():
    return dict(w=W, h=H, lines=[round(42 * MM)] + [round(line_y(k)) for k in range(1, 24)], side='R',
                lt=round(X_TEXT0), rt=round(X_MARGIN - 10))
def geo_of(info): return info.get('geo') or geo_vorlage()

def align(color):
    g = cv2.cvtColor(color, cv2.COLOR_BGR2GRAY)
    a = find_anchors(g)
    if a is None: return None, None, 'Ankerpunkte nicht gefunden'
    for order in ([0, 1, 2, 3], [3, 2, 1, 0]):
        M = cv2.getPerspectiveTransform(a[order], CANON)
        al = cv2.warpPerspective(g, M, (W, H), borderValue=255)
        q = decode_qr(al)
        if q.startswith('KORR|'):
            return cv2.warpPerspective(color, M, (W, H), borderValue=(255, 255, 255)), q, 'ok'
    return None, None, 'QR nicht lesbar'

def words(color, gap=9):
    g = cv2.cvtColor(color, cv2.COLOR_BGR2GRAY)
    ink = (g < 150).astype(np.uint8)
    ink[:, :int(X_TEXT0)] = 0; ink[:, int(196 * MM):] = 0          # Randschrift der SuS wird mit erfasst
    ink[:int(50 * MM), int(X_MARGIN):] = 0                           # Aufdruck 'Korrekturrand'
    ink = cv2.morphologyEx(ink, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    out = {}
    for k in range(1, 24):
        y0, y1 = int(line_y(k) - 8.5 * MM), int(line_y(k) + 2.2 * MM)
        band = ink[y0:y1]; col = band.sum(0) > 0
        segs, x = [], 0
        while x < W:
            if col[x]:
                s = x
                while x < W and col[x]: x += 1
                segs.append([s, x])
            else: x += 1
        merged = []
        for s in segs:
            if merged and s[0] - merged[-1][1] < gap: merged[-1][1] = s[1]
            else: merged.append(s)
        merged = [m for m in merged if band[:, m[0]:m[1]].sum() > 20]
        if merged: out[k] = merged
    return out

def control_image(color, segs, path, lines=None):
    v = color.copy(); L = lines or geo_vorlage()['lines']
    for k in range(1, len(L)):
        y = int(L[k])
        cv2.putText(v, f'Z{k}', (4, y - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 200), 1)
        for i, (a, b) in enumerate(segs.get(k, [])):
            cv2.line(v, (a, y + 4), (b, y + 4), (0, 160, 0), 2)
            cv2.putText(v, str(i + 1), (a, y + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 120, 0), 1)
    cv2.imwrite(path, v)

# ---------- Normales liniertes Papier ----------
def deskew_frei(g):
    H_, W_ = g.shape; m = ((255 - g) > 18).astype(np.float32); best = None
    for a in np.arange(-2.5, 2.51, 0.05):
        M = cv2.getRotationMatrix2D((W_ / 2, H_ / 2), a, 1); r = cv2.warpAffine(m, M, (W_, H_))
        p = r[:, int(W_ * .1):int(W_ * .9)].sum(1); sc = float((p ** 2).sum())
        if best is None or sc > best[0]: best = (sc, a)
    return best[1]

def rulings(g):
    """Lineatur als regelmäßiges Gitter: Periode per Autokorrelation, Phase per Gittersumme, dann jede Linie auf das
    lokale Maximum (±15 % der Periode) einrasten. So ziehen kräftige Schriftzeilen die Linien nicht weg."""
    H_, W_ = g.shape; m = ((255 - g) > 18).astype(np.float32)
    p = m[:, int(W_ * .1):int(W_ * .9)].sum(1) / (W_ * .8)
    q = p - p.mean(); ac = [float((q[:-k] * q[k:]).sum()) for k in range(1, 140)]
    cands = [k for k in range(30, 138) if ac[k - 1] >= ac[k - 2] and ac[k - 1] >= ac[k] and ac[k - 1] > 0]
    if not cands:                                           # Fallback: alte Spitzenmethode
        pk = [y for y in range(2, H_ - 2) if p[y] > 0.45 and p[y] == p[y - 2:y + 3].max()]
        out = []
        for y in pk:
            if not out or y - out[-1] >= 25: out.append(y)
        return out
    T0 = max(cands, key=lambda k: ac[k - 1])
    for k in sorted(cands):                                 # kleinste Periode, deren Vielfache die stärkste erklärt
        if k >= 30 and ac[k - 1] > 0.6 * ac[T0 - 1] and abs(T0 / k - round(T0 / k)) < 0.08: T0 = k; break
    best = None                                             # Periode fein (0,05 px) und Phase gemeinsam
    for T in np.arange(T0 - 1.5, T0 + 1.51, 0.05):
        for ph in range(int(T)):
            ys = np.arange(ph, H_ - 2, T).astype(int)
            sc = float(np.maximum.reduce([p[np.clip(ys + d, 0, H_ - 1)] for d in (-1, 0, 1)]).sum())
            if best is None or sc > best[0]: best = (sc, T, ph)
    _, T, ph = best; r = max(3, int(0.15 * T)); out = []
    for y0 in np.arange(ph, H_ - 2, T):
        y0 = int(round(y0)); lo, hi = max(0, y0 - r), min(H_, y0 + r + 1)
        y = lo + int(np.argmax(p[lo:hi]))
        if p[y] > 0.3: out.append(y)
    return out

def margin_lines(g):
    """Senkrechte Randlinien des Blocks: Liste von x-Positionen (links/rechts), ggf. leer."""
    H_, W_ = g.shape; bw = ((255 - g) > 35).astype(np.uint8)
    vl = cv2.morphologyEx(bw, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 150)))
    col = vl.sum(0).astype(float); col[:20] = 0; col[-20:] = 0
    col = np.convolve(col, np.ones(3), mode='same'); out = []
    for x in np.argsort(-col):
        if col[x] <= 0.4 * H_: break
        if all(abs(int(x) - o) > 30 for o in out): out.append(int(x))
    return sorted(out)

def words_frei(color, L, gap=None):
    """Schriftzüge (zusammenhängende Komponenten) der Zeile zuordnen, in der ihr Schwerpunkt liegt; dann je Zeile
    nach Lücken in Wörter gruppieren. Ober-/Unterlängen über die Linie erzeugen so keine Geisterfelder."""
    g = cv2.cvtColor(color, cv2.COLOR_BGR2GRAY); inv = 255 - g
    bw = (inv > 45).astype(np.uint8) * 255
    hl = cv2.morphologyEx(bw, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (120, 1)))
    vl = cv2.morphologyEx(bw, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 120)))
    ink = cv2.subtract(bw, cv2.bitwise_or(hl, vl))
    ink = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 5)))   # durch Linien getrennte Striche schließen
    ink = cv2.morphologyEx(ink, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    sp = float(np.median(np.diff(L))); gap = gap or max(10, round(0.24 * sp))
    n, lab, st, cen = cv2.connectedComponentsWithStats(ink, 8)
    # durchscheinende Rückseite / Schatten: nur Schriftzüge mit genug wirklich dunkler Tinte zählen
    paper = float(np.percentile(g, 75)); strong = (g < paper - 90) & (lab > 0)
    nstrong = np.bincount(lab[strong], minlength=n)
    per = {}; Wd = ink.shape[1]
    for j in range(1, n):
        x, y, w, h, area = st[j]
        if area < 12 or x < 6 or x + w > Wd - 6: continue
        if nstrong[j] < max(6, 0.15 * area): continue
        if w > 0.6 * Wd: continue                                   # Reste von Linien
        cy = cen[j][1]
        k = next((k for k in range(1, len(L)) if L[k - 1] < cy <= L[k] + 3), None)
        if k is None: continue
        per.setdefault(k, []).append([int(x), int(x + w), int(area)])
    out = {}
    for k, comps in per.items():
        comps.sort(); merged = []
        for c in comps:
            if merged and c[0] - merged[-1][1] < gap: merged[-1][1] = max(merged[-1][1], c[1]); merged[-1][2] += c[2]
            else: merged.append(list(c))
        merged = [[m[0], m[1]] for m in merged if m[2] >= 40 or m[1] - m[0] >= 14]
        if merged: out[k] = merged
    return out

def frei(scan, wd):
    os.makedirs(wd, exist_ok=True)
    doc = pdfium.PdfDocument(scan); seiten, warn, thumbs = {}, [], []
    for i in range(len(doc)):
        n = i + 1
        img = cv2.cvtColor(np.array(doc[i].render(scale=150 / 72).to_pil()), cv2.COLOR_RGB2BGR)
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY); Hh, Ww = g.shape
        a = deskew_frei(g); M = cv2.getRotationMatrix2D((Ww / 2, Hh / 2), a, 1)
        img = cv2.warpAffine(img, M, (Ww, Hh), borderValue=(255, 255, 255)); g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        L = rulings(g)
        if len(L) < 5: warn.append(f'Seite {n}: keine Lineatur erkannt – nur liniertes Papier wird unterstützt'); continue
        d = np.diff(L); sp = float(np.median(d))
        if sp < 40: warn.append(f'Seite {n}: Linienabstand sehr klein ({sp:.0f} px) – kariert? Zeilen bitte prüfen')
        if any(abs(x - sp) > 10 for x in d): warn.append(f'Seite {n}: unregelmäßige Lineatur erkannt – Zeilen bitte prüfen')
        segs = words_frei(img, L)
        big = [sg for v in segs.values() for sg in v if sg[1] - sg[0] >= 30]
        if big:
            lt = float(np.percentile([a_ for a_, b_ in big], 5)); rt = float(max(b_ for a_, b_ in big))
        else: lt, rt = Ww * .15, Ww * .85
        ml = margin_lines(g)                      # gedruckte Randlinien haben Vorrang vor der Schriftkante
        li = [x for x in ml if x < Ww / 2 and x <= lt + 25]; re_ = [x for x in ml if x > Ww / 2 and x >= rt - 25]
        if li: lt = float(max(li))
        if re_: rt = float(min(re_))
        side = 'L' if lt > Ww - rt else 'R'       # Anmerkungen auf die breitere Randseite
        geo = dict(w=Ww, h=Hh, lines=[int(y) for y in L], side=side, lt=round(lt), rt=round(rt), randlinien=ml)
        cv2.imwrite(f'{wd}/seite_{n:02d}.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 88])
        control_image(img, segs, f'{wd}/kontrolle_seite_{n:02d}.png', L)
        seiten[n] = dict(segs=segs, geo=geo, drehung=round(a, 2))
        t = cv2.resize(img[:int(Hh * .45)], None, fx=0.22, fy=0.22, interpolation=cv2.INTER_AREA)
        cv2.putText(t, f'Seite {n}', (6, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 200), 2); thumbs.append(t)
    json.dump({str(k): v for k, v in seiten.items()}, open(f'{wd}/seiten_frei.json', 'w'))
    for j in range(0, len(thumbs), 12):          # Übersicht: je Bild 12 Seiten (obere Seitenhälfte)
        grp = thumbs[j:j + 12]; th, tw_ = max(t.shape[0] for t in grp), max(t.shape[1] for t in grp)
        rows = [np.hstack([cv2.copyMakeBorder(t, 0, th - t.shape[0], 0, tw_ - t.shape[1] + 8, cv2.BORDER_CONSTANT, value=(255, 255, 255))
                           for t in grp[r:r + 4]] + [np.full((th, tw_ + 8, 3), 255, np.uint8)] * (4 - len(grp[r:r + 4]))) for r in range(0, len(grp), 4)]
        cv2.imwrite(f'{wd}/uebersicht_{j // 12 + 1}.png', np.vstack([cv2.copyMakeBorder(r, 0, 8, 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255)) for r in rows]))
    print(f'{len(doc)} Seiten gelesen, {len(seiten)} mit Lineatur.')
    for k, v in seiten.items():
        print(f'  Seite {k}: {len(v["geo"]["lines"]) - 1} Zeilen, Rand {"links" if v["geo"]["side"] == "L" else "rechts"}, '
              f'{sum(len(x) for x in v["segs"].values())} Wortfelder, Drehung {v["drehung"]}°')
    print('Warnungen:', warn or 'keine')

def zuordnen(wd, zfile):
    import shutil
    S = json.load(open(f'{wd}/seiten_frei.json')); Z = json.load(open(zfile)); out, used = {}, []
    for code, pages in Z.items():
        out[code] = {}
        for b, n in enumerate(pages, 1):
            if str(n) not in S: print(f'FEHLER: Seite {n} fehlt oder hat keine Lineatur'); continue
            if n in used: print(f'FEHLER: Seite {n} doppelt zugeordnet')
            used.append(n); info = S[str(n)]
            out[code][str(b)] = dict(scan_seite=n, segs=info['segs'], geo=info['geo'])
            shutil.copy(f'{wd}/seite_{n:02d}.jpg', f'{wd}/{code}_B{b}.jpg')
            shutil.copy(f'{wd}/kontrolle_seite_{n:02d}.png', f'{wd}/kontrolle_{code}_B{b}.png')
    rest = sorted(set(map(int, S)) - set(used))
    json.dump(out, open(f'{wd}/seiten.json', 'w'))
    for code, bl in out.items(): print(f'  {code}: Seiten {[bl[b]["scan_seite"] for b in sorted(bl, key=int)]}')
    print('Nicht zugeordnete Seiten:', rest or 'keine')

def einlesen(scan, wd):
    os.makedirs(wd, exist_ok=True)
    doc = pdfium.PdfDocument(scan); found, problems = {}, []
    for i in range(len(doc)):
        img = cv2.cvtColor(np.array(doc[i].render(scale=150 / 72).to_pil()), cv2.COLOR_RGB2BGR)
        al, q, msg = align(img)
        if al is None: problems.append(f'Scan-Seite {i+1}: {msg}'); continue
        _, kid, code, blatt = q.split('|'); blatt = int(blatt)
        if (code, blatt) in found: problems.append(f'Scan-Seite {i+1}: Code {code} Blatt {blatt} doppelt'); continue
        found[(code, blatt)] = dict(kid=kid, scan_seite=i + 1)
        cv2.imwrite(f'{wd}/{code}_B{blatt}.jpg', al, [cv2.IMWRITE_JPEG_QUALITY, 88])
        segs = words(al); found[(code, blatt)]['segs'] = segs
        control_image(al, segs, f'{wd}/kontrolle_{code}_B{blatt}.png')
    codes = {}
    for (code, blatt), v in sorted(found.items()): codes.setdefault(code, {})[blatt] = v
    for code, bl in codes.items():
        missing = [b for b in range(1, max(bl) + 1) if b not in bl]
        if missing: problems.append(f'Code {code}: Blatt {missing} fehlt')
    json.dump({c: {b: dict(scan_seite=v['scan_seite'], segs=v['segs']) for b, v in bl.items()} for c, bl in codes.items()},
              open(f'{wd}/seiten.json', 'w'))
    print(f'{len(doc)} Scan-Seiten gelesen.')
    for code, bl in codes.items():
        print(f'  Code {code}: Blätter {sorted(bl)} (aus Scan-Seiten {[bl[b]["scan_seite"] for b in sorted(bl)]}), '
              f'Wörter je Blatt {[sum(len(x) for x in bl[b]["segs"].values()) for b in sorted(bl)]}')
    print('Probleme:', problems or 'keine')



# ---------- Transkription / Wortfelder ----------


def load(o): return json.load(open(f'{o}/seiten.json'))
def tokens(line): return line.split()

def check(o, code):
    S = load(o)[code]; T = json.load(open(f'{o}/text_{code}.json')); bad = 0
    for b in sorted(set(S) | set(T), key=int):
        segs = S.get(b, {}).get('segs', {}); tx = T.get(b, {})
        for z in sorted(set(segs) | set(tx), key=int):
            n, m = len(segs.get(z, [])), len(tokens(tx.get(z, '')))
            if n != m:
                bad += 1; print(f'Blatt {b} Zeile {z}: {m} Wörter transkribiert, {n} Wortfelder  |  {tx.get(z, "")[:70]}')
    print('OK – alle Zeilen stimmen.' if not bad else f'{bad} Zeile(n) abweichend.')

def edit(o, code, b, z, i, op, x=None):
    S = load(o); sg = S[code][b]['segs'][z]; i = int(i) - 1
    if op == 'merge': sg[i:i + 2] = [[sg[i][0], sg[i + 1][1]]]
    else:
        a, e = sg[i]
        if x is None:
            img = cv2.imread(f'{o}/{code}_B{b}.jpg', 0); Lg = geo_of(S[code][b])['lines']; y = int(Lg[int(z)])
            col = (img[int(Lg[int(z) - 1]) + 6:y - 2, a:e] < 150).sum(0)
            runs, cur = [], None
            for k, v in enumerate(col):
                if v == 0: cur = [k, k] if cur is None else [cur[0], k]
                elif cur: runs.append(cur); cur = None
            if not runs: print('Keine Lücke gefunden – bitte x angeben.'); return
            r = max(runs, key=lambda r: r[1] - r[0]); x = a + (r[0] + r[1]) // 2
        x = int(x); sg[i:i + 1] = [[a, x], [x, e]]
    json.dump(S, open(f'{o}/seiten.json', 'w')); print(f'Blatt {b} Zeile {z}: jetzt {len(sg)} Wortfelder')

def bild(o, code, b):
    S = load(o); img = cv2.imread(f'{o}/{code}_B{b}.jpg')
    control_image(img, {int(k): v for k, v in S[code][b]['segs'].items()}, f'{o}/kontrolle_{code}_B{b}.png', geo_of(S[code][b])['lines']); print('ok')



def _align_core(F, toks, prof=None):
    """Wortfelder an die Tokens anpassen. Die Zeile wird in 'Atome' zerlegt (Wortfelder, innerhalb breiter Felder
    zusätzlich an tintenarmen Stellen), dann per DP in n Gruppen geteilt: Gruppenbreite ~ erwartete Wortbreite
    (Zeichenzahl), Grenzen bevorzugt in echten Lücken, ungenutzte breite Lücken werden bestraft."""
    F = [list(f) for f in F]; n = len(toks)
    while len(F) > n and len(F) > 1:              # kleine Randfetzen weit außen verwerfen
        if F[-1][1] - F[-1][0] < 22 and F[-1][0] - F[-2][1] > 40: F.pop(); continue
        if F[0][1] - F[0][0] < 22 and F[1][0] - F[0][1] > 40: F.pop(0); continue
        break
    if n == 0 or not F or (len(F) == n and prof is None): return 0.0, F
    def _w(t):                                          # erwartete Breite in Zeichen; Satzzeichen zählen mit (Handschrift)
        t = t.replace('~', '').replace('[?]', '')
        return max(1, sum(1 if ch.isalnum() else 0.9 for ch in t)) + 0.8
    wts = [_w(t) for t in toks]
    X0, X1 = F[0][0], F[-1][1]; cw = (X1 - X0) / sum(wts); exp = [w * cw for w in wts]
    # Atome: (x0, x1, Grenztyp davor: 'gap' mit Breite oder 'cut')
    atoms = []
    for j, (a0, a1) in enumerate(F):
        parts = [(a0, a1, ('gap', F[j][0] - F[j - 1][1]) if j > 0 else ('start', 0))]
        if prof is not None and a1 - a0 > 1.2 * cw:
            p = prof[a0:a1]; zero = p <= 0; runs, x = [], 0
            while x < len(p):                           # tintenfreie Spalten innerhalb des Feldes = echte Lücke
                if zero[x]:
                    s0 = x
                    while x < len(p) and zero[x]: x += 1
                    if s0 > 2 and x < len(p) - 2 and x - s0 >= 2: runs.append((s0, x))
                else: x += 1
            if runs:
                pts, cur = [], a0
                for r0, r1 in runs: pts.append((cur, a0 + r0)); cur = a0 + r1
                pts.append((cur, a1))
                parts = [(pts[0][0], pts[0][1], parts[0][2])] + [(q0, q1, ('gap', q0 - pts[k][1])) for k, (q0, q1) in enumerate(pts[1:])]
        for (q0, q1, kind) in parts:                    # breite Stücke zusätzlich an tintenarmen Stellen schneiden
            cuts = []
            if prof is not None and q1 - q0 > 1.6 * cw:
                pr = np.convolve(prof[q0:q1].astype(float), np.ones(5) / 5, mode='same')
                th = np.percentile(pr, 30)
                for x in range(5, q1 - q0 - 5):
                    if pr[x] <= pr[x - 4:x + 5].min() and pr[x] <= th:
                        if not cuts or x - cuts[-1] > 0.7 * cw: cuts.append(x)
            if not cuts and q1 - q0 > 2.5 * cw and prof is None:
                cuts = list(range(int(cw), q1 - q0 - int(cw) // 2, max(4, int(cw * 0.7))))
            pp = [q0] + [q0 + c for c in cuts] + [q1]
            for k in range(len(pp) - 1):
                atoms.append((pp[k], pp[k + 1], kind if k == 0 else ('cut', 0)))
    A = len(atoms); INF = float('inf')
    def bcost(i):                                       # Kosten einer Grenze vor Atom i
        kind, gw = atoms[i][2]
        return -0.8 * min(gw / cw, 2.5) if kind == 'gap' else 1.2
    pre = [0.0] * (A + 1)                               # Strafe für ungenutzte Lücken (Präfixsumme)
    for i in range(A):
        kind, gw = atoms[i][2]; pre[i + 1] = pre[i] + (0.9 * min(gw / cw, 3) if kind == 'gap' else 0)
    dp = [[INF] * (A + 1) for _ in range(n + 1)]; bk = [[0] * (A + 1) for _ in range(n + 1)]; dp[0][0] = 0
    for t in range(1, n + 1):
        for e in range(t, A - (n - t) + 1):
            for s_ in range(t - 1, e):
                c0 = dp[t - 1][s_]
                if c0 == INF: continue
                w = atoms[e - 1][1] - atoms[s_][0]
                c = c0 + abs(w - exp[t - 1]) / cw + (pre[e] - pre[s_ + 1]) + (bcost(s_) if t > 1 else 0)
                if c < dp[t][e]: dp[t][e] = c; bk[t][e] = s_
    if dp[n][A] == INF: return INF, F
    out, e = [], A
    for t in range(n, 0, -1):
        s_ = bk[t][e]; out.append([int(atoms[s_][0]), int(atoms[e - 1][1])]); e = s_
    return dp[n][A], out[::-1]

def _align_line(F, toks, prof=None):
    """Wie _align_core, probiert aber zusätzlich, kleine abgesetzte Stücke am Zeilenanfang/-ende zu verwerfen
    (Unterlängen der Zeile darüber, Punkte, Durchschein-Reste). Verwerfen kostet etwas; die günstigste Variante gewinnt."""
    if not F or not toks: return F
    F = [list(f) for f in F]
    if prof is None and len(F) == len(toks): return F
    best = None
    def small(f, nb):
        return f[1] - f[0] < 45 and abs(nb) > 18
    for dl in range(0, 2):
        for dr in range(0, 3):
            if dl + dr >= len(F): continue
            ok = all(small(F[i], F[i + 1][0] - F[i][1]) for i in range(dl)) and \
                 all(small(F[len(F) - 1 - i], F[len(F) - 1 - i][0] - F[len(F) - 2 - i][1]) for i in range(dr))
            if not ok: continue
            G = F[dl:len(F) - dr]
            if len(G) < 1: continue
            c, out = _align_core(G, toks, prof)
            c += 1.8 * (dl + dr)
            if best is None or c < best[0]: best = (c, out)
    return best[1] if best else F

def ausrichten(o, code):
    S = load(o); T = json.load(open(f'{o}/text_{code}.json')); n_adj = 0
    for b, lines in T.items():
        info = S[code][b]
        if 'segs_roh' not in info: info['segs_roh'] = json.loads(json.dumps(info['segs']))   # Rohfelder sichern
        segs = info['segs'] = json.loads(json.dumps(info['segs_roh'])); img = None   # immer von den Rohfeldern ausgehen
        for z, line in lines.items():
            toks = line.split(); F = segs.get(z, [])
            if not F: print(f'Blatt {b} Zeile {z}: Text, aber keine Schrift erkannt – Zeile prüfen'); continue
            if True:
                if img is None: img = cv2.imread(f'{o}/{code}_B{b}.jpg')
                Lg = geo_of(S[code][b])['lines']; zi = int(z)
                band = cv2.cvtColor(img[int(Lg[zi - 1]) + 6:int(Lg[zi]) - 2], cv2.COLOR_BGR2GRAY)
                prof = (band < np.percentile(band, 75) - 60).sum(0)
                neu = _align_line(F, toks, prof)
                if neu != F:
                    n_adj += 1; print(f'Blatt {b} Zeile {z}: {len(F)} Felder -> {len(toks)} Wörter angepasst')
                segs[z] = neu
        for z in list(segs):
            if z not in lines: print(f'Blatt {b} Zeile {z}: Schrift erkannt, aber nicht transkribiert ({len(segs[z])} Felder) – ignoriert'); del segs[z]
        img = cv2.imread(f'{o}/{code}_B{b}.jpg')
        control_image(img, {int(k): v for k, v in segs.items()}, f'{o}/kontrolle_{code}_B{b}.png', geo_of(S[code][b])['lines'])
    json.dump(S, open(f'{o}/seiten.json', 'w'))
    print(f'Code {code}: {n_adj} Zeilen angepasst. Kontrollbilder neu erzeugt – angepasste Zeilen dort prüfen.')

def zoom(o, code, b, z0, z1):
    Lg = geo_of(load(o)[code][b])['lines']; z0, z1 = max(1, int(z0)), min(len(Lg) - 1, int(z1))
    img = cv2.imread(f'{o}/kontrolle_{code}_B{b}.png'); y0 = max(0, int(Lg[z0 - 1]) - 15); y1 = int(Lg[z1]) + 30
    c = cv2.resize(img[y0:y1, :], None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC); p = f'{o}/zoom_{code}_B{b}_{z0}-{z1}.png'
    cv2.imwrite(p, c); print(p)

# ---------- Korrekturliste ----------
def vorschlaege(o, code):
    T = json.load(open(f'{o}/text_{code}.json')); S = json.load(open(f'{o}/seiten.json'))[code]
    K = json.load(open(f'{o}/korrektur_{code}.json'))
    SIGNS = {'W', 'A', 'G', 'Sb', 'St', 'R', 'Z', 'Präp', 'Wdh', 'Г'}
    out, fehler = [], []
    woerter = sum(1 for b in T.values() for l in b.values() for t in l.split() if not t.startswith('~~') and t != '·')
    for n, e in enumerate(K, 1):
        b = str(e['b']); txt = []
        if e['sign'] not in SIGNS: fehler.append(f'#{n}: unbekanntes Zeichen {e["sign"]!r}')
        if e.get('conf', 's') not in ('s', 'e', 'u'): fehler.append(f'#{n}: conf muss s/e/u sein')
        segs = []
        for z, w0, w1 in e['pos']:
            toks = T.get(b, {}).get(str(z), '').split(); nseg = len(S.get(b, {}).get('segs', {}).get(str(z), []))
            if not (1 <= w0 <= w1 <= len(toks)) or len(toks) != nseg:
                fehler.append(f'#{n}: Blatt {b} Zeile {z} Wort {w0}-{w1} ungültig (Tokens {len(toks)}, Wortfelder {nseg})'); continue
            txt.append(' '.join(toks[w0 - 1:w1])); segs.append([z, w0, w1])
        if e.get('gap') and segs: segs = [segs[-1][:1] + [segs[-1][2], segs[-1][2], 'gap']]
        if not segs: continue
        out.append(dict(b=e['b'], segs=segs, sign=e['sign'], c=e.get('c', ''), conf=e.get('conf', 's'), m=e.get('m', '')))
        mark = '»' + ' / '.join(txt) + '«' + (' ⎵' if e.get('gap') else '')
        print(f"B{b} Z{segs[0][0]:>2} {mark:<34} {e['sign']}{' (' + e['c'] + ')' if e.get('c') else ''}  [{e.get('m','')}, {e.get('conf','s')}]")
    json.dump(dict(vorschlaege=out, woerter=woerter), open(f'{o}/vorschlaege_{code}.json', 'w'), ensure_ascii=False)
    print(f'Code {code}: {len(out)} Anstreichungen, {woerter} Wörter, {round(100*len(out)/max(woerter,1),1)} pro 100 Wörter')
    print('FEHLER:\n  ' + '\n  '.join(fehler) if fehler else 'Keine Fehler.')

# ---------- Paket ----------


MUSTER = {
 'KOM': 'Kommasetzung', 'SVA': '3. Person Singular / Kongruenz', 'TEMP': 'Zeitformen (simple / progressive / perfect)',
 'VERB': 'Verbformen (Gerund, Infinitiv, Verneinung, Passiv)', 'ADV': 'Adjektiv oder Adverb', 'ART': 'Artikel',
 'KOMP': 'Steigerung', 'ST': 'Wortstellung', 'PRAEP': 'Präpositionen', 'FF': 'False Friends / deutsche Strukturen',
 'WW': 'Wortwahl / Kollokation', 'VW': "Verwechslungswörter (their/there, its/it's, then/than …)",
 'REG': 'Register (Kurzformen, Umgangssprache)', 'RS': 'Rechtschreibung', 'SB': 'Satzbau (Komma-Reihung, Satzgrenzen)',
 'REL': 'Relativpronomen (who / which / whose)', 'WF': 'Wortform (Plural, Demonstrativ)'}

PT = 72 / 150                     # px (150 dpi) -> pt
PW, PH = 595.28, 841.89
CONF = {'s': 'sicher', 'e': 'ermessen', 'u': 'unsicher'}

def esc(t):
    t = t.replace('Г', '^')                        # Vorschau-PDF: Standardschrift kennt kein Г (Arbeitsfläche zeigt Г)
    t = t.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
    return t.encode('cp1252', errors='replace')

def build(wd):
    meta = json.load(open(f'{wd}/meta.json'))
    pool = json.load(open(f'{wd}/pool.json')) if os.path.exists(f'{wd}/pool.json') else {}
    seiten = json.load(open(f'{wd}/seiten.json'))
    data = dict(format='korrektur-paket', version=2, paket_id=uuid.uuid4().hex[:12],
                klausur=dict(id=meta['id'], titel=meta['titel'], datum=meta['datum']),
                muster=meta.get('muster', MUSTER), pool=pool, eh=meta['eh'], schluessel=meta['schluessel'], codes=[],
                erstellt=datetime.date.today().isoformat())
    pages, warn = [], []
    for code, bl in sorted(seiten.items(), key=lambda x: x[0]):
        blaetter = sorted(bl, key=int)
        if not os.path.exists(f'{wd}/vorschlaege_{code}.json'): warn.append(f'Code {code}: keine Vorschläge – übersprungen'); continue
        vj = json.load(open(f'{wd}/vorschlaege_{code}.json'))
        cpages, csug = [], []
        for b in blaetter:
            segs = {int(k): v for k, v in bl[b]['segs'].items()}
            gg = geo_of(bl[b])
            cpages.append(dict(img=None, w=gg['w'], h=gg['h'], lines=gg['lines'], side=gg['side'], lt=gg['lt'], rt=gg['rt'],
                               edges={k: [v[0][0], v[-1][1]] for k, v in segs.items()}))
        for i, e in enumerate(vj['vorschlaege']):
            segs = {int(k): v for k, v in bl[str(e['b'])]['segs'].items()}; Lg = geo_of(bl[str(e['b'])])['lines']
            sg = []
            for z, w0, w1, *flag in e['segs']:
                ws = segs[z]
                if flag:
                    x0 = ws[w1 - 1][1] - 8; x1 = ws[w1][0] + 4 if w1 < len(ws) else ws[w1 - 1][1] + 22
                    if x1 - x0 < 18: x0, x1 = (x0 + x1) / 2 - 9, (x0 + x1) / 2 + 9
                    sg.append([round(x0), round(x1), round(Lg[z]) + 4, z, 'gap'])
                else: sg.append([ws[w0 - 1][0], ws[w1 - 1][1], round(Lg[z]) + 4, z])
            csug.append(dict(id=f'{code}-{i+1:02d}', page=blaetter.index(str(e['b'])), segs=sg, line=e['segs'][0][0],
                             sign=e['sign'], corr=e['c'], conf=CONF[e['conf']], muster=e['m']))
        data['codes'].append(dict(code=code, pages=cpages, sug=csug, woerter=vj.get('woerter')))
        for pi, b in enumerate(blaetter):
            pages.append((code, pi, open(f'{wd}/{code}_B{b}.jpg', 'rb').read(), [s for s in csug if s['page'] == pi], cpages[pi]))
    return data, pages, warn

def overlay(sugs, gg):
    """Vorschau der Vorschläge als PDF-Zeichenbefehle."""
    sx, sy = PW / gg['w'], PH / gg['h']
    ops = [b'q 0.56 0.06 0.06 RG 0.56 0.06 0.06 rg 1.1 w [3 2] 0 d']
    byline = {}
    for s in sugs:
        for x0, x1, y, z, *_ in s['segs']:
            ops.append(f'{x0*sx:.1f} {PH - y*sy:.1f} m {x1*sx:.1f} {PH - y*sy:.1f} l S'.encode())
        byline.setdefault(s['line'], []).append(s)
    ops.append(b'[] 0 d')
    xm = (gg['rt'] + 16) * sx if gg['side'] == 'R' else 6
    for k, lst in sorted(byline.items()):
        lst.sort(key=lambda s: s['segs'][0][0])
        txt = '  ·  '.join(s['sign'] + (f" ({s['corr']})" if s['corr'] else '') + (' ?' if s['conf'] != 'sicher' else '') for s in lst)
        y = PH - (gg['lines'][k] - 3) * sy
        size = 7 if len(txt) < 40 else 6 if len(txt) < 52 else 5
        ops.append(b'BT /F1 ' + str(size).encode() + b' Tf ' + f'{xm:.1f} {y:.1f} Td ('.encode() + esc(txt[:70]) + b') Tj ET')
    ops.append(b'BT /F1 6.5 Tf 160 830 Td (' + esc('Vorkorrektur-Vorschau (Claude): gestrichelt = Vorschlag, ? = Ermessensfrage. Bearbeiten in der Korrektur-Arbeitsfläche.') + b') Tj ET')
    ops.append(b'Q')
    return b'\n'.join(ops)

def write_pdf(data, pages, out):
    buf = bytearray(); offs = {}
    def obj(n, body):
        offs[n] = len(buf); buf.extend(f'{n} 0 obj\n'.encode()); buf.extend(body); buf.extend(b'\nendobj\n')
    buf.extend(b'%PDF-1.7\n%\xe2\xe3\xcf\xd3\n')
    npg = len(pages); first = 10
    ids = [(first + 3 * i, first + 3 * i + 1, first + 3 * i + 2) for i in range(npg)]
    JSON_ID, SPEC_ID = first + 3 * npg, first + 3 * npg + 1
    obj(3, b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>')
    imgref = {}
    for (code, pi, jpg, sugs, gg), (P, C, I) in zip(pages, ids):
        ov = overlay(sugs, gg)
        cs = b'q 595.28 0 0 841.89 0 0 cm /Im0 Do Q\n' + ov
        obj(P, f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595.28 841.89] /Resources << /XObject << /Im0 {I} 0 R >> /Font << /F1 3 0 R >> >> /Contents {C} 0 R >>'.encode())
        obj(C, f'<< /Length {len(cs)} >>\nstream\n'.encode() + cs + b'\nendstream')
        head = f'<< /Type /XObject /Subtype /Image /Width {gg["w"]} /Height {gg["h"]} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length {len(jpg)} >>\nstream\n'.encode()
        offs[I] = len(buf); buf.extend(f'{I} 0 obj\n'.encode()); buf.extend(head)
        imgref[(code, pi)] = dict(off=len(buf), len=len(jpg))
        buf.extend(jpg); buf.extend(b'\nendstream\nendobj\n')
    for c in data['codes']:
        for pi, p in enumerate(c['pages']): p['img'] = imgref[(c['code'], pi)]
    js = json.dumps(data, ensure_ascii=False).encode('utf-8')
    obj(JSON_ID, f'<< /Type /EmbeddedFile /Subtype /application#2Fjson /Length {len(js)} >>\nstream\n'.encode())
    joff = offs[JSON_ID] + len(f'{JSON_ID} 0 obj\n<< /Type /EmbeddedFile /Subtype /application#2Fjson /Length {len(js)} >>\nstream\n')
    # obj() hat den Stream-Kopf geschrieben; Inhalt nachschieben
    buf[-len(b'\nendobj\n'):] = b''
    buf.extend(js); buf.extend(b'\nendstream\nendobj\n')
    buf.extend(f'%KORRDATA {joff} {len(js)}\n'.encode())
    obj(SPEC_ID, f'<< /Type /Filespec /F (korrektur.json) /UF (korrektur.json) /Desc (Daten fuer die Korrektur-Arbeitsflaeche) /EF << /F {JSON_ID} 0 R >> >>'.encode())
    obj(1, f'<< /Type /Catalog /Pages 2 0 R /Names << /EmbeddedFiles << /Names [(korrektur.json) {SPEC_ID} 0 R] >> >> >>'.encode())
    obj(2, f'<< /Type /Pages /Kids [{" ".join(f"{P} 0 R" for P, C, I in ids)}] /Count {npg} >>'.encode())
    t = data['klausur']
    obj(4, b'<< /Title (' + esc(f"Vorkorrektur {t['id']}") + b') /Producer (Claude Vorkorrektur) >>')
    maxid = SPEC_ID + 1
    xref = len(buf)
    buf.extend(f'xref\n0 {maxid}\n0000000000 65535 f \n'.encode())
    for n in range(1, maxid):
        buf.extend((f'{offs[n]:010d} 00000 n \n' if n in offs else '0000000000 65535 f \n').encode())
    buf.extend(f'trailer\n<< /Size {maxid} /Root 1 0 R /Info 4 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode())
    open(out, 'wb').write(buf)
    return len(buf)


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a: print(__doc__); sys.exit()
    cmd = a[0]
    if cmd == 'einlesen': einlesen(a[1], a[2])
    elif cmd == 'frei': frei(a[1], a[2])
    elif cmd == 'zuordnen': zuordnen(a[1], a[2])
    elif cmd == 'check': check(a[1], a[2])
    elif cmd in ('merge', 'split'): edit(a[1], a[2], a[3], a[4], a[5], cmd, a[6] if len(a) > 6 else None)
    elif cmd == 'bild': bild(a[1], a[2], a[3])
    elif cmd == 'ausrichten': ausrichten(a[1], a[2])
    elif cmd == 'zoom': zoom(a[1], a[2], a[3], a[4], a[5])
    elif cmd == 'vorschlaege': vorschlaege(a[1], a[2])
    elif cmd == 'paket':
        data, pages, warn = build(a[1]); n = write_pdf(data, pages, a[2])
        print(a[2], len(pages), 'Seiten,', len(data['codes']), 'Codes,', sum(len(c['sug']) for c in data['codes']), 'Anstreichungen,',
              len(data['pool']), 'Muster im Förderpool,', round(n / 1e6, 2), 'MB')
        for w in warn: print('WARNUNG:', w)
    else: print(__doc__)

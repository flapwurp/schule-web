"""Erzeugt eine Demo-Arbeitsfläche mit eingebetteten synthetischen Daten (keine echten Schülerdaten).
  python3 mkdata.py <arbeitsflaeche.html> <paket-id> <ausgabe.html>"""
import json, base64, io, sys, os
from PIL import Image, ImageDraw, ImageFont
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..') + '/'
MM = 150 / 25.4; W, H = int(210 * MM), int(297 * MM)
lines = [round(42 * MM)] + [round((52 + 10 * (k - 1)) * MM) for k in range(1, 24)]
lt, rt = round(19.5 * MM), round(157.5 * MM - 10)
meta = json.load(open(R + 'ais-version/src/standard_klausur_EF.json'))
pool = json.load(open(R + 'ais-version/src/foerderpool.json'))
TXT = ['In the article the autor explains how teenagers finds their', 'identity. He says that social media have a big influence,', 'because young people compare theirself with others all', 'the time. Furthermore it is important to have friends who',
       'support you and dont judge you. In my opinion the author', 'is right, because I made similar experiences in my life.']
_d = ImageDraw.Draw(Image.new('RGB', (1, 1)))
for sz in range(34, 18, -1):   # Schriftgröße so wählen, dass der Text im Schreibbereich bleibt (nicht in den Korrekturrand läuft)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf', sz)
    if max(_d.textlength(t, font=font) for t in TXT) < round(157.5 * MM) - lt - 25: break
def page(code, b):
    im = Image.new('RGB', (W, H), 'white'); d = ImageDraw.Draw(im)
    for y in lines[1:]: d.line([(lt - 20, y), (round(157.5 * MM), y)], fill=(170, 190, 220), width=2)
    d.line([(round(157.5 * MM), 0), (round(157.5 * MM), H)], fill=(230, 160, 160), width=2)
    d.text((lt, lines[0] - 40), f'Code {code} · Blatt {b+1} (Testdaten)', fill=(90, 90, 90), font=font)
    edges = {}
    for k, t in enumerate(TXT * 3, start=1):
        if k > 18: break
        d.text((lt, lines[k] - 38), t, fill=(20, 30, 90), font=font)
        edges[k] = [lt, lt + round(d.textlength(t, font=font))]
    buf = io.BytesIO(); im.convert('P', palette=Image.ADAPTIVE, colors=8).save(buf, 'PNG', optimize=True)
    return dict(img='data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode(), w=W, h=H, lines=lines, side='R', lt=lt, rt=rt, edges=edges)
def x_of(word, k):
    t = (TXT * 3)[k - 1]; i = t.index(word); f = font
    tmp = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    return lt + round(tmp.textlength(t[:i], font=f)), lt + round(tmp.textlength(t[:i + len(word)], font=f))
codes = []
for code in ['11', '27', '42']:
    sug = []
    for i, (k, w, sign, corr, conf, m) in enumerate([(1, 'autor', 'R', 'author', 's', 'RS'), (1, 'finds', 'G', 'find', 's', 'SVA'),
            (3, 'theirself', 'G', 'themselves', 'u', 'VW'), (4, 'Furthermore', 'Z', 'Furthermore,', 'e', 'KOM'), (5, 'dont', 'R', "don't", 's', 'RS'),
            (6, 'made', 'W', 'had', 's', 'VW'), (7, 'autor', 'R', 'author', 's', 'RS')]):
        x0, x1 = x_of(w, k)
        sug.append(dict(id=f'{code}-{i+1:02d}', page=0, segs=[[x0, x1, lines[k] + 4, k]], line=k, sign=sign, corr=corr,
                        conf={'s': 'sicher', 'e': 'ermessen', 'u': 'unsicher'}[conf], muster=m))
    codes.append(dict(code=code, pages=[page(code, 0), page(code, 1)], sug=sug, woerter=350))
data = dict(format='korrektur-paket', version=2, paket_id='test' + sys.argv[2], klausur=dict(id='TEST-K1', titel='Testklausur (synthetisch)', datum='15.11.2026'),
            muster={k: v.get('titel', k) for k, v in pool.items()}, pool=pool, eh=meta['eh'], schluessel=meta['schluessel'], codes=codes)
s = open(sys.argv[1], encoding='utf-8').read().replace('/*DATA*/', json.dumps(data, ensure_ascii=False).replace('</', '<\\/'), 1)
open(sys.argv[3], 'w', encoding='utf-8').write(s); print('ok')

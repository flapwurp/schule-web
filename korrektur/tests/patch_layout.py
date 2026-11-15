"""Einmal-Patch (15.11.2026): Layout Schnellmenü, Größe der Handschrift in der Randspalte, kompaktere Werkzeugleiste."""
import sys
P = sys.argv[1]; s = open(P, encoding='utf-8').read()
def sub(old, new, count=1):
    global s
    n = s.count(old); assert n == count, f'{n}x statt {count}: {old[:80]!r}'
    s = s.replace(old, new)

# 1 Knöpfe im Schnellmenü nicht zusammenquetschen, sondern umbrechen
sub(".qpop button{white-space:nowrap;", ".qpop button{flex:0 0 auto;white-space:nowrap;")
sub(".qpop button.qa{background:var(--ok);border-color:var(--ok);color:#fff;flex:1}", ".qpop button.qa{background:var(--ok);border-color:var(--ok);color:#fff;flex:1 0 auto}")
sub(".qpop button.qr{color:var(--red);border-color:#e3b9b9;background:#fff;flex:1}", ".qpop button.qr{color:var(--red);border-color:#e3b9b9;background:#fff;flex:1 0 auto}")

# 2 Position: links vom Korrekturrand, im sichtbaren Bereich
sub("""  let x = s[0] * sc, y = (s[2] + 14) * sc;
  if (x + w > page.clientWidth - 4) x = Math.max(4, page.clientWidth - w - 4);
  if (y + h > page.clientHeight - 4) y = Math.max(4, (s[2] - 44) * sc - h);
  el.style.left = x + 'px'; el.style.top = y + 'px';""",
"""  // waagerecht: links vom Korrekturrand bleiben, damit die Randspalte (dort erscheint das Ergebnis) sichtbar bleibt
  const textR = (P.side === 'L' ? page.clientWidth : P.rt * sc) - 6, textL = P.side === 'L' ? P.lt * sc + 6 : 4;
  let x = Math.max(textL, Math.min(s[0] * sc, textR - w)); if (x + w > page.clientWidth - 4) x = Math.max(4, page.clientWidth - w - 4);
  // senkrecht: unter der Anstreichung; reicht der sichtbare Platz nicht, darüber
  const vr = VW.getBoundingClientRect(), pr = page.getBoundingClientRect(), bar = $('.vbar').getBoundingClientRect().bottom;
  const below = (s[2] + 16) * sc, above = (s[2] - 40) * sc - h;
  let y = below;
  if ((pr.top + below + h > vr.bottom - 8 || below + h > page.clientHeight) && above >= 0 && pr.top + above >= bar) y = above;
  el.style.left = x + 'px'; el.style.top = y + 'px';
  clearTimeout(renderPop.t);
  renderPop.t = setTimeout(() => { if (!el.isConnected) return; const r = el.getBoundingClientRect(), v = VW.getBoundingClientRect(), b = $('.vbar').getBoundingClientRect().bottom;
    if (r.bottom > v.bottom - 8) VW.scrollBy({ top: Math.min(r.bottom - v.bottom + 16, r.top - b - 8), behavior: 'smooth' });
    else if (r.top < b + 4) VW.scrollBy({ top: r.top - b - 12, behavior: 'smooth' }); }, 450);""")

# 3 Handschrift auf Texthöhe normieren (unabhängig von der Schreibgröße in der Fläche)
sub("""const INKH = 42;
function inkBox(k){ let a = 1e9, b = -1e9; k.s.forEach(st => st.forEach(q => { a = Math.min(a, q[0]); b = Math.max(b, q[0]); })); return [a, b]; }
function inkW(k){ const [a, b] = inkBox(k); return (b - a) * INKH / k.h + 4; }
function inkNote(k, x, y){ const a = inkBox(k)[0], sc = INKH / k.h; return k.s.map(st => inkD(st.map(q => [r1(x + 2 + (q[0] - a) * sc), r1(y + (q[1] - k.h * 62 / 90) * sc)]))).join(' '); }""",
"""const INK_TXT = 20, INK_MAXW = 200, inkCache = new WeakMap();
function inkGeo(k){
  let g = inkCache.get(k); if (g) return g;
  let a = 1e9, b = -1e9, c = 1e9, d = -1e9;
  k.s.forEach(st => st.forEach(q => { a = Math.min(a, q[0]); b = Math.max(b, q[0]); c = Math.min(c, q[1]); d = Math.max(d, q[1]); }));
  // Höhe der Handschrift auf etwa Texthöhe bringen; sehr breite Wörter so weit verkleinern, dass sie in die Randspalte passen
  const sc = Math.max(0.2, Math.min(0.7, INK_TXT / Math.max(d - c, 1), INK_MAXW / Math.max(b - a, 1)));
  const line = k.h * 62 / 90, base = (d < line - 8 || c > line) ? d : line;   // Grundlinie: Hilfslinie, sonst Unterkante der Schrift
  g = { a, b, sc, base }; inkCache.set(k, g); return g;
}
function inkW(k){ const g = inkGeo(k); return (g.b - g.a) * g.sc + 4; }
function inkNote(k, x, y){ const g = inkGeo(k); return k.s.map(st => inkD(st.map(q => [r1(x + 2 + (q[0] - g.a) * g.sc), r1(y + (q[1] - g.base) * g.sc)]))).join(' '); }""")
sub("stroke:var(--red);stroke-width:2.2;stroke-linecap:round", "stroke:var(--red);stroke-width:1.8;stroke-linecap:round")
sub("g.save(); g.lineWidth = 2.2; g.setLineDash([]);", "g.save(); g.lineWidth = 1.8; g.setLineDash([]);")

# 4 kompaktere Werkzeugleiste
sub(".vbar{flex-wrap:wrap;row-gap:6px}", ".vbar{flex-wrap:wrap;row-gap:6px;column-gap:12px}\n.vbar input[type=range]{width:90px}")
sub("  .tools button{min-height:40px;padding:6px 12px}", "  .tools button{min-height:38px;padding:4px 10px}")
open(P, 'w', encoding='utf-8').write(s); print('ok', len(s))

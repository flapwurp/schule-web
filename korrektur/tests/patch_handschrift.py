"""Einmal-Patch (15.11.2026): handschriftliche Positivkorrektur im Schnellmenü. Patcht arbeitsflaeche.html in place."""
import sys
P = sys.argv[1]; s = open(P, encoding='utf-8').read()
def sub(old, new, count=1):
    global s
    n = s.count(old); assert n == count, f'{n}x statt {count}: {old[:80]!r}'
    s = s.replace(old, new)

# CSS
sub('.qpop input{margin-top:7px}', '''.qpop input{margin-top:7px}
.qpad{margin-top:7px;border:1px solid var(--line);border-radius:8px;position:relative;
  background:linear-gradient(transparent 61px,#c9d3e3 61px,#c9d3e3 62px,transparent 62px) #fffdf6}
.qpad canvas{display:block;width:100%;height:90px;touch-action:none;cursor:crosshair}
.qpad .qph{position:absolute;left:8px;top:5px;font-size:11.5px;color:var(--muted);pointer-events:none}
.mk path.cink{fill:none;stroke:var(--red);stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round}
.mk.rej path.cink{stroke:var(--grey)}''')

# Zustand / Anzeige
sub("sign:d.sign??s.sign, corr:d.corr??s.corr, muster:d.muster??s.muster, segs, orig:s",
    "sign:d.sign??s.sign, corr:d.corr??s.corr, cink:d.cink||null, muster:d.muster??s.muster, segs, orig:s")
sub("(it.corr ? ' (' + it.corr + ')' : '') + (it.status==='open'", "(it.corr ? ' (' + it.corr + ')' : it.cink ? ' (✎)' : '') + (it.status==='open'")
sub("({ sign:it.sign, corr:it.corr, muster:it.muster })", "({ sign:it.sign, corr:it.corr, muster:it.muster, hand: !!it.cink })")
sub("const changed = it.sign!==it.orig.sign || it.corr!==it.orig.corr || (isI(it)", "const changed = it.sign!==it.orig.sign || it.corr!==it.orig.corr || !!it.cink || (isI(it)")
sub("const changed = it.src==='claude' && (it.sign!==it.orig.sign || it.corr!==it.orig.corr);",
    "const changed = it.src==='claude' && (it.sign!==it.orig.sign || it.corr!==it.orig.corr || !!it.cink);")
sub('''placeholder="z.B. effects  ·  Streichung: -">''',
    '''placeholder="z.B. effects  ·  Streichung: -">${it.cink ? '<div class="note">✎ Positivkorrektur handschriftlich – Tippen ersetzt sie</div>' : ''}''')
sub("$('#corr').oninput = e => edit(it, { corr:e.target.value }, true);", "$('#corr').oninput = e => edit(it, { corr:e.target.value, cink:null }, true);", 2)

# Randspalte: Handschrift als Teil der Notiz („G (“ + Handschrift + „)“)
sub("    const ents = g.map((it, i) => ({ it, num: multi ? String(i+1) : '', txt: label(it) }));",
    "    const hand = it => it.cink && !it.corr ? it.cink : null;\n"
    "    const ents = g.map((it, i) => ({ it, num: multi ? String(i+1) : '', txt: hand(it) ? (it.sign || '?') : label(it), ink: hand(it) }));\n"
    "    const ew = e => e.ink ? tw(e.txt + ' (') + inkW(e.ink) + tw(')') : tw(e.txt);")
sub("s + tw(e.txt) + (e.num?NUMW:0), 0)", "s + ew(e) + (e.num?NUMW:0), 0)")
sub("oneLine = !multi && tw(ents[0].txt) <= avail", "oneLine = !multi && ew(ents[0]) <= avail")
sub("[{ x, y: top + 0.8*LH, txt:e.txt, num:e.num }]; x += tw(e.txt) + (e.num?NUMW:0) + GAP;",
    "[{ x, y: top + 0.8*LH, txt:e.txt, num:e.num, ink:e.ink, w:ew(e) }]; x += ew(e) + (e.num?NUMW:0) + GAP;")
sub("        wrap(e.txt, avail - NUMW).forEach((ln, li) => {\n          const w = tw(ln) + (e.num?NUMW:0),",
    "        (e.ink ? [e.txt] : wrap(e.txt, avail - NUMW)).forEach((ln, li) => {\n          const w = (e.ink ? ew(e) : tw(ln)) + (e.num?NUMW:0),")
sub("txt:ln, num: li===0 ? e.num : '', indent: li>0 && e.num ? NUMW : 0 });",
    "txt:ln, num: li===0 ? e.num : '', indent: li>0 && e.num ? NUMW : 0, ink:e.ink, w: e.ink ? ew(e) : 0 });")
sub("ns.forEach(n => { const w = tw(n.txt) + (n.num?NUMW:0)", "ns.forEach(n => { const w = (n.w || tw(n.txt)) + (n.num?NUMW:0)")
sub('''        g += `<text x="${n.x + (n.num?NUMW:0) + (n.indent||0)}" y="${n.y}">${esc(n.txt)}</text>`;''',
    '''        const tx = n.x + (n.num?NUMW:0) + (n.indent||0), ta = n.ink ? tw(n.txt + ' (') : 0;
        g += n.ink ? `<text x="${tx}" y="${n.y}">${esc(n.txt + ' (')}</text><path class="cink" d="${inkNote(n.ink, tx + ta, n.y)}"/><text x="${tx + ta + inkW(n.ink)}" y="${n.y}">)</text>`
                   : `<text x="${tx}" y="${n.y}">${esc(n.txt)}</text>`;''')
sub("      g.font = FONT; g.fillText(n.txt, n.x + (n.num ? NUMW : 0) + (n.indent || 0), n.y);",
    "      g.font = FONT; const tx = n.x + (n.num ? NUMW : 0) + (n.indent || 0);\n"
    "      if (n.ink){ const ta = tw(n.txt + ' ('); g.fillText(n.txt + ' (', tx, n.y); g.save(); g.lineWidth = 2.2; g.setLineDash([]); g.globalAlpha = 1;\n"
    "        g.stroke(new Path2D(inkNote(n.ink, tx + ta, n.y))); g.restore(); g.fillText(')', tx + ta + inkW(n.ink), n.y); }\n"
    "      else g.fillText(n.txt, tx, n.y);")

# Hilfsfunktionen + Schreibfläche im Schnellmenü
sub("// ---------- Schnellmenü an der Anstreichung (Antippen / Klicken) ----------\nconst popMore = new Set();",
'''// ---------- Handschriftliche Positivkorrektur ----------
// Gespeichert als Vektorstriche in Schreibflächen-Koordinaten { h: Höhe der Fläche, s: [[ [x,y], … ], …] };
// in der Randspalte auf Texthöhe skaliert (Fläche 90 px hoch -> 42 Einheiten, Hilfslinie der Fläche = Grundlinie des Textes).
const INKH = 42;
function inkBox(k){ let a = 1e9, b = -1e9; k.s.forEach(st => st.forEach(q => { a = Math.min(a, q[0]); b = Math.max(b, q[0]); })); return [a, b]; }
function inkW(k){ const [a, b] = inkBox(k); return (b - a) * INKH / k.h + 4; }
function inkNote(k, x, y){ const a = inkBox(k)[0], sc = INKH / k.h; return k.s.map(st => inkD(st.map(q => [r1(x + 2 + (q[0] - a) * sc), r1(y + (q[1] - k.h * 62 / 90) * sc)]))).join(' '); }
let lastPtr = matchMedia('(any-pointer:coarse)').matches ? 'touch' : 'mouse', keepPop = false;
document.addEventListener('pointerdown', e => { lastPtr = e.pointerType || lastPtr; }, true);
const usePad = () => cur.pad != null ? cur.pad : lastPtr !== 'mouse';
function initPad(el, it){
  const cv = el.querySelector('.qpad canvas'); if (!cv) return;
  const dpr = window.devicePixelRatio || 1, W = cv.clientWidth, H = 90, g = cv.getContext('2d');
  cv.width = W * dpr; cv.height = H * dpr; g.scale(dpr, dpr); g.lineWidth = 2.6; g.lineCap = g.lineJoin = 'round'; g.strokeStyle = '#8f1010';
  const strokes = it.cink ? it.cink.s.map(x => x.slice()) : []; let cs_ = null;
  const draw = () => { g.clearRect(0, 0, W, H); strokes.concat(cs_ ? [cs_] : []).forEach(x => g.stroke(new Path2D(inkD(x)))); };
  const pt = e => { const r = cv.getBoundingClientRect(); return [r1(e.clientX - r.left), r1(e.clientY - r.top)]; };
  draw();
  cv.addEventListener('pointerdown', e => { e.preventDefault(); e.stopPropagation(); try { cv.setPointerCapture(e.pointerId); } catch(_){}
    cs_ = [pt(e)]; const ph = el.querySelector('.qph'); if (ph) ph.remove(); draw(); });
  cv.addEventListener('pointermove', e => { if (!cs_) return; e.preventDefault();
    const ce = e.getCoalescedEvents ? e.getCoalescedEvents() : []; (ce.length ? ce : [e]).forEach(ev => cs_.push(pt(ev))); draw(); });
  const up = () => { if (!cs_) return; strokes.push(cs_); cs_ = null;
    keepPop = true; try { edit(it, { cink: { h: H, s: strokes }, corr: '' }, true); } finally { keepPop = false; } };
  cv.addEventListener('pointerup', up); cv.addEventListener('pointercancel', up);
  cv.addEventListener('touchstart', e => e.preventDefault(), { passive: false });
}

// ---------- Schnellmenü an der Anstreichung (Antippen / Klicken) ----------
const popMore = new Set();''')
sub("function renderPop(){\n", "function renderPop(){\n  if (keepPop) return;\n")
sub('''         <input type="text" class="qcorr" value="${esc(it.corr||'')}" placeholder="Positivkorrektur (optional) · Streichung: -">
         <div class="qrow"><button data-q="gap" class="${isGap(it)?'on':''}">Lücke</button>''',
'''         ${usePad() ? `<div class="qpad"><canvas></canvas>${it.cink ? '' : '<span class="qph">Positivkorrektur hier schreiben (optional)</span>'}</div>`
                    : `<input type="text" class="qcorr" value="${esc(it.corr||'')}" placeholder="Positivkorrektur (optional) · Streichung: -">`}
         <div class="qrow"><button data-q="gap" class="${isGap(it)?'on':''}">Lücke</button>${usePad()
           ? `<button data-q="clr">Leeren</button><button data-q="kbd" title="Positivkorrektur tippen">⌨</button>`
           : `<button data-q="pen" title="Positivkorrektur mit Stift oder Maus schreiben">✎</button>`}''')
sub("    else if (q === 'gap') setGap(it, !isGap(it));",
    "    else if (q === 'gap') setGap(it, !isGap(it));\n"
    "    else if (q === 'clr') edit(it, { cink: null });\n"
    "    else if (q === 'kbd' || q === 'pen'){ cur.pad = q === 'pen'; el.remove(); renderPop(); const i2 = document.querySelector('.qpop .qcorr'); if (i2) i2.focus(); }")
sub("inp.oninput = () => edit(it, { corr: inp.value }, true);", "inp.oninput = () => edit(it, { corr: inp.value, cink: null }, true);")
sub("  const inp = el.querySelector('.qcorr');\n", "  initPad(el, it);\n  const inp = el.querySelector('.qcorr');\n")
open(P, 'w', encoding='utf-8').write(s); print('ok', len(s))

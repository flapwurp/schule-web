// ===================== AIS-Vorbereitung =====================
// Scan einlesen (PDF/JPG/PNG) -> Seiten ausrichten (Ankerpunkte), per QR zuordnen, Wortfelder finden
// -> Halbseiten-Bilder für AIS.chat -> Antworten (Abschrift, Fehlerliste) einfügen -> Vorschläge -> Arbeitsfläche.
// Alles läuft lokal im Browser. Portiert aus werkzeuge/kw.py (einlesen, words, ausrichten, vorschlaege, build).
'use strict';
const P = (() => {
const MM = 150 / 25.4, PW_ = Math.floor(210 * MM), PH_ = Math.floor(297 * MM);
const CANON = [[11, 11], [199, 11], [11, 286], [199, 286]];          // Mittelpunkte der Ankerpunkte (mm)
const lineY = k => (52 + 10 * (k - 1)) * MM, X_TEXT0 = 19.5 * MM, X_MARGIN = 157.5 * MM;
const GEO = () => ({ w: PW_, h: PH_, lines: [Math.round(42 * MM)].concat(Array.from({ length: 23 }, (_, i) => Math.round(lineY(i + 1)))),
  side: 'R', lt: Math.round(X_TEXT0), rt: Math.round(X_MARGIN - 10) });
const SIGNS = new Set(['W', 'A', 'G', 'Sb', 'St', 'R', 'Z', 'Präp', 'Wdh', 'Г']);
const MUSTERSET = new Set('KOM SVA TEMP VERB ADV ART KOMP ST PRAEP FF WW VW REG RS SB REL WF'.split(' '));
// Modell schreibt manchmal das Fehlermuster in die Zeichen-Spalte: passendes Zeichen ableiten
const SIGN_OF = { KOM: 'Z', SB: 'Z', SVA: 'G', TEMP: 'G', VERB: 'G', ADV: 'G', ART: 'G', KOMP: 'G', WF: 'G', REL: 'G', ST: 'St', PRAEP: 'Präp', 'PRÄP': 'Präp', FF: 'W', WW: 'W', VW: 'R', RS: 'R', REG: 'A' };
const CONF = { s: 'sicher', e: 'ermessen', u: 'unsicher' };
const UPLOAD_DPI = 300, MAXIMG = 5;
const HALF = [{ z0: 1, z1: 12, y0: 41, y1: 162.5 }, { z0: 13, z1: 23, y0: 163, y1: 275 }];   // mm
const X0MM = 9, X1MM = 201;

// ---------------------------------------------------------------- PDF: Seitenbilder lesen
const latin1 = b => { let s = ''; for (let i = 0; i < b.length; i += 65536) s += String.fromCharCode.apply(null, b.subarray(i, i + 65536)); return s; };
function pdfParser(bytes){
  const S = latin1(bytes); let i = 0;
  const ws = () => { for (;;){ while (i < S.length && /[\s\0]/.test(S[i])) i++; if (S[i] === '%'){ while (i < S.length && S[i] !== '\n' && S[i] !== '\r') i++; } else break; } };
  function val(){
    ws(); if (i >= S.length) throw new Error('Ende'); const c = S[i];
    if (c === '<' && S[i + 1] === '<'){ i += 2; const d = {}; for (;;){ ws(); if (S[i] === '>' && S[i + 1] === '>'){ i += 2; return d; } const k = val(); d[k.n] = val(); } }
    if (c === '<'){ const j = S.indexOf('>', i); const h = S.slice(i + 1, j); i = j + 1; return { hex: h }; }
    if (c === '['){ i++; const a = []; for (;;){ ws(); if (S[i] === ']'){ i++; return a; } a.push(val()); } }
    if (c === '('){ let d = 0, j = i; for (; j < S.length; j++){ if (S[j] === '\\'){ j++; continue; } if (S[j] === '(') d++; else if (S[j] === ')' && --d === 0) break; } const s = S.slice(i + 1, j); i = j + 1; return { str: s }; }
    if (c === '/'){ let j = i + 1; while (j < S.length && !/[\s\/\[\]<>()%{}]/.test(S[j])) j++; const n = S.slice(i + 1, j).replace(/#([0-9a-fA-F]{2})/g, (_, h) => String.fromCharCode(parseInt(h, 16))); i = j; return { n }; }
    let j = i; while (j < S.length && !/[\s\/\[\]<>()%{}]/.test(S[j])) j++;
    if (j === i) throw new Error('Syntax'); const t = S.slice(i, j); i = j;
    if (/^[+-]?(\d+\.?\d*|\.\d+)$/.test(t)){
      const save = i; const m = /^\s+(\d+)\s+R(?![A-Za-z])/.exec(S.slice(i, i + 24));
      if (m && /^\d+$/.test(t)){ i += m[0].length; return { ref: +t }; }
      i = save; return +t;
    }
    return { kw: t };
  }
  const skipWs = k => { while (k < S.length && /[\s]/.test(S[k])) k++; return k; };
  const objs = {};
  const re = /(\d+)\s+(\d+)\s+obj\b/g; let m;
  while ((m = re.exec(S))){
    i = m.index + m[0].length;
    try {
      const v = val(); ws(); const o = { v };
      if (S.startsWith('stream', i)){ i += 6; if (S[i] === '\r') i++; if (S[i] === '\n') i++; o.s = i;
        const L = typeof o.v.Length === 'number' ? o.v.Length : -1, e = L >= 0 && S.startsWith('endstream', skipWs(i + L)) ? i + L : S.indexOf('endstream', i);
        o.e = e < 0 ? S.length : e; i = o.e; }
      objs[+m[1]] = o; re.lastIndex = Math.max(re.lastIndex, i);
    } catch(e){ /* defektes Objekt überspringen */ }
  }
  const get = x => (x && x.ref !== undefined) ? (objs[x.ref] ? objs[x.ref].v : null) : x;
  function raw(o){
    let len = get(o.v.Length);
    if (typeof len !== 'number') len = (o.e !== undefined ? o.e : S.indexOf('endstream', o.s)) - o.s;
    return bytes.subarray(o.s, o.s + len);
  }
  return { objs, get, raw, S, setPos: p => { i = p; }, val: () => val(), ws: () => ws(), pos: () => i };
}
async function inflate(b){
  for (const fmt of ['deflate', 'deflate-raw']){
    try { const ds = new DecompressionStream(fmt); const r = new Response(new Blob([b]).stream().pipeThrough(ds)); return new Uint8Array(await r.arrayBuffer()); } catch(e){}
  }
  throw new Error('Datenstrom nicht entpackbar');
}
function a85(b){
  const out = []; let t = [], s = latin1(b).replace(/\s/g, ''); if (s.startsWith('<~')) s = s.slice(2);
  const end = s.indexOf('~>'); if (end >= 0) s = s.slice(0, end);
  for (let k = 0; k < s.length; k++){
    if (s[k] === 'z' && !t.length){ out.push(0, 0, 0, 0); continue; }
    t.push(s.charCodeAt(k) - 33);
    if (t.length === 5){ let n = 0; for (const d of t) n = n * 85 + d; out.push(n >>> 24 & 255, n >>> 16 & 255, n >>> 8 & 255, n & 255); t = []; }
  }
  if (t.length){ const c = t.length; while (t.length < 5) t.push(84); let n = 0; for (const d of t) n = n * 85 + d; [n >>> 24 & 255, n >>> 16 & 255, n >>> 8 & 255, n & 255].slice(0, c - 1).forEach(x => out.push(x)); }
  return new Uint8Array(out);
}
function unpredict(d, cols, colors, bpc, pred){
  if (!pred || pred < 10) return d;
  const bpp = Math.max(1, Math.ceil(colors * bpc / 8)), rowLen = Math.ceil(cols * colors * bpc / 8), rows = Math.floor(d.length / (rowLen + 1));
  const out = new Uint8Array(rows * rowLen); let prev = new Uint8Array(rowLen);
  for (let r = 0; r < rows; r++){
    const f = d[r * (rowLen + 1)], src = d.subarray(r * (rowLen + 1) + 1, (r + 1) * (rowLen + 1)), cur = out.subarray(r * rowLen, (r + 1) * rowLen);
    for (let x = 0; x < rowLen; x++){
      const a = x >= bpp ? cur[x - bpp] : 0, b = prev[x], c = x >= bpp ? prev[x - bpp] : 0; let v = src[x];
      if (f === 1) v += a; else if (f === 2) v += b; else if (f === 3) v += (a + b) >> 1;
      else if (f === 4){ const p = a + b - c, pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c); v += (pa <= pb && pa <= pc) ? a : (pb <= pc ? b : c); }
      cur[x] = v & 255;
    }
    prev = cur;
  }
  return out;
}
async function pdfPageImages(bytes){
  const p = pdfParser(bytes), { objs, get } = p;
  // Objektströme (PDF 1.5+) entpacken
  for (const o of Object.values(objs)){
    if (!o.v || get(o.v.Type)?.n !== 'ObjStm' || o.s === undefined) continue;
    try {
      const d = await inflate(p.raw(o)), s = latin1(d), N = get(o.v.N), first = get(o.v.First);
      const hdr = s.slice(0, first).trim().split(/\s+/).map(Number);
      const sub = pdfParser(d);
      for (let k = 0; k < N; k++){ const num = hdr[2 * k], off = hdr[2 * k + 1]; if (objs[num]) continue; sub.setPos(first + off); try { objs[num] = { v: sub.val() }; } catch(e){} }
    } catch(e){}
  }
  const cat = Object.values(objs).find(o => o.v && get(o.v.Type)?.n === 'Catalog');
  if (!cat) throw new Error('PDF-Aufbau nicht lesbar.');
  const pages = [];
  (function walk(node, inh){
    node = get(node); if (!node) return;
    const res = node.Resources !== undefined ? node.Resources : inh;
    if (get(node.Type)?.n === 'Pages' || node.Kids) (get(node.Kids) || []).forEach(k => walk(k, res));
    else pages.push({ node, res, rot: get(node.Rotate) || 0 });
  })(get(cat.v).Pages, null);
  const out = [];
  for (const pg of pages){
    const imgs = [];
    (function collect(res, depth){
      res = get(res); if (!res || depth > 4) return; const xo = get(res.XObject); if (!xo) return;
      for (const k in xo){ const ref = xo[k], o = ref && ref.ref !== undefined ? objs[ref.ref] : null; if (!o) continue;
        const st = get(o.v.Subtype)?.n; if (st === 'Image') imgs.push(o); else if (st === 'Form') collect(o.v.Resources, depth + 1); }
    })(pg.res, 0);
    if (!imgs.length){ out.push({ err: 'kein Bild auf der Seite' }); continue; }
    imgs.sort((a, b) => get(b.v.Width) * get(b.v.Height) - get(a.v.Width) * get(a.v.Height));
    try { out.push({ bmp: await decodeImage(p, imgs[0]), rot: pg.rot }); } catch(e){ out.push({ err: e.message }); }
  }
  return out;
}
async function decodeImage(p, o){
  const { get } = p, d = o.v; let data = p.raw(o);
  let filters = get(d.Filter); filters = filters ? (Array.isArray(filters) ? filters.map(f => get(f).n) : [filters.n]) : [];
  let parms = get(d.DecodeParms); parms = Array.isArray(parms) ? parms.map(get) : [parms];
  const w = get(d.Width), h = get(d.Height), bpc = get(d.BitsPerComponent) || 8;
  for (let k = 0; k < filters.length; k++){
    const f = filters[k], pr = get(parms[k]) || {};
    if (f === 'ASCII85Decode' || f === 'A85') data = a85(data);
    else if (f === 'ASCIIHexDecode' || f === 'AHx'){ const s = latin1(data).replace(/[^0-9a-fA-F]/g, ''); const u = new Uint8Array(s.length >> 1); for (let j = 0; j < u.length; j++) u[j] = parseInt(s.substr(2 * j, 2), 16); data = u; }
    else if (f === 'FlateDecode' || f === 'Fl'){ data = await inflate(data); const cs0 = csInfo(p, d.ColorSpace); data = unpredict(data, get(pr.Columns) || w, get(pr.Colors) || cs0.n, get(pr.BitsPerComponent) || bpc, get(pr.Predictor)); }
    else if (f === 'DCTDecode' || f === 'DCT'){ return await createImageBitmap(new Blob([data], { type: 'image/jpeg' })); }
    else throw new Error(`Bildformat ${f} wird nicht unterstützt – bitte in Graustufen oder Farbe scannen (JPEG).`);
  }
  const cs = csInfo(p, d.ColorSpace), img = new ImageData(w, h), px = img.data;
  const rowLen = Math.ceil(w * cs.n * bpc / 8);
  const decode = get(d.Decode), inv = Array.isArray(decode) && decode[0] === 1;
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++){
    const q = (y * w + x) * 4; let r, g, b;
    if (bpc === 1){ const bit = (data[y * rowLen + (x >> 3)] >> (7 - (x & 7))) & 1; r = g = b = (bit ^ (inv ? 1 : 0)) ? 255 : 0; }
    else if (cs.n === 1){ r = g = b = data[y * rowLen + x]; }
    else if (cs.n === 3){ const o3 = y * rowLen + 3 * x; r = data[o3]; g = data[o3 + 1]; b = data[o3 + 2]; }
    else throw new Error('Farbraum wird nicht unterstützt.');
    px[q] = r; px[q + 1] = g; px[q + 2] = b; px[q + 3] = 255;
  }
  return await createImageBitmap(img);
}
function csInfo(p, cs){
  cs = p.get(cs);
  if (!cs) return { n: 1 };
  if (cs.n) return { n: cs.n === 'DeviceRGB' || cs.n === 'CalRGB' ? 3 : cs.n === 'DeviceCMYK' ? 4 : 1 };
  if (Array.isArray(cs)){ const t = p.get(cs[0]).n; if (t === 'ICCBased'){ const o = p.objs[cs[1].ref]; return { n: p.get(o.v.N) || 3 }; } if (t === 'CalRGB') return { n: 3 }; if (t === 'CalGray') return { n: 1 }; }
  throw new Error('Farbraum wird nicht unterstützt.');
}

// ---------------------------------------------------------------- Geometrie
function solve(A, b){                                             // Gauß-Elimination
  const n = b.length; A = A.map((r, i) => r.concat([b[i]]));
  for (let c = 0; c < n; c++){
    let piv = c; for (let r = c + 1; r < n; r++) if (Math.abs(A[r][c]) > Math.abs(A[piv][c])) piv = r;
    [A[c], A[piv]] = [A[piv], A[c]];
    for (let r = 0; r < n; r++){ if (r === c) continue; const f = A[r][c] / A[c][c]; for (let k = c; k <= n; k++) A[r][k] -= f * A[c][k]; }
  }
  return A.map((r, i) => r[n] / r[i]);
}
function homography(src, dst){                                    // src -> dst, je 4 Punkte
  const A = [], b = [];
  for (let k = 0; k < 4; k++){ const [x, y] = src[k], [u, v] = dst[k];
    A.push([x, y, 1, 0, 0, 0, -u * x, -u * y]); b.push(u); A.push([0, 0, 0, x, y, 1, -v * x, -v * y]); b.push(v); }
  const h = solve(A, b); return [...h, 1];
}
const apply = (H, x, y) => { const w = H[6] * x + H[7] * y + H[8]; return [(H[0] * x + H[1] * y + H[2]) / w, (H[3] * x + H[4] * y + H[5]) / w]; };
// Ausschnitt in mm-Koordinaten der Vorlage mit dpi aus dem Scanbild (ImageData) entzerrt herausrechnen
function warp(src, H, x0, y0, x1, y1, dpi){
  const ppm = dpi / 25.4, W = Math.round((x1 - x0) * ppm), Ht = Math.round((y1 - y0) * ppm);
  const out = new ImageData(W, Ht), o = out.data, s = src.data, sw = src.width, sh = src.height;
  for (let v = 0; v < Ht; v++){
    const my = y0 + (v + 0.5) / ppm;
    for (let u = 0; u < W; u++){
      const mx = x0 + (u + 0.5) / ppm, w = H[6] * mx + H[7] * my + H[8];
      const X = (H[0] * mx + H[1] * my + H[2]) / w - 0.5, Y = (H[3] * mx + H[4] * my + H[5]) / w - 0.5;
      const q = (v * W + u) * 4;
      const xi = Math.floor(X), yi = Math.floor(Y), fx = X - xi, fy = Y - yi;
      if (xi < 0 || yi < 0 || xi + 1 >= sw || yi + 1 >= sh){ o[q] = o[q + 1] = o[q + 2] = 255; o[q + 3] = 255; continue; }
      const a = (yi * sw + xi) * 4, b = a + 4, c = a + sw * 4, d = c + 4;
      for (let ch = 0; ch < 3; ch++)
        o[q + ch] = (s[a + ch] * (1 - fx) + s[b + ch] * fx) * (1 - fy) + (s[c + ch] * (1 - fx) + s[d + ch] * fx) * fy;
      o[q + 3] = 255;
    }
  }
  return out;
}
function grayOf(img){ const g = new Uint8Array(img.width * img.height), d = img.data; for (let i = 0; i < g.length; i++) g[i] = (0.299 * d[4 * i] + 0.587 * d[4 * i + 1] + 0.114 * d[4 * i + 2]) | 0; return g; }
function otsu(g){
  const h = new Float64Array(256); for (const v of g) h[v]++;
  let sum = 0; for (let t = 0; t < 256; t++) sum += t * h[t];
  let wB = 0, sB = 0, best = 0, th = 127;
  for (let t = 0; t < 256; t++){ wB += h[t]; if (!wB) continue; const wF = g.length - wB; if (!wF) break; sB += t * h[t];
    const mB = sB / wB, mF = (sum - sB) / wF, v = wB * wF * (mB - mF) ** 2; if (v > best){ best = v; th = t; } }
  return th;
}
// Ankerpunkte: 4 gefüllte Quadrate (6 mm) nahe den Bildecken. Arbeitet auf einer verkleinerten Kopie (~150 dpi).
function findAnchors(bmp){
  const sc = Math.min(1, PW_ / Math.min(bmp.width, bmp.height) * (bmp.width > bmp.height ? 1 : 1)), w = Math.round(bmp.width * sc), h = Math.round(bmp.height * sc);
  const cv = new OffscreenCanvas(w, h), g0 = cv.getContext('2d'); g0.drawImage(bmp, 0, 0, w, h);
  const g = grayOf(g0.getImageData(0, 0, w, h)), th = otsu(g);
  const lab = new Int32Array(w * h), par = [0];
  const find = x => { while (par[x] !== x){ par[x] = par[par[x]]; x = par[x]; } return x; };
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++){
    const i = y * w + x; if (g[i] > th) continue;
    const l = x > 0 ? lab[i - 1] : 0, u = y > 0 ? lab[i - w] : 0;
    if (!l && !u){ lab[i] = par.length; par.push(par.length); }
    else if (l && u){ const a = find(l), b = find(u); lab[i] = Math.min(a, b); par[Math.max(a, b)] = Math.min(a, b); }
    else lab[i] = l || u;
  }
  const st = new Map();
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++){
    const i = y * w + x; if (!lab[i]) continue; const r = find(lab[i]);
    let s = st.get(r); if (!s){ s = { n: 0, x0: x, x1: x, y0: y, y1: y, sx: 0, sy: 0 }; st.set(r, s); }
    s.n++; s.sx += x; s.sy += y; if (x < s.x0) s.x0 = x; if (x > s.x1) s.x1 = x; if (y < s.y0) s.y0 = y; if (y > s.y1) s.y1 = y;
  }
  const pxmm = Math.max(w, h) / 297, exp = (6 * pxmm) ** 2, c = [];
  for (const s of st.values()){
    const bw = s.x1 - s.x0 + 1, bh = s.y1 - s.y0 + 1;
    if (s.n > 0.5 * exp && s.n < 1.6 * exp && bw / bh > 0.7 && bw / bh < 1.4 && s.n / (bw * bh) > 0.75) c.push([s.sx / s.n / sc, s.sy / s.n / sc]);
  }
  if (c.length < 4) return null;
  const W = bmp.width, Hh = bmp.height;
  return [[0, 0], [W, 0], [0, Hh], [W, Hh]].map(([cx, cy]) => c.reduce((b, p) => Math.hypot(p[0] - cx, p[1] - cy) < Math.hypot(b[0] - cx, b[1] - cy) ? p : b));
}
function qrRead(src, H){
  for (const dpi of [300, 400, 220]){
    const im = warp(src, H, 158, 4, 200, 46, dpi);
    const r = jsQR(im.data, im.width, im.height, { inversionAttempts: 'dontInvert' });
    if (r && r.data) return r.data;
  }
  return '';
}
const ORDERS = [[0, 1, 2, 3], [3, 2, 1, 0], [2, 0, 3, 1], [1, 3, 0, 2]];   // aufrecht, 180°, 90°, 270°

// ---------------------------------------------------------------- Wortfelder (kw.words)
function words(gray){
  const W = PW_, Hh = PH_, ink = new Uint8Array(W * Hh);
  for (let y = 0; y < Hh; y++) for (let x = 0; x < W; x++){
    let v = gray[y * W + x] < 150 ? 1 : 0;
    if (x < Math.floor(X_TEXT0) || x >= Math.floor(196 * MM)) v = 0;
    if (y < Math.floor(50 * MM) && x >= Math.floor(X_MARGIN)) v = 0;
    ink[y * W + x] = v;
  }
  const er = new Uint8Array(W * Hh), op = new Uint8Array(W * Hh);
  for (let y = 1; y < Hh; y++) for (let x = 1; x < W; x++){ const i = y * W + x; er[i] = ink[i] & ink[i - 1] & ink[i - W] & ink[i - W - 1]; }
  for (let y = 0; y < Hh - 1; y++) for (let x = 0; x < W - 1; x++){ const i = y * W + x; op[i] = er[i] | er[i + 1] | er[i + W] | er[i + W + 1]; }
  const out = {};
  for (let k = 1; k <= 23; k++){
    const y0 = Math.floor(lineY(k) - 8.5 * MM), y1 = Math.floor(lineY(k) + 2.2 * MM);
    const col = new Uint8Array(W), colSum = new Int32Array(W);
    for (let y = y0; y < y1; y++) for (let x = 0; x < W; x++){ const v = op[y * W + x]; if (v){ col[x] = 1; colSum[x]++; } }
    const segs = []; let x = 0;
    while (x < W){ if (col[x]){ const s = x; while (x < W && col[x]) x++; segs.push([s, x]); } else x++; }
    const merged = [];
    for (const s of segs){ if (merged.length && s[0] - merged[merged.length - 1][1] < 9) merged[merged.length - 1][1] = s[1]; else merged.push(s.slice()); }
    const keep = merged.filter(m => { let n = 0; for (let x2 = m[0]; x2 < m[1]; x2++) n += colSum[x2]; return n > 20; });
    if (keep.length) out[k] = keep;
  }
  return out;
}
function percentile(arr, q){
  const a = Float64Array.from(arr).sort(), idx = q * (a.length - 1), lo = Math.floor(idx), hi = Math.ceil(idx);
  return a[lo] + (a[hi] - a[lo]) * (idx - lo);
}
function lineProfile(gray, L, z){
  const W = PW_, y0 = Math.floor(L[z - 1]) + 6, y1 = Math.floor(L[z]) - 2, vals = [];
  for (let y = y0; y < y1; y++) for (let x = 0; x < W; x++) vals.push(gray[y * W + x]);
  const th = percentile(vals, 0.75) - 60, prof = new Int32Array(W);
  for (let y = y0; y < y1; y++) for (let x = 0; x < W; x++) if (gray[y * W + x] < th) prof[x]++;
  return prof;
}
// ---------------------------------------------------------------- Ausrichten (kw._align_core / _align_line)
function alignCore(F, toks, prof){
  F = F.map(f => f.slice()); const n = toks.length;
  while (F.length > n && F.length > 1){
    const L = F.length;
    if (F[L - 1][1] - F[L - 1][0] < 22 && F[L - 1][0] - F[L - 2][1] > 40){ F.pop(); continue; }
    if (F[0][1] - F[0][0] < 22 && F[1][0] - F[0][1] > 40){ F.shift(); continue; }
    break;
  }
  if (n === 0 || !F.length || (F.length === n && !prof)) return [0, F];
  const wOf = t => { t = t.replace(/~/g, '').replace(/\[\?\]/g, ''); let s = 0; for (const ch of t) s += /[\p{L}\p{N}]/u.test(ch) ? 1 : 0.9; return Math.max(1, s) + 0.8; };
  const wts = toks.map(wOf), X0 = F[0][0], X1 = F[F.length - 1][1], cw = (X1 - X0) / wts.reduce((a, b) => a + b, 0), exp = wts.map(w => w * cw);
  const atoms = [];
  F.forEach(([a0, a1], j) => {
    let parts = [[a0, a1, j > 0 ? ['gap', F[j][0] - F[j - 1][1]] : ['start', 0]]];
    if (prof && a1 - a0 > 1.2 * cw){
      const p = prof.subarray(a0, a1), runs = []; let x = 0;
      while (x < p.length){ if (p[x] <= 0){ const s0 = x; while (x < p.length && p[x] <= 0) x++; if (s0 > 2 && x < p.length - 2 && x - s0 >= 2) runs.push([s0, x]); } else x++; }
      if (runs.length){
        const pts = []; let cur = a0;
        for (const [r0, r1] of runs){ pts.push([cur, a0 + r0]); cur = a0 + r1; }
        pts.push([cur, a1]);
        parts = [[pts[0][0], pts[0][1], parts[0][2]]].concat(pts.slice(1).map(([q0, q1], k) => [q0, q1, ['gap', q0 - pts[k][1]]]));
      }
    }
    for (const [q0, q1, kind] of parts){
      let cuts = [];
      if (prof && q1 - q0 > 1.6 * cw){
        const L = q1 - q0, pr = new Float64Array(L);
        for (let x = 0; x < L; x++){ let s = 0; for (let d = -2; d <= 2; d++){ const xx = x + d; if (xx >= 0 && xx < L) s += prof[q0 + xx]; } pr[x] = s / 5; }
        const th = percentile(pr, 0.30);
        for (let x = 5; x < L - 5; x++){
          let mn = Infinity; for (let d = -4; d <= 4; d++) mn = Math.min(mn, pr[x + d]);
          if (pr[x] <= mn && pr[x] <= th){ if (!cuts.length || x - cuts[cuts.length - 1] > 0.7 * cw) cuts.push(x); }
        }
      }
      if (!cuts.length && q1 - q0 > 2.5 * cw && !prof){ for (let c = Math.floor(cw); c < q1 - q0 - Math.floor(cw / 2); c += Math.max(4, Math.floor(cw * 0.7))) cuts.push(c); }
      const pp = [q0, ...cuts.map(c => q0 + c), q1];
      for (let k = 0; k < pp.length - 1; k++) atoms.push([pp[k], pp[k + 1], k === 0 ? kind : ['cut', 0]]);
    }
  });
  const A = atoms.length, INF = Infinity;
  const bcost = i => atoms[i][2][0] === 'gap' ? -0.8 * Math.min(atoms[i][2][1] / cw, 2.5) : 1.2;
  const pre = new Float64Array(A + 1);
  for (let i = 0; i < A; i++) pre[i + 1] = pre[i] + (atoms[i][2][0] === 'gap' ? 0.9 * Math.min(atoms[i][2][1] / cw, 3) : 0);
  const dp = Array.from({ length: n + 1 }, () => new Float64Array(A + 1).fill(INF)), bk = Array.from({ length: n + 1 }, () => new Int32Array(A + 1));
  dp[0][0] = 0;
  for (let t = 1; t <= n; t++) for (let e = t; e <= A - (n - t); e++) for (let s_ = t - 1; s_ < e; s_++){
    const c0 = dp[t - 1][s_]; if (c0 === INF) continue;
    const w = atoms[e - 1][1] - atoms[s_][0];
    const c = c0 + Math.abs(w - exp[t - 1]) / cw + (pre[e] - pre[s_ + 1]) + (t > 1 ? bcost(s_) : 0);
    if (c < dp[t][e]){ dp[t][e] = c; bk[t][e] = s_; }
  }
  if (dp[n][A] === INF) return [INF, F];
  const out = []; let e = A;
  for (let t = n; t > 0; t--){ const s_ = bk[t][e]; out.push([Math.trunc(atoms[s_][0]), Math.trunc(atoms[e - 1][1])]); e = s_; }
  return [dp[n][A], out.reverse()];
}
function alignLine(F, toks, prof){
  if (!F.length || !toks.length) return F;
  F = F.map(f => f.slice());
  if (!prof && F.length === toks.length) return F;
  let best = null; const small = (f, nb) => f[1] - f[0] < 45 && Math.abs(nb) > 18, L = F.length;
  for (let dl = 0; dl < 2; dl++) for (let dr = 0; dr < 3; dr++){
    if (dl + dr >= L) continue;
    let ok = true;
    for (let i = 0; i < dl; i++) if (!small(F[i], F[i + 1][0] - F[i][1])) ok = false;
    for (let i = 0; i < dr; i++) if (!small(F[L - 1 - i], F[L - 1 - i][0] - F[L - 2 - i][1])) ok = false;
    if (!ok) continue;
    const G = F.slice(dl, L - dr); if (!G.length) continue;
    let [c, out] = alignCore(G, toks, prof); c += 1.8 * (dl + dr);
    if (!best || c < best[0]) best = [c, out];
  }
  return best ? best[1] : F;
}
// Notlösung, wenn Wortfelder und Wörter nicht zusammenpassen: Zeile nach Wortlänge aufteilen
function splitEven(F, toks){
  if (!F.length) return [];
  const X0 = F[0][0], X1 = F[F.length - 1][1], w = toks.map(t => Math.max(1, t.length) + 1), tot = w.reduce((a, b) => a + b, 0);
  let x = X0; return w.map(v => { const a = x; x += (X1 - X0) * v / tot; return [Math.round(a), Math.round(x - 4)]; });
}

// ---------------------------------------------------------------- Antworten von AIS.chat lesen (ais_import.py)
const RAND = '.,;:!?"\'()[]“”‘’';
const strip = w => { let a = 0, b = w.length; while (a < b && RAND.includes(w[a])) a++; while (b > a && RAND.includes(w[b - 1])) b--; return w.slice(a, b); };
function findWords(toks, phrase){
  let occ = 1; const m = /^(.*?)\s*#(\d+)$/.exec(phrase); if (m){ phrase = m[1]; occ = +m[2]; }
  const p = phrase.split(/\s+/).filter(Boolean);
  for (const norm of [x => x, strip]){
    const t = toks.map(norm), q = p.map(norm); if (!q.length || q.some(x => !x) && norm === strip) continue;
    const hits = []; for (let i = 0; i + q.length <= t.length; i++) if (q.every((w, k) => t[i + k] === w)) hits.push(i);
    if (hits.length >= occ) return [hits[occ - 1] + 1, hits[occ - 1] + q.length];
  }
  return null;
}
function parseAnswers(txt){
  const blocks = {}; let code = null, sec = null;
  const B = c => blocks[c] || (blocks[c] = { text: {}, err: [], hint: [], probs: [] });
  txt = txt.replace(/([^\n])[ \t]*(###)/g, '$1\n$2');                       // „### WEITER### CODE 58“ trennen
  txt.split(/\r?\n/).forEach((raw, n) => {
    const line = raw.trim().replace(/^`+|`+$/g, '').replace(/^\*\*|\*\*$/g, '').trim(); if (!line) return;
    if (/^#+\s*WEITER/i.test(line) || /^Erhalten:/i.test(line)) return;
    let m = /^#+\s*CODE\s+(\S+)/i.exec(line); if (m){ code = m[1].replace(/[*:]/g, ''); sec = null; B(code); return; }
    m = /^#+\s*(TEXT|FEHLER|HINWEISE)/i.exec(line); if (m){ sec = m[1].toUpperCase(); return; }
    if (!code) return; const b = B(code);
    if (sec === 'TEXT'){
      m = /^B(\d+)\s*Z(\d+)\s*:\s?(.*)$/.exec(line);
      if (!m){ b.probs.push(`TEXT-Zeile nicht erkannt: ${line.slice(0, 60)}`); return; }
      (b.text[m[1]] || (b.text[m[1]] = {}))[String(+m[2])] = m[3].trim();
    } else if (sec === 'FEHLER'){
      const p = line.split('|').map(x => x.trim()); m = p.length ? /^B(\d+)\s*Z(\d+)$/.exec(p[0]) : null;
      if (!m || p.length < 6){ b.probs.push(`Fehlerzeile nicht erkannt: ${line.slice(0, 70)}`); return; }
      b.err.push({ b: +m[1], z: +m[2], w: p[1], sign: p[2], c: p[3], m: p[4].toUpperCase(), conf: (p[5] || 'e').toLowerCase()[0], gap: p.length > 6 && /^l/i.test(p[6]) });
    } else if (sec === 'HINWEISE'){ if (!/^keine\.?$/i.test(line)) b.hint.push(line); }
  });
  return blocks;
}

// ---------------------------------------------------------------- Zustand der Vorbereitung
const st = { pages: [], codes: {}, probs: [], kid: '', meta: null, textA: '', textB: '', file: '', skipLese: true, mode: 's16' };
const key = () => 'ais-prep:' + (st.kid || 'ohne-id');
function saveTexts(){ try { localStorage.setItem(key(), JSON.stringify({ a: st.textA, b: st.textB, t: Date.now() })); } catch(e){} }
function loadTexts(){ try { const o = JSON.parse(localStorage.getItem(key()) || 'null'); if (o){ st.textA = o.a || ''; st.textB = o.b || ''; } } catch(e){} }

async function readScan(files, progress){
  st.pages = []; st.codes = {}; st.probs = [];
  const srcs = [];
  for (const f of files){
    if (/\.pdf$/i.test(f.name)){
      const imgs = await pdfPageImages(new Uint8Array(await f.arrayBuffer()));
      imgs.forEach((x, i) => srcs.push({ name: `${f.name} S. ${i + 1}`, ...x }));
    } else if (/\.(jpe?g|png)$/i.test(f.name)) srcs.push({ name: f.name, bmp: await createImageBitmap(f) });
  }
  if (!srcs.length) throw new Error('Keine Scan-Seiten gefunden (PDF, JPG oder PNG).');
  for (let i = 0; i < srcs.length; i++){
    progress(`Scan-Seite ${i + 1} von ${srcs.length} …`); await new Promise(r => setTimeout(r, 0));
    const s = srcs[i]; if (s.err){ st.probs.push(`${s.name}: ${s.err}`); continue; }
    const res = await processPage(s.bmp);
    if (!res.ok){ st.probs.push(`${s.name}: ${res.msg}`); continue; }
    const [, kid, code, blatt] = res.qr.split('|'); const b = +blatt;
    if (st.kid && kid !== st.kid && kid !== 'STD') st.probs.push(`${s.name}: gehört zu Klausur ${kid}, nicht ${st.kid}`);
    if (!st.kid || st.kid === 'STD') st.kid = kid;
    const C = st.codes[code] || (st.codes[code] = { code, blatt: {} });
    if (C.blatt[b]){ st.probs.push(`${s.name}: Code ${code} Blatt ${b} doppelt – übersprungen`); continue; }
    C.blatt[b] = { scan: s.name, ...res };
  }
  for (const C of Object.values(st.codes)){
    const bs = Object.keys(C.blatt).map(Number), mx = Math.max(...bs);
    const miss = []; for (let b = 1; b <= mx; b++) if (!C.blatt[b]) miss.push(b);
    if (miss.length) st.probs.push(`Code ${C.code}: Blatt ${miss.join(', ')} fehlt`);
  }
  buildUploads();
}
async function processPage(bmp){
  const a = findAnchors(bmp); if (!a) return { ok: false, msg: 'Ankerpunkte nicht gefunden' };
  const cv = new OffscreenCanvas(bmp.width, bmp.height), g = cv.getContext('2d'); g.drawImage(bmp, 0, 0);
  const src = g.getImageData(0, 0, bmp.width, bmp.height);
  let H = null, qr = '';
  for (const ord of ORDERS){
    const Hk = homography(CANON, ord.map(k => a[k]));
    const q = qrRead(src, Hk); if (q.startsWith('KORR|')){ H = Hk; qr = q; break; }
  }
  if (!H) return { ok: false, msg: 'QR-Code nicht lesbar' };
  const page = warp(src, H, 0, 0, PW_ / MM, PH_ / MM, 150);
  const gray = grayOf(page), segs = words(gray);
  const pc = new OffscreenCanvas(page.width, page.height); pc.getContext('2d').putImageData(page, 0, 0);
  const jpg = await pc.convertToBlob({ type: 'image/jpeg', quality: 0.88 });
  return { ok: true, qr, H, src, gray, segs, segsRoh: JSON.parse(JSON.stringify(segs)), jpg, w: page.width, h: page.height };
}
// ---------------------------------------------------------------- Upload-Bilder
function buildUploads(){
  if (st.mode && st.mode !== 'halb') return buildStreifen(+st.mode.slice(1));
  st.uploads = [];
  const codes = Object.keys(st.codes).sort((a, b) => a.localeCompare(b, 'de', { numeric: true }));
  for (const code of codes){
    const C = st.codes[code], list = [];
    for (const b of Object.keys(C.blatt).map(Number).sort((x, y) => x - y)){
      const pg = C.blatt[b];
      for (const hf of HALF){
        let ink = 0; for (let z = hf.z0; z <= hf.z1; z++) ink += (pg.segs[z] || []).length;
        if (!ink) continue;
        list.push({ code, b, hf, name: `Code${code}_B${b}_Z${String(hf.z0).padStart(2, '0')}-${hf.z1}.jpg`, label: `Code ${code} - Blatt ${b} - Zeilen ${hf.z0}-${hf.z1}` });
      }
    }
    for (let k = 0; k < list.length; k += MAXIMG) st.uploads.push({ code, part: k / MAXIMG + 1, parts: Math.ceil(list.length / MAXIMG), imgs: list.slice(k, k + MAXIMG) });
  }
}
// TEST: Zeilenstreifen – nur beschriebene Zeilen, links beschriftet, ohne Rand; mehrere Codes pro Nachricht
const STR = { x0: 18.8, x1: 158.5, top: 8.2, bot: 1.8, lab: 20, gap: 8 };
function buildStreifen(perImg){
  st.uploads = []; const items = [];
  const codes = Object.keys(st.codes).sort((a, b) => a.localeCompare(b, 'de', { numeric: true }));
  for (const code of codes){
    const C = st.codes[code], lines = [];
    for (const b of Object.keys(C.blatt).map(Number).sort((x, y) => x - y))
      for (let z = 1; z <= 23; z++) if ((C.blatt[b].segs[z] || []).length) lines.push([b, z]);
    const n = Math.ceil(lines.length / perImg), per = Math.ceil(lines.length / n);
    for (let k = 0; k < n; k++){
      const L = lines.slice(k * per, (k + 1) * per), bs = [...new Set(L.map(l => l[0]))];
      items.push({ code, streifen: L, name: `Code${code}_Teil${k + 1}.jpg`, label: `Code ${code} - Teil ${k + 1} von ${n} - Blatt ${bs.join(', ')}` });
    }
  }
  for (let k = 0; k < items.length; k += MAXIMG){
    const imgs = items.slice(k, k + MAXIMG), cs = [...new Set(imgs.map(i => i.code))];
    st.uploads.push({ code: cs.join('-'), part: 1, parts: 1, imgs });
  }
}
async function streifenImage(u){
  const ppm = UPLOAD_DPI / 25.4, head = 72, labW = Math.round(STR.lab * ppm);
  const strips = u.streifen.map(([b, z]) => { const pg = st.codes[u.code].blatt[b], y = lineY(z) / MM;
    return { b, z, im: warp(pg.src, pg.H, STR.x0, y - STR.top, STR.x1, y + STR.bot, UPLOAD_DPI) }; });
  const W = labW + strips[0].im.width, H = head + strips.reduce((s, x) => s + x.im.height + STR.gap, 0);
  const cv = new OffscreenCanvas(W, H), g = cv.getContext('2d');
  g.fillStyle = '#fff'; g.fillRect(0, 0, W, H);
  g.fillStyle = '#000'; g.font = 'bold 44px Helvetica, Arial, sans-serif'; g.textBaseline = 'middle'; g.fillText(u.label, 24, head / 2 + 2);
  let y = head;
  for (const s of strips){
    g.fillStyle = '#ccc'; g.fillRect(0, y, W, 2);
    g.putImageData(s.im, labW, y + STR.gap / 2);
    g.fillStyle = '#000'; g.font = 'bold 38px Helvetica, Arial, sans-serif'; g.fillText(`B${s.b} Z${s.z}`, 14, y + STR.gap / 2 + s.im.height * 0.55);
    y += s.im.height + STR.gap;
  }
  return await cv.convertToBlob({ type: 'image/jpeg', quality: 0.9 });
}
async function uploadImage(u){
  if (u.streifen) return streifenImage(u);
  const pg = st.codes[u.code].blatt[u.b], im = warp(pg.src, pg.H, X0MM, u.hf.y0, X1MM, u.hf.y1, UPLOAD_DPI);
  const head = 72, cv = new OffscreenCanvas(im.width, im.height + head), g = cv.getContext('2d');
  g.fillStyle = '#fff'; g.fillRect(0, 0, cv.width, cv.height); g.putImageData(im, 0, head);
  g.fillStyle = '#000'; g.font = 'bold 44px Helvetica, Arial, sans-serif'; g.textBaseline = 'middle'; g.fillText(u.label, 24, head / 2 + 2);
  return await cv.convertToBlob({ type: 'image/jpeg', quality: 0.9 });
}
// ZIP (ohne Kompression)
const CRC = (() => { const t = new Uint32Array(256); for (let n = 0; n < 256; n++){ let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; })();
const crc32 = b => { let c = 0xFFFFFFFF; for (let i = 0; i < b.length; i++) c = CRC[(c ^ b[i]) & 255] ^ (c >>> 8); return (c ^ 0xFFFFFFFF) >>> 0; };
function zip(files){
  const enc = new TextEncoder(), parts = [], cen = []; let off = 0;
  for (const f of files){
    const nm = enc.encode(f.name), crc = crc32(f.data), h = new DataView(new ArrayBuffer(30));
    h.setUint32(0, 0x04034b50, true); h.setUint16(4, 20, true); h.setUint16(6, 0x0800, true); h.setUint32(14, crc, true);
    h.setUint32(18, f.data.length, true); h.setUint32(22, f.data.length, true); h.setUint16(26, nm.length, true);
    parts.push(new Uint8Array(h.buffer), nm, f.data);
    const c = new DataView(new ArrayBuffer(46));
    c.setUint32(0, 0x02014b50, true); c.setUint16(4, 20, true); c.setUint16(6, 20, true); c.setUint16(8, 0x0800, true); c.setUint32(16, crc, true);
    c.setUint32(20, f.data.length, true); c.setUint32(24, f.data.length, true); c.setUint16(28, nm.length, true); c.setUint32(42, off, true);
    cen.push(new Uint8Array(c.buffer), nm); off += 30 + nm.length + f.data.length;
  }
  const csz = cen.reduce((n, x) => n + x.length, 0), e = new DataView(new ArrayBuffer(22));
  e.setUint32(0, 0x06054b50, true); e.setUint16(8, files.length, true); e.setUint16(10, files.length, true); e.setUint32(12, csz, true); e.setUint32(16, off, true);
  return new Blob([...parts, ...cen, new Uint8Array(e.buffer)], { type: 'application/zip' });
}
async function uploadZip(progress){
  const files = [], enc = new TextEncoder(); let n = 0, total = st.uploads.reduce((s, u) => s + u.imgs.length, 0);
  const lines = ['So geht’s:', '1. Im AIS.chat-Assistenten „Abschrift“ einen neuen Chat öffnen.', '2. Für jeden Ordner eine Nachricht: alle Bilder des Ordners hochladen und senden.',
    '3. Wenn alle Nachrichten beantwortet sind: die Antworten nacheinander kopieren und in der Arbeitsfläche bei „Abschrift einfügen“ einfügen.', ''];
  for (let k = 0; k < st.uploads.length; k++){
    const u = st.uploads[k], dir = `Nachricht_${String(k + 1).padStart(2, '0')}_Code${u.code}${u.parts > 1 ? `_Teil${u.part}` : ''}/`;
    lines.push(dir + '  ' + u.imgs.length + ' Bild(er)');
    for (const im of u.imgs){ progress(`Bild ${++n} von ${total} …`); await new Promise(r => setTimeout(r, 0)); files.push({ name: dir + im.name, data: new Uint8Array(await (await uploadImage(im)).arrayBuffer()) }); }
  }
  files.unshift({ name: '0_So_gehts.txt', data: enc.encode(lines.join('\r\n')) });
  return zip(files);
}
// ---------------------------------------------------------------- Abschrift + Fehlerliste -> Vorschläge
function analyse(){
  const A = parseAnswers(st.textA + '\n' + st.textB), rep = {};
  for (const code of Object.keys(st.codes)){
    const C = st.codes[code], b = A[code] || { text: {}, err: [], hint: [], probs: [] }, r = rep[code] = { lines: 0, words: 0, err: b.err.length, ok: 0, probs: b.probs.slice(), hint: b.hint, fallback: 0, notext: false, lese: [] };
    C.text = b.text; C.err = b.err;
    if (!Object.keys(b.text).length){ r.notext = true; continue; }
    for (const bl of Object.keys(b.text)){
      const pg = C.blatt[bl]; if (!pg){ r.probs.push(`Blatt ${bl} steht in der Abschrift, aber nicht im Scan`); continue; }
      const segs = pg.segs = JSON.parse(JSON.stringify(pg.segsRoh)), L = GEO().lines; pg.fb = {};
      for (const z of Object.keys(b.text[bl])){
        const toks = b.text[bl][z].split(/\s+/).filter(Boolean); r.lines++; r.words += toks.filter(t => !t.startsWith('~~')).length;
        const F = segs[z] || [];
        if (!F.length){ r.probs.push(`B${bl} Z${z}: Text, aber keine Schrift im Scan erkannt`); continue; }
        let neu = alignLine(F, toks, lineProfile(pg.gray, L, +z));
        if (neu.length !== toks.length){ neu = splitEven(F, toks); pg.fb[z] = true; r.fallback++; }
        segs[z] = neu;
      }
      for (const z of Object.keys(segs)) if (!(z in b.text[bl])) delete segs[z];
    }
    C.sug = [];
    b.err.forEach(e => {
      const tag = `B${e.b} Z${e.z} »${e.w}«`;
      if (!SIGNS.has(e.sign) && SIGN_OF[e.sign.toUpperCase()]){ const z = SIGN_OF[e.sign.toUpperCase()]; r.mapped = (r.mapped || 0) + 1; if (!MUSTERSET.has(e.m)) e.m = e.sign.toUpperCase(); e.sign = z; }
      if (!SIGNS.has(e.sign)){ r.probs.push(`${tag}: unbekanntes Zeichen „${e.sign}“`); return; }
      if (!MUSTERSET.has(e.m)) r.probs.push(`${tag}: unbekanntes Fehlermuster „${e.m}“ (übernommen)`);
      const T = b.text[e.b] || {};
      let line = T[e.z], toks = line === undefined ? [] : line.split(/\s+/).filter(Boolean), pos = line === undefined ? null : findWords(toks, e.w);
      if (!pos){                                                                   // Zeilennummer um eins verrutscht?
        const alt = [e.z - 1, e.z + 1].filter(z => T[z] !== undefined && findWords(T[z].split(/\s+/).filter(Boolean), e.w));
        if (alt.length === 1){ r.probs.push(`${tag}: steht in Z${alt[0]} – dorthin gesetzt`); e.z = alt[0]; line = T[e.z]; toks = line.split(/\s+/).filter(Boolean); pos = findWords(toks, e.w); }
      }
      if (!pos){ r.probs.push(line === undefined ? `${tag}: Zeile fehlt in der Abschrift` : `${tag}: Wörter stehen nicht in dieser Zeile der Abschrift`); return; }
      let conf = 'seu'.includes(e.conf) ? e.conf : 'e', note = '';
      if (toks.slice(pos[0] - 1, pos[1]).some(t => t.includes('[?]'))) conf = 'u';
      if (e.gap && e.sign === 'Z' && /^[.!?]$/.test(e.c)){                       // fehlender Satzpunkt: oft nur übersehen
        const next = toks[pos[1]] !== undefined ? toks[pos[1]] : nextLineFirst(b.text[e.b], e.z);
        if (next === null || (/^["'“(]?[A-Z]/.test(next) && !/^["'“(]?I\b/.test(next))){ conf = 'u'; note = 'Punkt evtl. vorhanden'; }
      }
      if (C.blatt[e.b] && C.blatt[e.b].fb && C.blatt[e.b].fb[e.z]) conf = conf === 's' ? 'e' : conf;
      if (e.c.replace(/\s+/g, ' ').trim() === toks.slice(pos[0] - 1, pos[1]).join(' ')){ r.lese.push(`${tag} ${e.sign} (${e.c}) – Korrektur gleich dem Original`); return; }
      const lf = leseFehler(e, toks, pos, b.text[e.b]);
      if (lf){ if (st.skipLese){ r.lese.push(`${tag} ${e.sign} (${e.c}) – ${lf}`); return; } conf = 'u'; note = lf; }
      C.sug.push({ b: e.b, z: e.z, w0: pos[0], w1: pos[1], gap: e.gap, sign: e.sign, c: e.c, m: e.m, conf, note }); r.ok++;
    });
  }
  return rep;
}
// Anstreichungen, die sehr wahrscheinlich auf einem Lesefehler der Abschrift beruhen (Tests 05.11.2026)
function leseFehler(e, toks, pos, T){
  const marked = toks.slice(pos[0] - 1, pos[1]), last = marked[marked.length - 1] || '';
  const next = toks[pos[1]] !== undefined ? toks[pos[1]] : nextLineFirst(T, e.z);
  const klein = next && /^["'“‘(]?[a-z]/.test(next);
  // Komma als Punkt gelesen: „parents. friends“ -> Vorschlag „parents,“
  if (e.sign === 'Z' && /\.$/.test(last) && klein && (e.c === ',' || e.c.replace(/\s+/g, '') === marked.join('').replace(/\.$/, ',')))
    return 'Komma vermutlich als Punkt gelesen';
  // Zeilenangaben und Zitatklammern: „(l. 1).“, „(ll. 23-24).“, „[...]“
  if ((e.sign === 'Z' || e.sign === 'R') && marked.some(t => /^[(\[{]?l{1,2}\.$/.test(t) || /^[(\[{]?\d+([-–]\d+)?[)\]}]+[.,;:]?$/.test(t) || /^[(\[{]\.\.\.[)\]}]/.test(t)))
    return 'Zeilenangabe oder Klammer';
  return '';
}
function nextLineFirst(T, z){
  const zs = Object.keys(T).map(Number).sort((a, b) => a - b), k = zs.indexOf(+z);
  if (k < 0 || k === zs.length - 1 || zs[k + 1] !== +z + 1) return null;                 // Absatzende
  return T[zs[k + 1]].split(/\s+/)[0] || null;
}
const DEFAULT_META = /*DEFAULT_META*/null;
const DEFAULT_POOL = /*DEFAULT_POOL*/null;
const MUSTER = { KOM: 'Kommasetzung', SVA: '3. Person Singular / Kongruenz', TEMP: 'Zeitformen (simple / progressive / perfect)',
  VERB: 'Verbformen (Gerund, Infinitiv, Verneinung, Passiv)', ADV: 'Adjektiv oder Adverb', ART: 'Artikel', KOMP: 'Steigerung', ST: 'Wortstellung',
  PRAEP: 'Präpositionen', FF: 'False Friends / deutsche Strukturen', WW: 'Wortwahl / Kollokation', VW: "Verwechslungswörter (their/there, its/it's, then/than …)",
  REG: 'Register (Kurzformen, Umgangssprache)', RS: 'Rechtschreibung', SB: 'Satzbau (Komma-Reihung, Satzgrenzen)', REL: 'Relativpronomen (who / which / whose)', WF: 'Wortform (Plural, Demonstrativ)' };
function buildData(){
  const meta = st.meta || Object.assign({}, DEFAULT_META, { id: st.kid, titel: `Klausur ${st.kid}`, datum: new Date().toLocaleDateString('de-DE') });
  const data = { format: 'korrektur-paket', version: 2, paket_id: (crypto.randomUUID ? crypto.randomUUID() : String(Math.random())).replace(/-/g, '').slice(0, 12),
    klausur: { id: meta.id, titel: meta.titel, datum: meta.datum }, muster: meta.muster || MUSTER, pool: st.pool || DEFAULT_POOL || {},
    eh: meta.eh, schluessel: meta.schluessel, codes: [], erstellt: new Date().toISOString().slice(0, 10), quelle: 'AIS.chat' };
  const blobs = [];
  for (const code of Object.keys(st.codes).sort((a, b) => a.localeCompare(b, 'de', { numeric: true }))){
    const C = st.codes[code]; if (!C.sug || !C.err || !C.err.length) continue;
    const bl = Object.keys(C.blatt).map(Number).sort((a, b) => a - b), pages = [], sug = [];
    for (const b of bl){
      const pg = C.blatt[b], g = GEO(), edges = {};
      Object.entries(pg.segs).forEach(([k, v]) => { if (v.length) edges[k] = [v[0][0], v[v.length - 1][1]]; });
      pages.push({ img: URL.createObjectURL(pg.jpg), w: g.w, h: g.h, lines: g.lines, side: g.side, lt: g.lt, rt: g.rt, edges });
      blobs.push({ code, pi: pages.length - 1, blob: pg.jpg });
    }
    const L = GEO().lines; let wc = 0;
    Object.values(C.text).forEach(T => Object.values(T).forEach(l => l.split(/\s+/).forEach(t => { if (t && !t.startsWith('~~') && t !== '·') wc++; })));
    C.sug.forEach((e, i) => {
      const ws = (C.blatt[e.b].segs[e.z]) || []; let sg;
      if (ws.length < e.w1) return;
      if (e.gap){
        let x0 = ws[e.w1 - 1][1] - 8, x1 = e.w1 < ws.length ? ws[e.w1][0] + 4 : ws[e.w1 - 1][1] + 22;
        if (x1 - x0 < 18){ const m = (x0 + x1) / 2; x0 = m - 9; x1 = m + 9; }
        sg = [[Math.round(x0), Math.round(x1), Math.round(L[e.z]) + 4, e.z, 'gap']];
      } else sg = [[ws[e.w0 - 1][0], ws[e.w1 - 1][1], Math.round(L[e.z]) + 4, e.z]];
      sug.push({ id: `${code}-${String(i + 1).padStart(2, '0')}`, page: bl.indexOf(e.b), segs: sg, line: e.z, sign: e.sign, corr: e.c, conf: CONF[e.conf], muster: e.m, ...(e.note ? { hinweis: e.note } : {}) });
    });
    data.codes.push({ code, pages, sug, woerter: wc });
  }
  return { data, blobs };
}
// Vorkorrektur-PDF (gleiches Format wie kw.py paket; ohne Vorschau-Zeichnung)
async function packagePdf(data, blobs){
  const enc = new TextEncoder(), chunks = []; let len = 0; const offs = {};
  const put = x => { const b = typeof x === 'string' ? enc.encode(x) : x; chunks.push(b); len += b.length; };
  const obj = (n, body) => { offs[n] = len; put(`${n} 0 obj\n`); put(body); put('\nendobj\n'); };
  put(new Uint8Array([37, 80, 68, 70, 45, 49, 46, 55, 10, 37, 226, 227, 207, 211, 10]));
  const D = JSON.parse(JSON.stringify(data)), first = 10, ids = blobs.map((_, i) => [first + 3 * i, first + 3 * i + 1, first + 3 * i + 2]);
  const JSON_ID = first + 3 * blobs.length, SPEC_ID = JSON_ID + 1;
  for (let k = 0; k < blobs.length; k++){
    const [Pn, Cn, In] = ids[k], jpg = new Uint8Array(await blobs[k].blob.arrayBuffer()), pg = D.codes.find(c => c.code === blobs[k].code).pages[blobs[k].pi];
    const cs = 'q 595.28 0 0 841.89 0 0 cm /Im0 Do Q\n';
    obj(Pn, `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595.28 841.89] /Resources << /XObject << /Im0 ${In} 0 R >> >> /Contents ${Cn} 0 R >>`);
    obj(Cn, `<< /Length ${cs.length} >>\nstream\n${cs}\nendstream`);
    offs[In] = len; put(`${In} 0 obj\n<< /Type /XObject /Subtype /Image /Width ${pg.w} /Height ${pg.h} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${jpg.length} >>\nstream\n`);
    pg.img = { off: len, len: jpg.length }; put(jpg); put('\nendstream\nendobj\n');
  }
  const js = enc.encode(JSON.stringify(D));
  offs[JSON_ID] = len; put(`${JSON_ID} 0 obj\n<< /Type /EmbeddedFile /Subtype /application#2Fjson /Length ${js.length} >>\nstream\n`);
  const joff = len; put(js); put('\nendstream\nendobj\n'); put(`%KORRDATA ${joff} ${js.length}\n`);
  obj(SPEC_ID, `<< /Type /Filespec /F (korrektur.json) /UF (korrektur.json) /EF << /F ${JSON_ID} 0 R >> >>`);
  obj(1, `<< /Type /Catalog /Pages 2 0 R /Names << /EmbeddedFiles << /Names [(korrektur.json) ${SPEC_ID} 0 R] >> >> >>`);
  obj(2, `<< /Type /Pages /Kids [${ids.map(i => i[0] + ' 0 R').join(' ')}] /Count ${ids.length} >>`);
  const maxid = SPEC_ID + 1, xref = len; let x = `xref\n0 ${maxid}\n0000000000 65535 f \n`;
  for (let n = 1; n < maxid; n++) x += n in offs ? `${String(offs[n]).padStart(10, '0')} 00000 n \n` : '0000000000 65535 f \n';
  put(x + `trailer\n<< /Size ${maxid} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`);
  return new Blob(chunks, { type: 'application/pdf' });
}
function abschriftFuerB(code){
  const T = st.codes[code] && st.codes[code].text; if (!T || !Object.keys(T).length) return '';
  const out = [`### CODE ${code}`, '### TEXT'];
  Object.keys(T).map(Number).sort((a, b) => a - b).forEach(b => Object.keys(T[b]).map(Number).sort((a, c) => a - c).forEach(z => out.push(`B${b} Z${z}: ${T[b][z]}`)));
  return out.join('\n');
}
return { st, readScan, uploadZip, uploadImage, buildUploads, analyse, buildData, packagePdf, saveTexts, loadTexts, abschriftFuerB, parseAnswers, findWords, alignLine, words, GEO };
})();

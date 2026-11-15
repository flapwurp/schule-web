// ===================== AIS-Vorbereitung: Oberfläche =====================
(() => {
const q = s => document.querySelector(s), st = P.st;
const showPrep = on => { q('#prep').style.display = on ? 'block' : 'none'; document.body.classList.toggle('prepping', on); if (on) q('#start').style.display = 'none'; else if (!D) q('#start').style.display = 'flex'; };
q('#startPrep').onclick = () => showPrep(true);
q('#prepBack').onclick = () => showPrep(false);
q('#prepScanBtn').onclick = () => q('#prepScan').click();
q('#prepMetaBtn').onclick = () => q('#prepMeta').click();
const busy = (el, t) => { el.textContent = t; };
q('#prepScan').onchange = async e => {
  const files = [...e.target.files]; e.target.value = ''; if (!files.length) return;
  const s = q('#scanStatus'); s.className = 'pst';
  try {
    st.file = files.map(f => f.name).join(', ');
    await P.readScan(files, t => busy(s, t));
    P.loadTexts(); q('#taA').value = st.textA; q('#taB').value = st.textB;
    renderScan(); renderUploads(); analyse();
  } catch(err){ console.error(err); s.className = 'pst err'; s.textContent = err.message; }
};
q('#prepMeta').onchange = async e => {
  const f = e.target.files[0]; e.target.value = ''; if (!f) return;
  try { const m = JSON.parse(await f.text()); if (!m.eh || !m.schluessel) throw new Error('Die Datei enthält keinen Erwartungshorizont (eh) und Notenschlüssel.');
    st.meta = m; if (m.pool) st.pool = m.pool; q('#metaStatus').textContent = `${m.titel || m.id}`; q('#metaStatus').className = 'pst ok';
  } catch(err){ q('#metaStatus').textContent = 'Klausurdatei nicht lesbar: ' + err.message; q('#metaStatus').className = 'pst err'; }
};
function renderScan(){
  const codes = Object.keys(st.codes).sort((a, b) => a.localeCompare(b, 'de', { numeric: true }));
  const s = q('#scanStatus');
  s.className = 'pst ' + (st.probs.length ? 'warn' : 'ok');
  s.innerHTML = `${codes.length} Klausuren erkannt${st.kid ? ` (Klausur ${esc(st.kid)})` : ''}.` + (st.probs.length ? `<ul>${st.probs.map(p => `<li>${esc(p)}</li>`).join('')}</ul>` : '');
  q('#prepS2').classList.toggle('off', !codes.length); q('#prepS3').classList.toggle('off', !codes.length);
}
function renderUploads(){
  const U = st.uploads || [], n = U.reduce((s, u) => s + u.imgs.length, 0);
  q('#upSum').innerHTML = `<b>${U.length} Nachrichten</b> mit zusammen ${n} Bildern (höchstens 5 je Nachricht, leere Zeilen weggelassen).`;
  q('#upList').innerHTML = U.map((u, k) => `<div class="upm"><b>Nachricht ${k + 1}</b> · Code ${esc(u.code)}${u.parts > 1 ? ` (Teil ${u.part}/${u.parts})` : ''} · ${u.imgs.map(i => `<button class="lnk" data-up="${k}" data-im="${esc(i.name)}">${esc(i.label.replace(/^Code \S+ - /, ''))}</button>`).join(', ')}</div>`).join('');
}
q('#upMode').onchange = e => { st.mode = e.target.value; P.buildUploads(); renderUploads(); };
q('#upList').onclick = async e => {
  const b = e.target.closest('[data-up]'); if (!b) return;
  const im = st.uploads[+b.dataset.up].imgs.find(i => i.name === b.dataset.im), blob = await P.uploadImage(im);
  const url = URL.createObjectURL(blob); q('#upPrev').innerHTML = `<div class="cap">${esc(im.label)} <button class="lnk" id="upPrevX">schließen</button></div><img src="${url}">`;
  q('#upPrevX').onclick = () => q('#upPrev').innerHTML = '';
};
q('#upZip').onclick = async () => {
  const btn = q('#upZip'), t = btn.textContent; btn.disabled = true;
  try { const z = await P.uploadZip(x => btn.textContent = x); download(z, `AIS-Upload_${st.kid || 'Klausur'}.zip`); }
  catch(err){ toast(err.message, 8000); } finally { btn.textContent = t; btn.disabled = false; }
};
q('#skipLese').onchange = e => { st.skipLese = e.target.checked; analyse(); };
let tmr = null;
['#taA', '#taB'].forEach(id => q(id).addEventListener('input', () => { clearTimeout(tmr); tmr = setTimeout(() => { st.textA = q('#taA').value; st.textB = q('#taB').value; P.saveTexts(); analyse(); }, 350); }));
function analyse(){
  if (!Object.keys(st.codes).length) return;
  st.textA = q('#taA').value; st.textB = q('#taB').value;
  const rep = P.analyse(), codes = Object.keys(rep).sort((a, b) => a.localeCompare(b, 'de', { numeric: true }));
  let ready = 0;
  q('#repTab').innerHTML = `<tr><th>Code</th><th>Abschrift</th><th>Für Assistent B</th><th>Fehlerliste</th><th>Hinweise und Probleme</th></tr>` + codes.map(c => {
    const r = rep[c]; if (r.err) ready++;
    const ab = r.notext ? '<span class="miss">fehlt</span>' : `${r.lines} Zeilen, ${r.words} Wörter` + (r.fallback ? ` <span class="warn" title="Wörter und Schriftbild passten nicht zusammen; Wortgrenzen geschätzt">· ${r.fallback} Zeile(n) geschätzt</span>` : '');
    const fl = r.notext ? '–' : !r.err ? '<span class="miss">fehlt</span>' : `${r.ok} von ${r.err} übernommen` + (r.lese.length ? `<br><span class="miss">${r.lese.length} vermutete Lesefehler weggelassen</span>` : '');
    const notes = [...(r.mapped ? [`<li class="miss">${r.mapped}× Fehlermuster statt Zeichen angegeben – Zeichen ergänzt (z. B. KOMP → G)</li>`] : []), ...r.probs.map(p => `<li class="warn">${esc(p)}</li>`), ...r.hint.map(h => `<li>${esc(h)}</li>`),
      ...(r.lese.length ? [`<li><details><summary>${r.lese.length} vermutete Lesefehler bzw. leere Korrekturen nicht übernommen</summary>${r.lese.map(esc).join('<br>')}</details></li>`] : [])].join('');
    return `<tr><td><b>${esc(c)}</b></td><td>${ab}</td><td>${r.notext ? '' : `<button class="lnk" data-copy="${esc(c)}">kopieren</button>`}</td><td>${fl}</td><td>${notes ? `<ul>${notes}</ul>` : ''}</td></tr>`;
  }).join('');
  q('#prepOpen').disabled = q('#prepSave').disabled = !ready;
  q('#prepReady').textContent = ready ? `${ready} von ${codes.length} Klausuren bereit.` : 'Noch keine Fehlerliste eingefügt.';
}
q('#repTab').onclick = async e => {
  const b = e.target.closest('[data-copy]'); if (!b) return;
  try { await navigator.clipboard.writeText(P.abschriftFuerB(b.dataset.copy)); toast(`Abschrift Code ${b.dataset.copy} kopiert – in den Assistenten „Korrektur“ einfügen.`, 4000); }
  catch(err){ toast('Kopieren nicht möglich: ' + err.message, 6000); }
};
q('#copyAllB').onclick = async () => {
  const t = Object.keys(st.codes).sort((a, b) => a.localeCompare(b, 'de', { numeric: true })).map(P.abschriftFuerB).filter(Boolean).join('\n\n');
  if (!t) return toast('Noch keine Abschrift eingefügt.', 4000);
  try { await navigator.clipboard.writeText(t); toast('Alle Abschriften kopiert.', 4000); } catch(err){ toast('Kopieren nicht möglich: ' + err.message, 6000); }
};
q('#prepOpen').onclick = () => {
  try { const { data } = P.buildData(); if (!data.codes.length) throw new Error('Keine Klausur mit Fehlerliste.'); showPrep(false); boot(data);
    const fehlt = Object.keys(st.codes).filter(c => !data.codes.some(x => x.code === c));
    toast(`${data.codes.length} Klausuren aus AIS.chat geladen.` + (fehlt.length ? ` Noch ohne Fehlerliste und daher nicht geladen: ${fehlt.join(', ')}.` : '') + ' Tipp: „Vorkorrektur-PDF speichern“ sichert die Vorbereitung als Datei.', 9000); }
  catch(err){ console.error(err); toast(err.message, 8000); }
};
q('#prepSave').onclick = async () => {
  try { const { data, blobs } = P.buildData(); const pdf = await P.packagePdf(data, blobs); download(pdf, `${data.klausur.id}_Vorkorrektur_AIS.pdf`); }
  catch(err){ console.error(err); toast(err.message, 8000); }
};
})();

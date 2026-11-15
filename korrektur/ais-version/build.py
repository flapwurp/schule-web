"""Baut die AIS-Arbeitsfläche: Arbeitsfläche v1 + Vorbereitungsmodul (src/) + jsQR, als eine Offline-HTML-Datei.
  python3 build.py <jsQR.js> <foerderpool.json> <standard-klausur.json>
Die v1-Datei (../arbeitsflaeche/arbeitsflaeche.html) bleibt unverändert."""
import sys, json, os
H = os.path.dirname(os.path.abspath(__file__))
rd = lambda p: open(os.path.join(H, p), encoding='utf-8').read()
jsqr, pool, meta = open(sys.argv[1], encoding='utf-8').read(), json.load(open(sys.argv[2])), json.load(open(sys.argv[3]))

def sub(s, old, new, count=1):
    assert s.count(old) >= 1, f'Stelle nicht gefunden: {old[:60]!r}'
    return s.replace(old, new, count)

# Standard-Bewertung ohne Klausurdatei: Sprachteile aus der Vorlage, Inhalt als ein Platzhalter-Kriterium
inh = sum(t['max'] for t in meta['eh'] if not t.get('sprache'))
default = dict(eh=[dict(teil='Inhalt (laut Erwartungshorizont)', max=inh,
                        krit=[dict(id='i1', t='Inhaltliche Leistung gesamt – Klausurdatei laden für die einzelnen Kriterien', max=inh)])]
                  + [t for t in meta['eh'] if t.get('sprache')], schluessel=meta['schluessel'])

s = rd('../arbeitsflaeche/arbeitsflaeche.html')
s = sub(s, '<title>Korrektur-Arbeitsfläche</title>', '<title>Korrektur-Arbeitsfläche (AIS)</title>')
s = sub(s, '</style>', rd('src/prep.css') + '</style>')
s = sub(s, '<p class="err" id="startErr"></p>',
        '<p class="err" id="startErr"></p>\n  <div class="alt"><p><b>Neue Klausur aus dem Scan vorbereiten</b><br><span class="note small">'
        'Abschrift und Fehlerliste kommen aus AIS.chat.</span></p><button class="btn" id="startPrep">Mit AIS.chat vorbereiten …</button></div>')
s = sub(s, '<script id="data"', rd('src/prep.html') + '\n<script id="data"')
s = sub(s, "document.addEventListener('drop', e => openFiles(",
        "document.addEventListener('drop', e => document.body.classList.contains('prepping') ? null : openFiles(")
prep = rd('src/prep.js').replace('/*DEFAULT_META*/null', json.dumps(default, ensure_ascii=False)) \
                        .replace('/*DEFAULT_POOL*/null', json.dumps(pool, ensure_ascii=False))
tail = ('<script>/* jsQR – Apache License 2.0, https://github.com/cozmo/jsQR */\n' + jsqr + '\n</script>\n'
        '<script>\n' + prep + '\n</script>\n<script>\n' + rd('src/prep_ui.js') + '\n</script>\n</body>')
s = sub(s, '</body>', tail)
out = os.path.join(H, 'arbeitsflaeche_ais.html')
open(out, 'w', encoding='utf-8').write(s)
print(out, round(len(s.encode()) / 1e3), 'kB')

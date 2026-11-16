"""Baut ../workflow-ki-korrektur.html aus workflow_src.html.
Bettet ein: Arbeitsfläche (Gestaltungs-Version), Förderpool, Bewertungsraster EF, QR-Codes der Demo-Bögen.
Aufruf aus diesem Ordner:  python3 build.py [pfad/zur/arbeitsflaeche.html]
Standard: ../../korrekturtest-design/arbeitsflaeche.html"""
import json, sys, os
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, '..', '..', 'korrektur', 'ais-version', 'src')
af = sys.argv[1] if len(sys.argv) > 1 else os.path.join(H, '..', '..', 'korrekturtest-design', 'arbeitsflaeche.html')
s = open(os.path.join(H, 'workflow_src.html'), encoding='utf-8').read()
meta = json.load(open(os.path.join(R, 'standard_klausur_EF.json'), encoding='utf-8'))
m = dict(pool=json.load(open(os.path.join(R, 'foerderpool.json'), encoding='utf-8')), eh=meta['eh'], schluessel=meta['schluessel'],
         qr=json.load(open(os.path.join(H, 'qr.json'))))
j = lambda x: json.dumps(x, ensure_ascii=False).replace('</', '<\\/')
s = s.replace('/*META*/', j(m), 1).replace('/*AFTPL*/', j(open(af, encoding='utf-8').read()), 1)
open(os.path.join(H, '..', 'workflow-ki-korrektur.html'), 'w', encoding='utf-8').write(s); print('ok', round(len(s.encode()) / 1e3), 'kB')

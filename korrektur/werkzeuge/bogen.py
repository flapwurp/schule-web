"""Klausurbögen (Master-Satz) und Zuordnungsliste.
Master:   python3 bogen.py master <out.pdf> [anzahl_codes=35] [blaetter=6] [seed]
Liste:    python3 bogen.py liste <out.pdf> <codes_kommagetrennt>
Geometrie (mm, von oben links) ist fest und wird von einlesen.py vorausgesetzt:
Ankerpunkte 6x6 mm, Mittelpunkte (11|11) (199|11) (11|286) (199|286); Lineatur 23 Zeilen ab y=52, Abstand 10;
Text x=20..158, Korrekturrand 158..202; QR 'KORR|STD|<code>|<blatt>' bei x=166..192, y=12..38."""
import sys, random
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF

W, H = A4
LINE, GREY = (0.70, 0.79, 0.90), (0.45, 0.45, 0.45)
def Y(ymm): return H - ymm * mm

def qr(c, data, x, y, size):
    w = QrCodeWidget(data); w.barLevel = 'M'
    b = w.getBounds(); bw, bh = b[2] - b[0], b[3] - b[1]
    d = Drawing(size, size, transform=[size / bw, 0, 0, size / bh, 0, 0]); d.add(w); renderPDF.draw(d, c, x, y)

def sheet(c, code, blatt, kopf='Englisch · Klausur'):
    c.setFillColorRGB(0, 0, 0)
    for xm, ym in [(8, 8), (196, 8), (8, 283), (196, 283)]:
        c.rect(xm * mm, Y(ym + 6), 6 * mm, 6 * mm, stroke=0, fill=1)
    c.setFont('Helvetica-Bold', 12); c.drawString(20 * mm, Y(17), kopf)
    c.setFont('Helvetica', 9.5); c.drawString(20 * mm, Y(23.5), 'Kurs: ______________    Datum: ______________')
    c.setFont('Helvetica-Oblique', 8); c.setFillColorRGB(*GREY)
    c.drawString(20 * mm, Y(29), 'Bitte keinen Namen eintragen – dein Code steht oben rechts.')
    c.setFillColorRGB(0, 0, 0); c.setFont('Helvetica', 9); c.drawString(20 * mm, Y(36), 'Auf diesem Blatt bearbeite ich Aufgabe:')
    for i, a in enumerate(['1', '2', '3']):
        bx = 82 + i * 14; c.setLineWidth(0.8); c.rect(bx * mm, Y(37.2), 4.2 * mm, 4.2 * mm); c.drawString((bx + 5.5) * mm, Y(36), a)
    c.setLineWidth(0.8); c.roundRect(128 * mm, Y(37), 34 * mm, 25 * mm, 2 * mm)
    c.setFont('Helvetica', 7.5); c.setFillColorRGB(*GREY); c.drawCentredString(145 * mm, Y(16.5), 'CODE')
    c.setFillColorRGB(0, 0, 0); c.setFont('Helvetica-Bold', 22); c.drawCentredString(145 * mm, Y(26), code)
    c.setFont('Helvetica', 8.5); c.drawCentredString(145 * mm, Y(33), f'Blatt {blatt}')
    qr(c, f'KORR|STD|{code}|{blatt}', 166 * mm, Y(38), 26 * mm)
    c.setStrokeColorRGB(0.6, 0.6, 0.6); c.setLineWidth(0.6); c.line(20 * mm, Y(42), 202 * mm, Y(42))
    c.setStrokeColorRGB(*LINE); c.setLineWidth(0.8); c.line(158 * mm, Y(45), 158 * mm, Y(282))
    c.setFont('Helvetica', 6.5); c.setFillColorRGB(0.55, 0.62, 0.72); c.drawCentredString(180 * mm, Y(48), 'KORREKTURRAND – freilassen')
    for i in range(23):
        ym = 52 + i * 10
        c.setStrokeColorRGB(*LINE); c.setLineWidth(0.5); c.line(20 * mm, Y(ym), 158 * mm, Y(ym))
        c.setDash(1, 2); c.line(158 * mm, Y(ym), 202 * mm, Y(ym)); c.setDash()
        c.setFont('Helvetica', 6); c.setFillColorRGB(0.55, 0.62, 0.72); c.drawRightString(18 * mm, Y(ym) + 1, str(i + 1))
    c.setFont('Helvetica', 6.8); c.setFillColorRGB(*GREY)
    c.drawCentredString(105 * mm, Y(289), 'Dunkler Kugelschreiber · nur auf den Linien schreiben · Streichungen mit einem Strich · Rückseite frei lassen')
    c.drawCentredString(105 * mm, Y(292.5), f'Code {code} · Blatt {blatt}')

def liste(path, codes):
    c = canvas.Canvas(path, pagesize=A4); c.setTitle('Zuordnungsliste')
    c.setFont('Helvetica-Bold', 14); c.drawString(20 * mm, Y(20), 'Zuordnungsliste – nur für die Lehrkraft')
    c.setFont('Helvetica', 10); c.drawString(20 * mm, Y(28), 'Kurs: ______________   Klausur: ______________   Datum: ______________')
    c.setFillColorRGB(0.65, 0, 0); c.setFont('Helvetica-Bold', 9)
    c.drawString(20 * mm, Y(35), 'Nicht scannen, nicht hochladen. Bleibt bei der Lehrkraft. Codes bei jeder Klausur neu verteilen.')
    c.setFillColorRGB(0, 0, 0); c.setFont('Helvetica-Bold', 9); y = 44
    for x, t in [(20, 'Code'), (38, 'Name'), (120, 'Blätter'), (140, 'Bemerkung')]: c.drawString(x * mm, Y(y), t)
    c.setLineWidth(0.4)
    for code in codes:
        y += 6.7; c.line(20 * mm, Y(y + 1.8), 195 * mm, Y(y + 1.8)); c.setFont('Helvetica-Bold', 10.5); c.drawString(20 * mm, Y(y), code)
    c.save()

if __name__ == '__main__':
    mode, out = sys.argv[1:3]
    if mode == 'master':
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 35; nb = int(sys.argv[4]) if len(sys.argv) > 4 else 6
        rnd = random.Random(int(sys.argv[5]) if len(sys.argv) > 5 else None)
        codes = [f'{x:02d}' for x in sorted(rnd.sample(range(10, 100), n))]
        c = canvas.Canvas(out, pagesize=A4); c.setTitle('Klausurbögen Englisch (Master)')
        for code in codes:
            for b in range(1, nb + 1): sheet(c, code, b); c.showPage()
        c.save(); print(','.join(codes))
    else:
        liste(out, sys.argv[3].split(','))

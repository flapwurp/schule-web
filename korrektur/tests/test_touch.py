import asyncio, sys, io
from playwright.async_api import async_playwright
import os
URL = 'file://' + os.path.abspath(sys.argv[1])
OUT = os.path.dirname(os.path.abspath(sys.argv[1]))
ok = lambda c, m: print(('OK   ' if c else 'FEHL ') + m)

PEN = """([sel, pts, type]) => { const svg = document.querySelector(sel), r = svg.getBoundingClientRect(), vb = svg.viewBox.baseVal;
  const ev = (t, p) => svg.dispatchEvent(new PointerEvent(t, { bubbles:true, cancelable:true, pointerId: 7, pointerType: type, button:0, buttons:1,
     clientX: r.left + p[0] * r.width / vb.width, clientY: r.top + p[1] * r.height / vb.height }));
  ev('pointerdown', pts[0]); pts.slice(1).forEach(p => ev('pointermove', p)); ev('pointerup', pts[pts.length-1]); }"""

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={'width': 1180, 'height': 820}, has_touch=True, accept_downloads=True)
        pg = await ctx.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(URL); await pg.wait_for_timeout(500)
        st = lambda: pg.evaluate("JSON.parse(localStorage.getItem(STORE))")
        # 1 Maus: Vorschlag anklicken -> Schnellmenü -> Annehmen
        await pg.click('.mk[data-id="11-01"] line.hit', force=True)
        ok(await pg.locator('.qpop[data-id="11-01"]').count() == 1, 'Schnellmenü erscheint per Klick')
        await pg.click('.qpop button[data-q="acc"]')
        s = await st(); ok(s['codes']['11']['dec']['11-01']['status'] == 'acc', 'Annehmen per Schnellmenü')
        ok(await pg.locator('.qpop[data-id="11-02"]').count() == 1, 'springt zum nächsten offenen Vorschlag')
        # 2 Tastatur
        await pg.keyboard.press('x'); s = await st(); ok(s['codes']['11']['dec']['11-02']['status'] == 'rej', 'Verwerfen per Taste X')
        # 3 Finger-Tipp (Touch) auf Vorschlag
        await pg.keyboard.press('Escape')
        box = await pg.locator('.mk[data-id="11-05"] line.hit').bounding_box()
        await pg.touchscreen.tap(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
        ok(await pg.locator('.qpop[data-id="11-05"]').count() == 1, 'Schnellmenü per Fingertipp')
        await pg.click('.qpop button[data-q="more"]'); await pg.click('.qpop .signs button[data-s="W"]')
        await pg.fill('.qpop .qcorr', 'do not'); await pg.press('.qpop .qcorr', 'Enter')
        s = await st(); d = s['codes']['11']['dec']['11-05']; ok(d['sign'] == 'W' and d['corr'] == 'do not' and d['status'] == 'acc', 'Ändern + Enter übernimmt')
        # 4 Unterstreichen mit Stift (wellig), Zeichen antippen
        await pg.click('#tools button[data-m="sprache"]')
        L = await pg.evaluate("D.codes[0].pages[0].lines")
        y = L[8] - 2; await pg.evaluate(PEN, ['.page[data-i="0"] svg', [[300, y], [350, y + 5], [420, y - 4], [520, y + 3]], 'pen'])
        s = await st(); own = s['codes']['11']['own']; ok(len(own) == 1 and own[0]['line'] == 8 and own[0]['segs'][0][:2] == [300, 520], 'Stift-Unterstreichung -> Anstreichung Zeile 8')
        ok(await pg.locator('.qpop .signs').count() == 1, 'Zeichenauswahl erscheint')
        await pg.click('.qpop .signs button[data-s="G"]'); await pg.click('.qpop button[data-q="done"]')
        s = await st(); ok(s['codes']['11']['own'][0]['sign'] == 'G', 'Zeichen per Antippen gesetzt')
        # Finger im Unterstreichen-Modus zeichnet nicht
        await pg.evaluate(PEN, ['.page[data-i="0"] svg', [[300, L[10]], [500, L[10]]], 'touch'])
        s = await st(); ok(len(s['codes']['11']['own']) == 1, 'Finger zeichnet nicht (scrollt)')
        # 4b Handschriftliche Positivkorrektur: Stift unterstreicht, Zeichen per Stift antippen, in Schreibfläche schreiben
        await pg.evaluate(PEN, ['.page[data-i="0"] svg', [[200, L[11] - 2], [420, L[11]]], 'pen'])
        await pg.evaluate("""() => { const b = document.querySelector('.qpop .signs button[data-s="W"]');
          b.dispatchEvent(new PointerEvent('pointerdown', { bubbles:true, pointerType:'pen' })); b.click(); }""")
        ok(await pg.locator('.qpop .qpad canvas').count() == 1, 'Schreibfläche erscheint nach Stift-Tipp')
        await pg.evaluate("""() => { const cv = document.querySelector('.qpop .qpad canvas'), r = cv.getBoundingClientRect();
          const ev = (t, x, y) => cv.dispatchEvent(new PointerEvent(t, { bubbles:true, cancelable:true, pointerId:9, pointerType:'pen', clientX:r.left + x, clientY:r.top + y }));
          ev('pointerdown', 20, 40); [[40, 65], [60, 40], [80, 65], [100, 40]].forEach(p => ev('pointermove', ...p)); ev('pointerup', 100, 40);
          ev('pointerdown', 130, 50); ev('pointermove', 170, 50); ev('pointerup', 170, 50); }""")
        s = await st(); o = s['codes']['11']['own'][-1]
        ok(o['sign'] == 'W' and o.get('cink') and len(o['cink']['s']) == 2, 'Handschrift gespeichert (2 Striche)')
        ok(await pg.locator('.qpop .qpad canvas').count() == 1, 'Schreibfläche bleibt nach dem Strich offen')
        ok(await pg.locator(f'.mk[data-id="{o["id"]}"] path.cink').count() == 1, 'Handschrift in der Randspalte')
        await pg.click('.qpop button[data-q="done"]')
        await pg.click('.mk[data-id="11-07"] line.hit', force=True); await pg.click('.qpop button[data-q="more"]')
        ok(await pg.locator('.qpop .qcorr').count() == 1, 'mit Maus: Tippfeld statt Schreibfläche')
        await pg.click('.qpop button[data-q="pen"]'); ok(await pg.locator('.qpop .qpad').count() == 1, 'Umschalten auf Schreibfläche')
        await pg.click('.qpop button[data-q="kbd"]'); await pg.keyboard.press('Escape')
        # 5 Freihand, Radierer, Rückgängig
        await pg.click('#tools button[data-m="ink"]')
        await pg.evaluate(PEN, ['.page[data-i="0"] svg', [[1000, 400], [1040, 380], [1080, 420], [1120, 390]], 'pen'])
        await pg.evaluate(PEN, ['.page[data-i="0"] svg', [[1000, 600], [1100, 650]], 'mouse'])
        s = await st(); ok(len(s['codes']['11']['ink']) == 2, 'Freihand mit Stift und Maus')
        await pg.click('#tools button[data-m="erase"]')
        await pg.evaluate(PEN, ['.page[data-i="0"] svg', [[1050, 625]], 'pen'])
        s = await st(); ok(len(s['codes']['11']['ink']) == 1, 'Radierer löscht Strich')
        await pg.keyboard.press('Control+z'); s = await st(); ok(len(s['codes']['11']['ink']) == 2, 'Strg+Z stellt wieder her')
        ok(await pg.locator('.page[data-i="0"] path.ink:not(#tmpInk)').count() == 2, 'Freihand wird angezeigt')
        # 6 Export mit eingebrannter Freihand
        await pg.keyboard.press('Escape')
        async with pg.expect_download() as dl:
            await pg.click('#pdfMenu summary'); await pg.click('#pdfOne')
        f = await (await dl.value).path(); data = open(f, 'rb').read()
        i = data.index(b'\xff\xd8'); j = data.index(b'\xff\xd9', i)
        from PIL import Image
        im = Image.open(io.BytesIO(data[i:j + 2])).convert('RGB'); px = im.getpixel((2 * 1060, 2 * 400 + 0))
        reds = sum(1 for x in range(2 * 995, 2 * 1125, 4) for yy in range(2 * 370, 2 * 430, 4) if (lambda c: c[0] > 110 and c[1] < 60)(im.getpixel((x, yy))))
        ok(len(data) > 50000 and reds > 5, f'PDF-Export ({len(data)//1000} kB), Freihand eingebrannt ({reds} rote Proben)')
        # 7 Reload: Stand bleibt
        await pg.reload(); await pg.wait_for_timeout(400)
        ok(await pg.locator('.page[data-i="0"] path.ink:not(#tmpInk)').count() == 2, 'Freihand nach Neuladen noch da')
        await pg.screenshot(path=OUT + '/quer.png')
        # 8 Hochformat
        await pg.set_viewport_size({'width': 820, 'height': 1180}); await pg.wait_for_timeout(200)
        await pg.click('.mk[data-id="11-03"] line.hit', force=True); await pg.wait_for_timeout(200)
        await pg.screenshot(path=OUT + '/hoch.png')
        ok(not errs, 'keine JS-Fehler ' + '; '.join(errs))
        await b.close()
asyncio.run(main())

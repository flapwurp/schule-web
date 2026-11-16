# Korrektur-Arbeitsfläche

Werkzeuge für die KI-gestützte **sprachliche Vorkorrektur** handschriftlicher Englisch-Klausuren. Die KI schlägt Anstreichungen vor; die Lehrkraft prüft jeden Vorschlag, ergänzt eigene, vergibt alle Punkte und die Note.

> **Datenschutz:** Dieses Repository enthält ausschließlich Programmcode, Anweisungen und Regeln – **keine Schülerarbeiten, Scans, Vorkorrektur-PDFs oder Korrekturstände**. Solche Dateien gehören nicht hierher (siehe `.gitignore`).

## Ordner

| Ordner | Inhalt |
| --- | --- |
| `arbeitsflaeche/` | Die Arbeitsfläche als einzelne Offline-HTML-Datei. Im Browser öffnen (Chrome, Edge, Firefox), Vorkorrektur-PDF hineinziehen. Es wird nichts hochgeladen. |
| `werkzeuge/` | `kw.py` (Scan einlesen, Wortfelder, Vorschläge, Vorkorrektur-PDF bauen), `bogen.py` (Klausurbögen mit Code, QR und Ankerpunkten), `resolve.py` (Hilfsfunktion), `korrekturprofil.md` (Korrekturregeln). |
| `tests/` | `mkdata.py` (Demo mit synthetischen Daten), `test_touch.py` (Browser-Tests: Maus, Touch, Stift, Export), `patch_handschrift.py`, `patch_layout.py` (bereits angewendete Einmal-Patches, nur zur Nachvollziehbarkeit). |
| `ais-version/` | Weiterentwicklung für **AIS.chat** (Landeslösung, Betrieb in der EU): Die Arbeitsfläche übernimmt Ausrichten, Zuordnen und Einlesen selbst; AIS.chat liefert nur Abschrift und Korrekturliste als Text. Siehe `ais-version/README.md`. |

## Versionen

| Version | Stand | Beschreibung |
| --- | --- | --- |
| `v1.0` | 20.10.2026 | Stand des Piloten: Arbeitsfläche mit Prüfen / Bewertung / Förderung, Export mit Förderblatt; Vorkorrektur über Claude und `kw.py`. |

## Neue Gestaltung (Branch `arbeitsflaeche-design`, 16.11.2026)

Nur Oberfläche, Funktionen und Datenformat unverändert (alle Browser-Tests in `tests/test_touch.py` laufen für v1.0 und AIS-Version). Gespeicherte Korrekturstände bleiben gültig.

- **Farben:** Korrekturrot nur noch auf dem Scan. Bedienelemente in Königsblau, Grün = angenommen/fertig, Warnrot nur für Löschen und Zurücksetzen. Ermessensfragen sind auf dem Scan jetzt violett (wie in der Liste), offene Vorschläge blasser als angenommene.
- **Kopfzeile:** Klausurtitel vorne, Kursleiste mit einem Chip pro Code und Fortschrittsring (fertige Codes grün), feste Speicheranzeige. „Datei“-Menü bündelt Öffnen, Sichern, Laden; Zurücksetzen steht abgesetzt in einem roten Bereich.
- **Werkzeugleiste:** Werkzeuge als zusammenhängende Gruppe mit Icons, Zoom mit −/+ und Prozentwert (startet passend zur Fensterbreite), Anzeige-Optionen und Legende unter „Ansicht“. „Finger zeichnet“ erscheint nur auf Touch-Geräten.
- **Prüfen:** Fortschrittsbalken; Entscheiden vor allem im Schnellmenü an der Stelle, die Seitenleiste zeigt Status und klappt Zeichen/Positivkorrektur/Fehlermuster bei Bedarf auf. Liste nach Blatt gruppiert, mit Status-Icons; Filter mit Anzahl. Ist ein Code fertig, bietet die Seitenleiste „Weiter mit Code …“ und „Zur Bewertung“ an.
- **Bewertung:** Teile aufklappbar, Teilsumme und Zahl der offenen Kriterien im Kopf, leere Felder grau.
- **Förderung:** Empfehlungen mit ★ statt grünem Rand, doppelte Titel entfernt.
- **Start:** Ablauf in drei Schritten, zuletzt bearbeitete Klausuren mit Fortschritt.
- **Hilfe:** Knopf „?“ in der Kopfzeile (oder Taste ?) mit Kurzanleitung, iPad-Hinweisen und Tastenkürzeln.
- **iPad hochkant:** Seitenleiste als Blatt von unten (Griff antippen = größer/kleiner, ziehen = Höhe frei), Werkzeuge nur als Icons.

## Touch- und Stift-Bedienung (Prototyp, 15.11.2026)

Umgezogen aus dem privaten Repo `schule` (dort Stand bis Branch `touch-prototyp`). Online testen: `korrekturtest/` in diesem Repo, z. B. https://flapwurp.github.io/schule-web/korrekturtest/demo.html (nur synthetische Daten).

Eine Version für Maus/Tastatur **und** iPad mit Stift oder Finger (gilt für v1.0 und die AIS-Version):

- **Antippen/Klicken** eines Vorschlags öffnet ein Schnellmenü direkt an der Stelle: ✓ Annehmen, ✗ Verwerfen, „Ändern“ (Zeichen, Positivkorrektur, Lücke). Nach dem Entscheiden springt es zum nächsten offenen Vorschlag.
- **Werkzeugleiste** über dem Scan: Auswählen · Unterstreichen · Freihand · Radierer · Rückgängig.
  - *Unterstreichen:* Strich unter das Wort (darf wellig sein) → gerade Unterstreichung auf der Zeile, Korrekturzeichen antippen, Positivkorrektur optional **handschriftlich in die Schreibfläche** im Schnellmenü; sie erscheint als Handschrift in der Randspalte („W (…)“) und im Export. Mit der Maus erscheint stattdessen ein Tippfeld; ✎ / ⌨ schaltet um. Handschriftliche Positivkorrekturen sind im Korrekturstand nur als „handschriftlich“ erkennbar, nicht als Text.
  - *Freihand:* freie Anmerkungen mit Stift/Maus. Werden gespeichert, im Korrekturstand gesichert und ins Export-PDF eingebrannt. Sie zählen **nicht** für Bewertungshinweise, Förderblatt und Lernprotokoll.
- **Stift zeichnet, Finger scrollt**, zwei Finger zoomen. Ohne Stift: „Finger zeichnet“ anhaken.
- Tastatur wie bisher, neu: `F` Freihand, `Strg/Cmd+Z` Freihand rückgängig.
- Größere Bedienflächen bei Touch-Geräten, Layout fürs Hochformat (Seitenleiste unten).
- Export gibt Bildspeicher nach jeder Seite frei (iPad-Safari-Limit).
- Für die Nutzung auf iPads muss die Seite gehostet sein (z. B. GitHub Pages); lokale HTML-Dateien öffnen dort nicht. Tipp: „Zum Home-Bildschirm“ hinzufügen, dann löscht Safari den gespeicherten Stand nicht nach 7 Tagen Nichtnutzung.

## Ablauf (v1.0)

1. Klausur auf Klausurbögen schreiben lassen (`werkzeuge/bogen.py`), Stapel scannen.
2. Vorkorrektur erzeugen (`werkzeuge/kw.py`, Schritte siehe Docstring) → Vorkorrektur-PDF.
3. Vorkorrektur-PDF in `arbeitsflaeche/arbeitsflaeche.html` öffnen, prüfen, bewerten, PDF exportieren.
4. Korrekturstand sichern (Menü „Korrekturstand“) und für Regel-Updates des Korrekturprofils zurückgeben.

Nur sprachliche Korrektur. Keine Inhaltskorrektur, keine Punkt- oder Notenvorschläge durch die KI.

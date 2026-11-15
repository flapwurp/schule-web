# AIS.chat-Version (Prototyp v0.1)

Ziel: Vorkorrektur ohne US-Dienst. Das Sprachmodell läuft über **AIS.chat** (Landeslösung NRW, Modelle in der EU, AV-Vertrag über die Schule). Alles andere läuft lokal im Browser.

## Benutzung

`arbeitsflaeche_ais.html` im Browser öffnen (Chrome, Edge, Firefox) → **„Mit AIS.chat vorbereiten …“**:

1. **Scan einlesen:** Sammelscan (PDF in Farbe/Graustufen, oder JPG/PNG) wählen, optional die Klausurdatei (Erwartungshorizont und Notenschlüssel als JSON). Seiten werden über die Ankerpunkte entzerrt und per QR den Codes zugeordnet.
2. **Bilder als ZIP herunterladen:** Standard sind Zeilenstreifen (nur beschriebene Zeilen, links mit „B1 Z6“ beschriftet, 16 Zeilen je Bild, 300 dpi), ein Ordner je Nachricht (höchstens 5 Bilder, mehrere Codes möglich). Im Assistenten „Abschrift“ (`assistenten/A_Assistent_Abschrift.txt`) je Ordner eine Nachricht senden. Halbseiten gibt es weiter als Option (Anweisung `A_Assistent_Abschrift_Halbseiten.txt`).
3. **Antworten einfügen:** alle Abschriften in das linke Feld, alle Fehlerlisten in das rechte. „kopieren“ liefert die Abschrift je Code sauber für den Assistenten „Korrektur“. Die Tabelle meldet je Code, was übernommen wurde und was nicht passt.
4. **In der Arbeitsfläche öffnen** – oder als Vorkorrektur-PDF speichern (lässt sich auch in v1.0 öffnen).

Eingefügte Texte bleiben im Browser gespeichert (je Klausur). Nach einem Neustart genügt es, den Scan erneut zu wählen.

Bauen: `python3 build.py vendor/jsQR.js src/foerderpool.json src/standard_klausur_EF.json` (setzt v1.0 + `src/` zusammen; v1.0 bleibt unverändert).

### Was das Programm selbst prüft
- Fehlerzeilen, deren Wörter nicht in der Abschrift stehen, werden nicht übernommen und gemeldet.
- Steht die Wortfolge eine Zeile darüber oder darunter, wird sie dorthin gesetzt (Meldung in der Tabelle).
- Vorgeschlagener fehlender Punkt vor einem großgeschriebenen Wort oder am Absatzende → „unsicher“ (oft nur ein übersehener, angeklebter Punkt).
- Wörter mit [?] → „unsicher“.
- **Vermutete Lesefehler** (Schalter, standardmäßig an): Z-Vorschläge, die einen Punkt in ein Komma verwandeln, obwohl danach klein weitergeschrieben wird („parents. friends“ → „parents,“), und Z/R-Vorschläge an Zeilenangaben („(l. 1).“) werden nicht übernommen und in der Tabelle aufgelistet. Ausgeschaltet kommen sie als „unsicher“ in die Arbeitsfläche.
- Passen Wörter und Schriftbild einer Zeile nicht zusammen, werden die Wortgrenzen geschätzt (Meldung „geschätzt“).

## Ablauf (Konzept)

1. **Scan vorbereiten (Arbeitsfläche, lokal):** Scan-PDF öffnen, Seiten über die Ankerpunkte ausrichten, per QR den Codes zuordnen, Bildausschnitte für den Upload erzeugen (halbe Seiten, 300 dpi).
2. **Abschrift (AIS.chat, Assistent A):** Bilder hochladen → buchstabengetreue Abschrift als Text (`### CODE / ### TEXT`).
3. **Korrektur (AIS.chat, Assistent B):** Abschrift einfügen → Fehlerliste als Text (`### FEHLER`).
4. **Einlesen (Arbeitsfläche, lokal):** Antworten einfügen; die Arbeitsfläche ordnet jedes Wort seiner Stelle im Scan zu und legt die Anstreichungen als Ebene über die Handschrift.
5. Prüfen, bewerten, exportieren wie in v1.0.

## Stand

| Teil | Stand |
| --- | --- |
| `assistenten/` | Anweisungen für die AIS.chat-Assistenten (Abschrift, Korrektur) und Testprofil. In Erprobung. |
| `abgleich.py` | Prototyp: vergleicht zwei Abschriften desselben Codes und listet abweichende Wörter. |
| `ais_import.py` | Python-Variante von Schritt 4 (für Tests mit `werkzeuge/kw.py`). |
| `arbeitsflaeche_ais.html` | **Prototyp v0.1** (05.11.2026): Schritte 1–4 im Browser, danach Arbeitsfläche v1.0. Getestet mit dem Dummy-Scan EF-E-K1 und echten AIS.chat-Antworten. |
| `src/` | Quellteile des Vorbereitungsmoduls (`prep.js` Logik, `prep_ui.js` Oberfläche, `prep.html`, `prep.css`), Förderpool, Standard-Bewertung. |
| `vendor/` | jsQR (QR-Erkennung, Apache-2.0). |

## Testergebnisse

- **Test 1 (05.11.2026, GPT-5.5, ganze Seiten 150 dpi):** Format fehlerfrei, Tokenverbrauch gering. Abschrift glättet Fehler (z. B. „Its“ → „It's“, „handy“ → „phone“) und übersieht Satzzeichen; Korrektur schlägt Semikolons vor.
- **Test 2 (05.11.2026, nur Abschrift, halbe Seiten 300 dpi, Code 71):** deutlich besser als Test 1. Claude Sonnet 5.5 und GPT-5.5 lesen „handy“, „fidelity“, „calls“, „There“ jetzt richtig. Sonnet 5.5: genauer bei Satzzeichen und Anführungszeichen, glättet aber vereinzelt („metapher“ → „metaphor“). GPT-5.5: behält Rechtschreibfehler, lässt öfter Satzzeichen weg. Beide markieren unsichere Wörter nur in den Hinweisen statt mit [?]. Gemini 3.5 Flash Lite: Anweisung ignoriert (Fehlerliste statt Abschrift, erfundene Wörter) – ungeeignet.
- **Grenze:** AIS.chat nimmt höchstens 5 Bilder **pro Nachricht** an. Mehrere Nachrichten im selben Chat funktionieren: Sonnet 5.5 liefert dann für alle Codes nacheinander je einen eigenen Block.
- **Test 3 (05.11.2026, Stapel, Sonnet 5.5, Codes 23/36/58/71, halbe Seiten 300 dpi):** 98,8–99,7 % Übereinstimmung mit der Referenz; mehrere Abweichungen waren Fehler der Referenz. Setzt [?] jetzt auch im Text. Verbleibende Schwächen: winzige Punkte direkt am letzten Buchstaben werden übersehen (Code 58: 3×), „metapher“ wird trotz ausdrücklichem Beispiel zu „metaphor“ geglättet.
- **Korrektur aus Abschrift (Code 71, Sonnet 5.5):** 38 von 45 Referenz-Anstreichungen getroffen; 2 Fehlalarme gingen auf Lesefehler der Abschrift zurück; 1 berechtigte Ergänzung (Komma nach Nebensatz). Übersehen u. a. „become fidelity“, „a better self-esteem“, „speaks with“. Markierungen teils zu breit („the life“ → „-“). Anweisung B daraufhin präzisiert.
- **Test 4 (05.11.2026, Stapel, GPT-5.5, dieselben 4 Codes):** 97,7–99,4 %. Übersieht häufiger angeklebte Punkte und Kommas („old.“, „hard.“, „interests.“, „statement,“), glättet ebenfalls („accesible“ → „accessible“) und erfindet vereinzelt Fehler („media“ → „medias“). Sonnet 5.5 bleibt Erstleser.
- **Abgleich Sonnet/GPT (4 Codes):** 18 Abweichungen bei 1.720 Wörtern (ca. 1 %), darunter „metapher“, „accesible“, „medias“. Beide übersehen gemeinsam „independent.“ (Code 58).
- **Korrektur Code 58 (Sonnet 5.5, eigene neue Abschrift):** 24 von 35 Referenz-Anstreichungen getroffen, aber 11 Fehlalarme aus Lesefehlern dieser Abschrift („Eriksan“, „Comes“, „woking“, „sameone“, „post“), die in der Stapel-Abschrift alle nicht vorkommen; 1 grammatischer Fehlalarm („gives“ → „give“). Die Qualität der Korrektur hängt direkt an der Abschrift.
- **Doppelte Abschrift (`abgleich.py`):** Vergleich Sonnet 5.5 / GPT-5.5 für Code 71: 12 Abweichungen bei 303 Wörtern, darunter alle bekannten Problemstellen („metapher“, „2026“, „role“, Zeilenangaben). Kandidat für den Regelablauf: abweichende Wörter gelten als unsicher.
- **Prototyp v0.1 (05.11.2026):** Scan-Einlesen im Browser dauert für 14 Seiten etwa 6 Sekunden. Wortfelder stimmen mit `kw.py` überein (212 von 213 Zeilen gleiche Feldzahl, mittlere Abweichung 2 px). Korrekturen, die auf einer anderen Abschrift beruhen, werden wie vorgesehen abgewiesen.
- **Durchlauf Rob (05.11.2026, alle 5 Codes, alle Vorschläge angenommen):** Bei der Zeichensetzung waren rund 15 von 24 Anstreichungen falsch. Ursachen: (1) Kommas als Punkte gelesen, danach „korrigiert“ (Code 23 allein 7×, Code 71 2×); (2) angeklebte Punkte übersehen (Code 58: 2×); (3) Zeilenangaben „(l. 1).“ (3×). Dazu uneinheitlich: Kommas nach Einleitungswörtern („Furthermore“, „All in all“) mal angestrichen, mal nicht. Maßnahmen: Filter „vermutete Lesefehler“, Regel in A (Komma oder Punkt, [?]), Regeln in B (Punkt mit Kleinschreibung danach, Zeilenangaben).
- **Test Zeilenstreifen 16 (06.11.2026, Sonnet 5.5, 5 Codes, 16 Bilder in 4 Nachrichten statt 25 in 6):** alle Zeilenbezeichnungen richtig; Übereinstimmung so gut wie bei Halbseiten (Code 23 fehlerfrei, angeklebte Punkte in Code 58 jetzt erkannt). Verbliebene Lesefehler: „confusion. Because“ statt „, because“ (Code 36), „metapher“ → „metaphor“ (Code 71), einzelne Satzzeichen am Wortende (Code 44). → Zeilenstreifen 16 als Standard.
- **Test kombinierter Assistent AB (08.11.2026, Sonnet 5.5, Zeilenstreifen 16, 5 Codes):** Abschrift so gut wie mit getrenntem Assistenten (98,3–99,8 %), „metapher“ diesmal richtig (nachdem das Wort aus den Beispielen der Anweisung entfernt wurde). Fehlerliste: 146 von 147 Zeilen zuordenbar; 120 von 159 Referenz-Anstreichungen getroffen (75 %), Lücken v. a. bei Kommas nach Einleitungswörtern, Verlaufsform („is using“), Artikel vor Unzählbarem („a higher self-esteem“), „way → far“. 19 Zeilen mit Fehlermuster statt Zeichen (wird jetzt automatisch umgesetzt), eine leere Korrektur („metaphor → metaphor“, wird verworfen), zwei Rücknahmen nur in den Hinweisen (Anweisung präzisiert).
- **Abgleich mit der Opus-Vorkorrektur vom 20.10.2026 (08.11.2026):** Opus 155, AIS (Sonnet 5.5, kombiniert) 143 Anstreichungen, 109 gemeinsam. Opus fand zusätzlich v. a. Kommas nach Einleitungswörtern (~16), Verlaufsform, Präpositionen, Relativsatz-Kommas, Artikel (~12 klare Fehler) und Stilvorschläge (~12). AIS zusätzlich: ~10 Fehlalarme aus Lesefehlern bzw. unsinnige Vorschläge, ~10 Register-Vorschläge (Ermessen), einige berechtigte Ergänzungen. Stark bei Code 71 und 44, schwach bei 36 und 58. Die frühere Angabe „75 % Treffer“ bezog sich auf diese Opus-Vorkorrektur als Referenz.

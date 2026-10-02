# Prüfbericht v0.1.0

Stand: 02.10.2026.

## Ergebnis

**32 Tests erfolgreich** mit Home Assistant Core 2026.9.4, Python 3.14.7, pycognito 2024.5.1 und pytest-homeassistant-custom-component 0.13.367. Python-Syntaxprüfung, JSON-Parsing, Übersetzungsabgleich und ZIP-Strukturprüfung erfolgreich.

## Geprüft

- Config Flow mit Benutzername/Passwort, erfolgreiche Einrichtung und Vermeidung doppelter Konten.
- Einrichtungsfehler für ungültige Anmeldung, unerreichbare API und fehlende Geräte.
- Erneute Anmeldung aktualisiert Zugangsdaten; anderes Konto wird zurückgewiesen.
- Home Assistant lädt die Sensorplattform und erzeugt 15 Sensoren aus den Referenzmetadaten. Temperatur und Einheit erscheinen korrekt; optionale Sollwertsensoren bleiben standardmäßig deaktiviert.
- Offline-/Fehlerzustände machen Sensoren nicht verfügbar; erfolgreiche Wiederherstellung liefert wieder Werte.
- Neue Parameter werden automatisch hinzugefügt; verschwundene Parameter werden nicht verfügbar.
- Unload der Integration und Schließen des Cognito-Clients.
- SRP-Handshake mit simuliertem Cognito einschließlich Challenge-Session, Token-Cache, Refresh und erneuter Anmeldung nach abgelaufenem Refresh-Token.
- Parallele Token-Anfragen erzeugen keine doppelten Refreshes für denselben abgelehnten Token.
- HTTP 401 löst genau einen Refresh-/Wiederholungsversuch aus; dauerhafte Ablehnung endet mit Authentifizierungsfehler.
- Mehrseitige Geräteerkennung mit dynamischen IDs, leere Geräteliste und Schutz vor wiederholten Seiten.
- GraphQL-Syntax der drei lesenden Queries, Ablehnung von GraphQL-Fehlern und falschen Geräte-IDs.
- Veränderte Parameterreihenfolge, anonyme Live-Antworten, ungültige Zahlen, Nullwerte und Sollwertänderung 26 → 26,5 anhand vollständig synthetischer Beispieldaten.
- Keine Service-Sequenzen in Abfragen und keine schreibenden Plattformen oder Dienste geladen.

## Praktische Rückmeldung

Der Projektinhaber hat Einrichtung und Anzeige der Poolwerte mit der v0.1 bestätigt. Die zunächst beobachtete Fahrenheit-Anzeige ließ sich über die Einheiteneinstellungen von Home Assistant auf Celsius umstellen.

## Nicht geprüft

Kein durch die automatisierte Testsuite ausgeführter Cloud-Login. Token-Erneuerung im Dauerbetrieb, weitere Anlagen und Langzeitstabilität stehen noch aus. Cognito und GraphQL sind in den automatisierten Tests simuliert. Die SRP-Kryptografie stammt aus pycognito und wurde hier nicht unabhängig kryptografisch auditiert. MFA und zusätzliche Login-Challenges werden ausdrücklich als nicht unterstützt behandelt.

Die API-Felder, der Cognito-Pool, der Endpunkt und die Verwendung des Access-Tokens wurden in der öffentlich ausgelieferten iXfield-Web-App geprüft. Das garantiert keine zukünftige API-Kompatibilität. Der erste erfolgreiche Einsatz wurde vom Projektinhaber bestätigt; weitere Anlagen sind noch zu prüfen.

Die öffentlichen Test-Fixtures sind vollständig künstlich erzeugt und enthalten keine Messwerte aus einer realen Anlage. Originalaufzeichnungen, Web-App-Dateien, Zugangsdaten und Arbeitsumgebung sind nicht im ZIP enthalten.

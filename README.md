# iXmanager für Home Assistant – v0.1.0

Inoffizielle, lesende Custom Integration für Pool-Systems / iXmanager / iControlPro. Anmeldung über das iXfield-Konto; keine lokale Verbindung zur Poolsteuerung erforderlich. Die Cloud muss erreichbar sein.

## Installation

1. ZIP entpacken.
2. Den enthaltenen Ordner `custom_components/ixmanager` nach `/config/custom_components/ixmanager` kopieren. Anschließend muss `/config/custom_components/ixmanager/manifest.json` existieren. Falls `custom_components` fehlt, den Ordner erstellen.
3. Home Assistant vollständig neu starten.
4. **Einstellungen → Geräte & Dienste → Integration hinzufügen → iXmanager** öffnen.
5. Benutzername/E-Mail und Passwort des iXfield/iXmanager-Kontos eingeben.

Home Assistant installiert die Python-Abhängigkeit automatisch; beim ersten Start ist Internetzugriff nötig. Keine YAML-Einträge, AWS-Zugangsschlüssel oder Geräte-IDs eingeben. Eine Installation über HACS als benutzerdefiniertes Repository ist ebenfalls vorgesehen; siehe unten. Das Paket richtet sich an aktuelle Home-Assistant-Versionen; automatisiert getestet mit Core 2026.9.4 / Python 3.14. Ältere Versionen sind nicht geprüft.

## Installation über HACS

1. In HACS das Menü **Benutzerdefinierte Repositories / Custom repositories** öffnen.
2. `https://github.com/Nico82x/home-assistant-ixmanager` eintragen und als Typ **Integration** wählen.
3. **iXmanager** herunterladen und Home Assistant neu starten.
4. Unter **Einstellungen → Geräte & Dienste → Integration hinzufügen → iXmanager** anmelden.

[Repository in HACS öffnen](https://my.home-assistant.io/redirect/hacs_repository/?owner=Nico82x&repository=home-assistant-ixmanager&category=integration)

Dieses Projekt ist nicht im HACS-Standardkatalog gelistet. Die manuelle Installation oben bleibt verfügbar.

## Umfang

- Cognito SRP-Anmeldung (`USER_SRP_AUTH`), Access-Token und Refresh-Token im Arbeitsspeicher.
- Erneuerung 90 Sekunden vor Ablauf; einmaliger neuer Versuch nach HTTP 401/403. Ungültiger Refresh-Token führt zu frischer SRP-Anmeldung. Abgelehnte Zugangsdaten lösen Home Assistants erneute Anmeldung aus.
- Automatische Erkennung aller zugänglichen `POOL`-Geräte über `me.devices`, einschließlich Folgeseiten. Geräte-IDs werden ausschließlich aus der API gelesen.
- Gemeinsame Abfrage alle 60 Sekunden; erneute Geräteerkennung alle 15 Minuten. Neue Geräte und Messwerte werden automatisch ergänzt.
- Sensoren aus `liveDeviceData.operatingValues`: im gelieferten Beispiel 15 aktuelle Werte, darunter Wasser-/Rücklauf-/Raumtemperatur, pH, Redox, Chemikalienvorrat, WLAN-Signal, Wärmepumpenleistung und Betriebsmodi. Leere Werte erscheinen als unbekannt.
- Zusätzliche **lesende Sollwertsensoren** für `showDesired` sind standardmäßig deaktiviert; bei Bedarf in der Entitätsverwaltung aktivieren.
- Einheiten und Dezimalstellen aus den Metadaten. pH und Redox haben im Referenz-JSON keine Einheit; deshalb wird dort keine Einheit erfunden. Die Redoxzahl bleibt sichtbar.
- Enum-Zustände behalten stabile API-Werte wie `HEATING`; das Attribut `value_labels` enthält die deutschen Bezeichnungen.
- Offline-Geräte werden nicht verfügbar. Bei fehlgeschlagener gemeinsamer Abfrage werden alle Sensoren des Kontos nicht verfügbar und nach erfolgreicher Abfrage wiederhergestellt. Entfernte Geräte bleiben in der HA-Geräteregistrierung, ihre Entitäten werden nicht verfügbar.

## API und Architektur

Verifiziert anhand der Nutzeraufzeichnungen und der öffentlichen [iXfield-Web-App](https://www.ixfield.com/) vom 02.10.2026:

- Region: `eu-central-1`
- User Pool: `eu-central-1_jCOzBXuR0`
- Client-ID: `5489vt8bvntn3v95tdt2nngq0r`
- GraphQL: `https://to2gjdst4h.execute-api.eu-central-1.amazonaws.com/prod/`
- Authorization: Bearer **Access-Token**
- `GetUserDevices`, `GetDevice`, `deviceLiveData`

Die aufgezeichnete `deviceLiveData`-Antwort enthält Werte ohne Namen. Die Integration erweitert die Feldauswahl deshalb um die bereits für `GetDevice` verwendeten Namen und Metadaten. Jeder Abruf liefert Namen und Werte gemeinsam; es gibt keine Zuordnung nach festen Array-Indizes. Anonyme oder widersprüchliche Antworten werden abgelehnt. `options` ist ein JSON-Skalar.

`api.py` trennt Cloudzugriff und Authentifizierung; `models.py` normalisiert Daten; `coordinator.py` koordiniert Abfragen; `entity.py` ist die gemeinsame Entity-Basis. Die Module `number.py`, `select.py` und `switch.py` reservieren Erweiterungspunkte, werden aber nicht geladen. `Parameter.future_platform` beschreibt mögliche Typen, erteilt keine Schreibberechtigung.

Die bekannte Mutation `deviceControl(input: {deviceId, name, value})` ist in v0.1 absichtlich nicht implementiert. Es gibt keine schreibenden Dienste, Schalter, Buttons oder Service-Sequenzen. Insbesondere Dosierung, Kalibrierung, Schutz-Reset und Rückspülung werden nicht exponiert. Eine spätere Schreibversion benötigt explizit geprüfte Parameterlisten und Berechtigungsprüfungen; `settable` allein reicht dafür nicht.

## Grenzen und Fehlerbehebung

**Erster Praxistest erfolgreich:** Der Projektinhaber hat Einrichtung und Anzeige der Poolwerte an seiner Anlage bestätigt. Weitere Anlagen, Langzeitbetrieb und automatische Token-Erneuerung im Dauerbetrieb sind noch nicht praktisch verifiziert. Automatisierte Tests verwenden synthetische Beispielantworten und simulierte Cloud-Antworten. Die Cloud-API ist nicht offiziell dokumentiert und kann sich ändern.

- „Anmeldung fehlgeschlagen“: Zugangsdaten in iXfield prüfen. MFA, Geräte-SRP-Challenges, neue Passwörter und zusätzliche Bestätigungen sind in dieser Version nicht implementiert. Eine dauerhaft verpflichtende MFA-Challenge kann die Integration nicht bedienen.
- „Keine Poolgeräte“: Prüfen, ob dasselbe Konto in iXfield Zugriff auf ein Poolgerät hat. Andere Gerätetypen werden nicht importiert.
- „Cloud-API nicht erreichbar“: Internetverbindung und Home-Assistant-Protokoll prüfen. Auch unerwartete API-Strukturen werden so gemeldet; es werden keine kompletten Serverantworten oder Tokens protokolliert.
- Anzeige in Fahrenheit: Unter **Einstellungen → System → Zuhause-Informationen** Celsius bzw. das metrische Einheitensystem wählen. Alternativ die Maßeinheit am Sensor ändern; die Integration liefert Temperaturen in °C.
- Einzelne unbekannte Werte: Die API liefert für einige unbestückte/ungültige Sensoren `null`. Das wird nicht zu 0 umgewandelt.
- Neue Zugangsdaten über die von Home Assistant angebotene erneute Anmeldung eingeben.
- Deinstallation über **Geräte & Dienste → iXmanager → Löschen**, anschließend bei Bedarf den Integrationsordner entfernen und neu starten.

Benutzername und Passwort werden wie üblich in Home Assistants Config Entry gespeichert. Tokens werden nicht dauerhaft gespeichert. Home-Assistant-Backups können Zugangsdaten enthalten. Die Testdaten enthalten ausschließlich künstliche Werte und keine echten Geräte-IDs, Kontakt- oder Adressdaten.

## Entwicklerprüfungen

Im Paket liegen synthetische Fixtures und reproduzierbare Tests. In einer getrennten Python-3.14-Umgebung:

```sh
pip install homeassistant==2026.9.4 pytest-homeassistant-custom-component==0.13.367 pycognito==2024.5.1 graphql-core
python -m pytest tests -q
python -m compileall -q custom_components/ixmanager
```

Getestete Verhaltensweisen und Ergebnis: siehe `VALIDATION.md`. Der `tests`-Ordner muss nicht nach Home Assistant kopiert werden.

Verwendete Entwicklerreferenzen: [Config Flow](https://developers.home-assistant.io/docs/config_entries_config_flow_handler/), [DataUpdateCoordinator](https://developers.home-assistant.io/docs/integration_fetching_data/), [Manifest](https://developers.home-assistant.io/docs/creating_integration_manifest/), [pycognito](https://github.com/pvizeli/pycognito).

## Rückmeldungen und Mitarbeit

Bitte [Fehler melden](https://github.com/Nico82x/home-assistant-ixmanager/issues) und dabei Home-Assistant-Version, Integrationsversion und Controller-Modell nennen. Zugangsdaten, Tokens, Adressen und Geräte-IDs vor dem Teilen entfernen. Pull Requests sind willkommen. Hinweise für lokale Tests stehen in [CONTRIBUTING.md](CONTRIBUTING.md).

## Lizenz und Einordnung

MIT-Lizenz, siehe [LICENSE](LICENSE). Unabhängiges Community-Projekt; keine offizielle Integration oder Unterstützung von Pool-Systems, iXmanager oder iXfield. Produktnamen gehören ihren jeweiligen Rechteinhabern.

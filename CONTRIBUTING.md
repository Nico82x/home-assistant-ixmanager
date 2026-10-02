# Mitarbeit

Python 3.14 verwenden und in einer virtuellen Umgebung installieren:

```sh
python -m pip install -r requirements_test.txt
python -m pytest tests -q
python -m compileall -q custom_components/ixmanager
```

Die Tests benötigen kein Poolkonto. Neue API-Beispiele vorab anonymisieren. Keine Zugangsdaten, Tokens, Adressen oder echten Geräte-IDs einchecken.

v0.1 bleibt lesend. Schreibfunktionen benötigen eine separate Prüfung der Parameter und Berechtigungen. Service-Sequenzen werden nicht automatisch aus Metadaten freigeschaltet.

Bei Änderungen bitte einen Pull Request mit Beschreibung des Problems und der Prüfung öffnen. `manifest.json` und Release-Tag müssen dieselbe Versionsnummer tragen.

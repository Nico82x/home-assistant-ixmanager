# Community und mögliche Core-Aufnahme

## Kurzfristig: Auffindbarkeit

- Öffentliches GitHub-Repository mit Release, README, HACS-Metadaten und Tests.
- Vorstellung im Home-Assistant-Community-Forum mit Link zum Repository, klar als Custom Integration gekennzeichnet.
- Rückmeldungen zu weiteren Controller-Modellen und zum Dauerbetrieb sammeln.

## HACS-Standardkatalog

Vor einer Einreichung müssen die Prüfungen von `hassfest` und `hacs/action` erfolgreich sein. Die aktuellen Anforderungen für Markenbilder und Repository-Metadaten prüfen. Anschließend als Repository-Inhaber einen Pull Request gegen `hacs/default` einreichen. Ein benutzerdefiniertes HACS-Repository ist bereits vorher möglich; eine Aufnahme in HACS ist keine Aufnahme in Home Assistant Core.

Referenz: https://hacs.dev/docs/publish/include/

## Home Assistant Core

Die v0.1 ist noch keine einreichungsfertige Core-Integration. Wesentliche Arbeiten:

- iXmanager-Protokollzugriff aus der Integration in eine eigenständige, gepflegte Python-Bibliothek auf PyPI auslagern, inklusive Quelldistribution und Issue-Tracker.
- Vollständige Config-Flow-Testabdeckung und die anwendbaren Bronze-Anforderungen der Integration Quality Scale nachweisen.
- Aktuelle Core-Konventionen, Formatierung, Typen und Tests anwenden.
- Markenbilder und Dokumentation für home-assistant.io vorbereiten.
- Kleinen, zunächst lesenden Core-Pull-Request zur Prüfung einreichen. Die Aufnahme entscheiden die Home-Assistant-Maintainer.

Referenzen:
- https://developers.home-assistant.io/docs/core/integration/contributing_to_core/
- https://developers.home-assistant.io/docs/development_checklist/
- https://developers.home-assistant.io/docs/core/integration-quality-scale/checklist/

Die Nutzung einer aus der Web-App ermittelten Cloud-API und deren Stabilität müssen transparent dokumentiert bleiben.

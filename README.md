# Taxsys leerlingenvervoer voor Home Assistant

[![Open in de Marketplace](https://img.shields.io/badge/Home%20Assistant-Marketplace-41BDF5.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=cardinal808&repository=ha-taxsys&category=integration)
[![Validate](https://github.com/cardinal808/ha-taxsys/actions/workflows/validate.yml/badge.svg)](https://github.com/cardinal808/ha-taxsys/actions/workflows/validate.yml)

Custom integration die de ophaal- en brengtijden van het leerlingenvervoer (groepsvervoer) uit het **Taxsys ouderportaal** haalt en als sensoren in Home Assistant zet. Instellen gaat via de gebruikersinterface; je hoeft geen YAML of `secrets.yaml` aan te passen.

*English: Home Assistant integration for the Dutch Taxsys school-transport parent portal. It reads the pickup and drop-off times of your child's taxi. Install it from Settings → Marketplace.*

Taxsys heeft geen publieke API. De integratie logt in op het ouderportaal (`account.taxsys.nl`) zoals een browser dat doet en leest de tabel *Vervoerschema* uit.

> ⚠️ Onofficieel. Niet gelieerd aan Taxsys / B.S. Automatisering of aan je vervoerder. Als het portaal verandert, kan de integratie stoppen met werken.

## Installatie

### Via de Marketplace (Home Assistant 2026.11 en nieuwer, aanbevolen)

**[Open deze integratie in je Marketplace](https://my.home-assistant.io/redirect/marketplace_repository/?owner=cardinal808&repository=ha-taxsys&category=integration)**

Klik op de link hierboven, of:

1. Ga naar **Instellingen → Marketplace** en zoek *Taxsys leerlingenvervoer*.
2. Staat hij er (nog) niet tussen? Voeg via het menu (⋮) de repository `https://github.com/cardinal808/ha-taxsys` toe als **Integratie**.
3. Installeer en herstart Home Assistant via de melding die de Marketplace geeft.

Updates verschijnen daarna gewoon onder **Instellingen → Updates**.

### Via HACS (Home Assistant ouder dan 2026.11)

Voeg in HACS `https://github.com/cardinal808/ha-taxsys` toe als aangepaste repository van het type **Integratie**, download en herstart. Na de update naar 2026.11 neemt de Marketplace dit automatisch over.

### Handmatig

Kopieer de map `custom_components/taxsys` naar `/config/custom_components/taxsys` en herstart Home Assistant.

## Instellen

**Instellingen → Apparaten en diensten → Integratie toevoegen → Taxsys leerlingenvervoer**, en vul in:

| Veld | Waar vind je het? |
|---|---|
| Bedrijfscode | In de URL van de inlogpagina van je vervoerder, bijv. `https://account.taxsys.nl/taxsys/?page=login&company=G-XXX` → `G-XXX` |
| Klantnummer (klantNr) | Log in en kijk naar de URL van de pagina met het vervoerschema: `...?page=deelnemerMutatie&klantNr=0000000&company=G-XXX` → `0000000` |
| Gebruikersnaam / wachtwoord | Je inloggegevens voor het ouderportaal |

Heb je meerdere kinderen met eigen klantnummers? Voeg de integratie dan per kind toe.

Werkt het inloggen later niet meer (bijv. nieuw wachtwoord), dan vraagt Home Assistant vanzelf om opnieuw in te loggen.

## Entiteiten

Per kind maakt de integratie een apparaat *Taxsys &lt;klantnummer&gt;* met:

| Entiteit (Engels / Nederlands HA) | Inhoud |
|---|---|
| `sensor.taxsys_<klantnr>_pickup` / `_ophalen` | O-tijd (ophaaltijd) van de huidige of eerstvolgende ochtendrit. Schuift 15 min na aankomst door naar de volgende |
| `sensor.taxsys_<klantnr>_home_arrival` / `_thuisbrengen` | A-tijd (aankomst thuis) van de huidige of eerstvolgende middagrit |
| `sensor.taxsys_<klantnr>_rides` / `_ritten` | Aantal ritten op het schema, met de hele lijst in het attribuut `rides` |
| `calendar.taxsys_<klantnr>_schedule` / `_planning` | Alle ritten uit het vervoerschema als afspraken, met status, chauffeur en adressen in de omschrijving |
| `binary_sensor.taxsys_<klantnr>_ride_window` / `_rit_venster` | Aan vanaf 45 min vóór de ophaaltijd tot 15 min na aankomst van een rit. Handig als zichtbaarheidsvoorwaarde voor een dashboardkaart |

De entity-id's hangen af van de taal van je Home Assistant toen je de integratie toevoegde.

De ritsensoren hebben de attributen `date`, `day`, `pickup_time`, `arrival_time`, `origin`, `destination`, `status`, `route`, `driver`, `live_location` en `live_time`. De live-locatie staat er alleen als het portaal die toont tijdens een rit.

## Planning

De kalender `calendar.taxsys_<klantnr>_planning` staat ook in de agenda van Home Assistant (zijbalk → Agenda). Op een dashboard toon je hem met de ingebouwde kalenderkaart, zie [`dashboard/taxsys_planning_card.yaml`](dashboard/taxsys_planning_card.yaml):

```yaml
type: calendar
initial_view: listWeek
entities:
  - calendar.taxsys_0000000_planning
```

## Hoe vaak wordt er ververst?

- **Rond een rit** (45 min vóór ophalen tot 15 min na aankomst): elke 5 minuten.
- **Elke ochtend om 06:30**: één keer, zodat de tijden van de dag bekend zijn.
- **Daarbuiten**: hooguit eens per 3 uur.

Zo blijft het aantal logins op het portaal beperkt.

## Dashboardkaart

[`dashboard/taxsys_card.yaml`](dashboard/taxsys_card.yaml) is een [Mushroom](https://github.com/piitaya/lovelace-mushroom) template card. Hij toont bijvoorbeeld *Ophalen 08:14 · Thuis 14:20 · Jan* en is alleen zichtbaar als het ritvenster aan staat. Vervang `0000000` door je klantnummer en pas de entity-id's aan je taal aan.

## Overstappen van de YAML-versie

Gebruikte je eerder het script en package uit [cardinal808/Taxsys](https://github.com/cardinal808/Taxsys)? Verwijder dan `packages/taxsys.yaml`, `/config/taxsys/taxsys.py` en de `taxsys_*`-regels uit `secrets.yaml`, en voeg deze integratie toe. De nieuwe entity-id's en attribuutnamen zijn anders (Engelse attribuutnamen, bijv. `driver` in plaats van `chauffeur`), dus pas je kaarten en automatiseringen aan.

## Problemen

- **"Inloggen mislukt"**: controleer gebruikersnaam en wachtwoord in het portaal zelf.
- **"Geen vervoerschema gevonden"**: inloggen lukte, maar de pagina had geen schema. Controleer bedrijfscode en klantnummer.
- **Debuglogs**: zet in de integratie *Debuglogboek inschakelen* aan, of voeg toe aan `configuration.yaml`:
  ```yaml
  logger:
    logs:
      custom_components.taxsys: debug
  ```
- Bij een issue helpt een download van de **diagnostiek** (menu van de integratie). Wachtwoord, namen en adressen worden daaruit weggelaten.

## Ontwikkelen

```bash
pip install -r requirements_test.txt
pytest
```

## Licentie

[MIT](LICENSE)

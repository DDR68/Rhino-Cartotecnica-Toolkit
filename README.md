# Rhino-Cartotecnica-Toolkit

Script IronPython 2.7 / RhinoCommon per la cartotecnica
in Rhinoceros 7. Generatori parametrici di fustelle,
utility di prestampa e strumenti di lavoro.

## Struttura
├── packaging/    Generatori parametrici ECMA

├── utilities/    Quotatura, crocini, diagnostica

├── prepress/     Preparazione file per produzione

└── docs/         Guide e documentazione

## Requisiti

- Rhinoceros 7 (Windows)
- IronPython 2.7 (integrato in Rhino 7)
- Nessuna dipendenza esterna — solo RhinoCommon

## Convenzioni generali

Tutti gli script seguono queste regole:

- **IronPython 2.7** puro, niente `rhinoscriptsyntax`, niente f-string
- **RhinoCommon** come unica libreria geometrica
- Layer **"Taglio"** (nero) per le linee di taglio
- Layer **"Cordone"** (rosso) per le linee di cordonatura
- Geometria via `NurbsCurve.Create` per curve spline
- Metadata via `doc.Strings.SetString`
- Unità: millimetri

## Classificazione ECMA

Gli script nella cartella `packaging/` generano fustelle
ispirate alla classificazione ECMA (European Carton Makers
Association). I codici ECMA sono una nomenclatura industriale
non vincolante per tipologie di astucci in cartoncino.
Le implementazioni geometriche (profili linguette, archi,
compensazione spessore) sono originali.

## Licenza

MIT — vedi [LICENSE](LICENSE)

## Autore

[@DDR68](https://github.com/DDR68) — Packaging designer, Toscana

Per segnalazioni o domande, apri una
[Issue](https://github.com/DDR68/Rhino-Cartotecnica-Toolkit/issues).

# LawCodex — Nicaragua (ni)

Nicaraguan legislation as Markdown, from **"Normas Jurídicas de Nicaragua"**, the legislative
database of the Asamblea Nacional (Dirección de Información Legislativa,
http://legislacion.asamblea.gob.ni/normaweb.nsf): the **constitutions**, **codes**, **laws**,
**decree-laws**, **legislative decrees**, **legislative agreements** and **regulations** it
publishes.

Part of [LawCodex](https://github.com/LawCodex): one public repository per jurisdiction.

Retrieved: **2026-10-13**. Language: Spanish (`es`).

Status: **full** for the legislative categories of the database (constitutions, codes, laws, decree-laws, legislative decrees and agreements, regulations); texts as published, consolidated texts only where the Asamblea published them.

## What is covered

| Category (database type) | Directory | Files |
|---|---|---|
| Constituciones Políticas de Nicaragua (historical and current, incl. reforms) | `constituciones/` | 25 |
| Códigos | `codigos/` | 27 |
| Leyes | `leyes/<year>/` | 2,116 |
| Decretos - Ley | `decretos-ley/<year>/` | 1,047 |
| Decretos Legislativos | `decretos-legislativos/<year>/` | 5,462 |
| Acuerdos Legislativos | `acuerdos-legislativos/<year>/` | 8 |
| Reglamentos | `reglamentos/<year>/` | 311 |

`<year>` is the year of publication in La Gaceta, Diario Oficial (`sin-fecha` when unknown).

Each file is the text of the database document (HTML), with the database's header and the
Asamblea's footer removed; LIBRO/TÍTULO/CAPÍTULO/SECCIÓN lines become headings and each
article (`Art. N`, `Artículo N`) a `######` heading. The database holds both original published
texts and later *textos consolidados* / *textos con reformas incorporadas* published in La
Gaceta as separate documents; when a document links to a later published version, the link is
given in the front matter as `latest_version`.

## What is NOT covered

- Executive and administrative norms of the same database (decretos ejecutivos, acuerdos
  presidenciales/ministeriales, resoluciones, normas técnicas…: ~18,000 documents) and
  international instruments.
- No legal status (in force / repealed) is given by the database: `status: unknown`.

## Source

Asamblea Nacional de la República de Nicaragua — Normas Jurídicas de Nicaragua:
view "NJPublicadas" read with Domino `?ReadViewEntries` (XML) by type of norm, each document
fetched with `?OpenDocument`. Each file's `source` is the document URL.

## Copyright

Nicaragua's Ley de Derecho de Autor y Derechos Conexos (Ley N° 312) excludes official texts of a
legislative, administrative or judicial nature from protection; the texts are published by the
Asamblea Nacional for public consultation.

## Regenerate

```
python3 -m venv .venv && .venv/bin/pip install -r scripts/requirements.txt
RAW=/path/to/scratch .venv/bin/python scripts/ni_fetch.py all
```

Up to 3 parallel connections, each at one request per second (the site has no robots.txt).

# Sources

Candidate corpus, validated on 2026-11-20: every URL below was fetched (HTTP 200), and the
legal pages of the main publishers were read. Rows marked **(to verify)** were not checked. The machine-readable versions
live in `ingestion/manifests/patient.yaml` and `ingestion/manifests/gp.yaml`.

## Licensing strategy

Most French health publishers reserve their rights. HAS content is reusable with attribution,
and the ESHRE guideline article is CC BY-NC. This document is an engineering policy, not legal
advice. Hence:

1. **The repo commits only manifests**: URL, title, publisher, date, licence, audience.
2. **The ingestion CLI downloads the content** into the gitignored `data/` directory, with
   a polite rate limit and a disk cache, for local, non-commercial use. Local indexing relies
   on the text-and-data-mining exception (EU DSM Directive art. 4, French CPI L.122-5-3),
   which applies only where the publisher has not opted out. Publishers with an explicit
   opt-out are excluded.
3. **No raw text, converted Markdown, chunks or embeddings of reserved-rights sources are
   committed or published.**
4. **The UI shows only short excerpts**, always with the publisher, date and a link to the
   original page.
5. **The README states** that content belongs to its publishers.
6. **Any deployment beyond a local demo requires written permission** from Ameli, Inserm,
   EndoFrance and Santé.fr, or their removal from the manifest.

| Publisher | Licence verdict | Practical rule |
|---|---|---|
| HAS | Reuse allowed if the text is unaltered and source and date are cited; do not use the logo | Can be cited freely; do not commit the PDFs anyway, to keep one rule |
| ESHRE guideline article (Human Reproduction Open, 2022) | CC BY-NC | Fine for non-commercial use with attribution |
| Ameli (CNAM) | All rights reserved; private consultation only | Local cache only. robots.txt asks for `Crawl-delay: 10`. |
| Inserm | No reproduction without written permission | Local cache only |
| EndoFrance | © EndoFrance | Local cache only; asking for permission is the clean route |
| Santé.fr (pages and hosted PDFs, including the easy-to-read PDFs and the ENDOmind sheet) | Terms restrict substantial extraction | Local cache only, a handful of pages |
| ENDOmind France | Rights reserved on its own site | The sheet is used only through its Santé.fr copy, so Santé.fr terms apply **(to verify)** |
| ESHRE PDFs on eshre.eu | Personal and educational use | Local cache only |
| CNGOF (content hosted on cngof.fr) | Explicit text-and-data-mining opt-out | **Excluded**. Co-authored documents hosted elsewhere (HAS, EndoFrance) follow the terms of their host. |
| Info-Endométriose | Reproduction forbidden | **Excluded** |
| YouTube videos (Inserm, Ministère de la Santé, AP-HP, EndoFrance) | Standard YouTube licence assumed; YouTube terms and per-channel terms not checked **(to verify)** | Optional connector, off by default |

## Patient corpus (v1, about 30 documents)

### Ameli: Assurance Maladie, patient section (HTML, updated 2025-12 to 2026-04)

| Title | URL |
|---|---|
| Endométriose : définition et facteurs favorisants | https://www.ameli.fr/assure/sante/themes/endometriose/definition-facteurs-favorisants |
| Endométriose : symptômes, diagnostic et évolution | https://www.ameli.fr/assure/sante/themes/endometriose/symptomes-diagnostic-evolution |
| Traitement de l'endométriose | https://www.ameli.fr/assure/sante/themes/endometriose/traitement |
| Endométriose : suivi médical et vie quotidienne | https://www.ameli.fr/assure/sante/themes/endometriose/suivi-medical-vie-quotidienne |
| Désir de grossesse et endométriose | https://www.ameli.fr/assure/sante/themes/endometriose/desir-de-grossesse-et-endometriose |

### Inserm: information file (HTML, modified 2024-07-01)

| Title | URL |
|---|---|
| Endométriose : une maladie gynécologique fréquente mais encore mal connue | https://www.inserm.fr/dossier/endometriose/ |

### EndoFrance: patient association (HTML and PDF, updated 2025-12 to 2026-11)

| Title | URL |
|---|---|
| Comprendre une endométriose: patient leaflet (with CNGOF and SCGP) | https://www.endofrance.org/wp-content/uploads/2025/12/notice_infos-patientes_num.pdf |
| Qu'est-ce que l'endométriose ? | https://www.endofrance.org/qu-est-ce-que-l-endometriose/ |
| Les symptômes de l'endométriose | https://www.endofrance.org/symptomes-endometriose/ |
| Le diagnostic de l'endométriose | https://www.endofrance.org/diagnostic-endometriose/ |
| Les traitements de l'endométriose | https://www.endofrance.org/traitements-endometriose/ |
| Lutter contre la douleur | https://www.endofrance.org/la-maladie-endometriose/lutter-contre-la-douleur/ |
| Vivre avec l'endométriose | https://www.endofrance.org/la-maladie-endometriose/vivre-avec-lendometriose/ |
| FAQ | https://www.endofrance.org/la-maladie-endometriose/faq-foire-aux-questions/ |
| Qu'est-ce que l'adénomyose ? | https://www.endofrance.org/la-maladie-endometriose/adenomyose-endometriose/ |
| L'assistance médicale à la procréation (AMP/PMA) | https://www.endofrance.org/la-maladie-endometriose/lassistance-medicale-a-la-procreation-amp-ou-pma/ |
| Travailler avec l'endométriose | https://www.endofrance.org/la-maladie-endometriose/travailler-avec-lendometriose/ |
| Vocabulaire de l'endométriose | https://www.endofrance.org/la-maladie-endometriose/vocabulaire-endometriose/ |

### Santé.fr: public health information service (HTML, dated articles only)

| Title | Published | URL |
|---|---|---|
| Qu'est-ce que l'endométriose ? | 2026-02-12 | https://www.sante.fr/endometriose/quest-ce-que-lendometriose |
| Je ressens des symptômes : quelle prise en charge ? | 2025-02-24 | https://www.sante.fr/endometriose/parcours-prise-en-charge |
| En quoi consiste le test salivaire de l'endométriose ? | 2025-03-26 | https://www.sante.fr/endometriose/endometriose-en-quoi-consiste-le-test-salivaire-de-lendometriose |
| Easy-to-read version (FALC): symptoms | 2026-04 | https://www.sante.fr/dam/sites/default/files/2026-04/Quels_sont_les%20sympt%C3%B4mes_d_une_endom%C3%A9triose%20_FALC.pdf |

The Santé.fr theme pages (`/symptomes`, `/diagnostic-et-examens/…`, `/droits-des-patients/…`)
mostly aggregate cards from other publishers and carry no page-level date. They are
excluded from v1 to avoid duplicates and undated citations.

### HAS: clinical summary sheets, shared with the GP corpus (PDF, 2017-12)

These sheets are written for clinicians, and their imaging section is superseded by the 2025
HAS-labelled imaging update (see the GP corpus). The answer always shows the document date,
and imaging questions should be answered from the more recent patient sources (Ameli 2026).

| Title | URL |
|---|---|
| Démarche diagnostique et traitement médical: summary sheet | https://www.has-sante.fr/upload/docs/application/pdf/2018-01/prise_en_charge_de_lendiometriose_-_demarche_diagnostique_et_traitement_medical_-_fiche_de_synthese.pdf |
| Traitement chirurgical et fertilité: summary sheet | https://www.has-sante.fr/upload/docs/application/pdf/2018-01/prise_en_charge_de_lendiometriose_-_traitement_chirurgical_et_fertilite_-_fiche_de_synthese.pdf |

## GP corpus (generalization profile)

| Publisher | Title | Date | URL |
|---|---|---|---|
| HAS / CNGOF | Messages clés destinés au médecin généraliste | 2017-12 | https://www.has-sante.fr/upload/docs/application/pdf/2018-01/prise_en_charge_de_lendiometriose_-_messages_cles_destines_au_medecin_generaliste.pdf |
| HAS / CNGOF | Prise en charge de l'endométriose: recommandations (39 p.) | 2017-12 | https://www.has-sante.fr/upload/docs/application/pdf/2018-01/prise_en_charge_de_lendometriose_-_recommandations.pdf |
| HAS / CNGOF | Both summary sheets above | 2017-12 | (see patient corpus) |
| HAS (label) | Actualisation de la place des examens d'imagerie pour le diagnostic (supersedes the 2017 imaging section) | 2025-05 | https://www.has-sante.fr/upload/docs/application/pdf/2025-05/reco492_label_endometriose_imagerie_recommandations_ca.pdf |
| ESHRE | ESHRE guideline: endometriosis (Hum Reprod Open 2022, CC BY-NC) | 2022 | https://europepmc.org/article/PMC/PMC8951218 |
| ENDOmind France | Fiche réflexe 1: les symptômes (for first-line actors, including clinicians) | 2025-09 | https://www.sante.fr/sites/default/files/2025-09/ENDOM%C3%89TRIOSE%20FICHE%20REFLEXE%201%20-%20LES%20SYMPT%C3%94MES.pdf |

Excluded: the HAS evidence report (several hundred pages), the national strategy report and press kit
(policy content with little Q&A value), and the English CNGOF version (TDM opt-out, and it
duplicates HAS).

## Optional: videos with French captions

This is a stretch goal, off by default and not part of v1. If enabled, a
`YouTubeCaptionsConnector` would fetch captions through the official YouTube Data API
(captions endpoint), subject to its terms **(to verify)**. Captions would be chunked with
`start_seconds`, so a citation links to `…&t=<seconds>`. Otherwise, videos can be offered as
"further watching" links with no transcript indexing.

| Channel | Title | Captions | URL |
|---|---|---|---|
| Inserm | Douleurs pendant les règles : signe d'endométriose ? | Manual FR | https://www.youtube.com/watch?v=5PTjs0pt9nQ |
| Ministère de la Santé | L'endométriose est-elle difficile à diagnostiquer ? | Auto FR | https://www.youtube.com/watch?v=y8Tm6_xzz_s |
| Ministère de la Santé | L'endométriose rend-elle stérile ? | Auto FR | https://www.youtube.com/watch?v=p5O49mObyRQ |
| Ministère de la Santé | Existe-t-il un traitement spécifique pour guérir de l'endométriose ? | Auto FR | https://www.youtube.com/watch?v=ZtvRI65PvHY |
| Ministère de la Santé | Peut-on vivre normalement avec l'endométriose ? | Auto FR | https://www.youtube.com/watch?v=gsuyePiQm4E |
| AP-HP | Endométriose : préservation de la fertilité | Auto FR | https://www.youtube.com/watch?v=YvBmzMAmduU |
| EndoFrance | Quels sont les principaux examens pour une endométriose ? | Auto FR | https://www.youtube.com/watch?v=BB4HFRjHkSw |

Auto captions have no punctuation and some recognition errors. They are acceptable for
retrieval, but the answer should always link to the video rather than quote the caption
verbatim.

## Manifest schema

```yaml
- id: ameli-traitement
  url: https://www.ameli.fr/assure/sante/themes/endometriose/traitement
  source: Ameli
  title: "Traitement de l'endométriose"
  published: 2026-04-09
  audience: patient          # patient | gp | both
  format: html               # html | pdf | video
  licence: all-rights-reserved
  crawl_delay_s: 10
```

## Scraping rules

- Respect `robots.txt` (checked per host with `urllib.robotparser`) and the per-host delay
  (Ameli: 10 s).
- Use a generic User-Agent that identifies the client as a research bot. It must not
  contain personal details.
- Fetch each URL once, cache it under `data/raw/`, and run offline afterwards. The demo
  never fetches live.

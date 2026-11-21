# Sources

Corpus, validated on 2026-11-20 and 2026-11-21: every URL below was fetched (HTTP 200), and the
legal pages of the main publishers were read. Rows marked **(to verify)** were not checked. The machine-readable versions
live in `ingestion/manifests/patient.yaml` and `ingestion/manifests/gp.yaml`.

## Licensing strategy

The corpus is used for a **non-commercial technical demonstration**. HAS content is
reusable with attribution, Service-Public content is under the open government licence
(etalab-2.0), and the ESHRE guideline article is CC BY-NC. The other publishers reserve
their rights; their content is reproduced here only for the demonstration, with full
attribution.

1. **Manifests** (`ingestion/manifests/`) list every document: URL, title, publisher, date,
   licence, audience.
2. **A snapshot of the fetched corpus is committed** under `data/raw/` and `data/markdown/`.
   The corpus is small (a few MB), and the snapshot lets the demo run offline or in a GitHub
   Codespace without fetching anything. The vector index (`data/qdrant/`) is not committed;
   it is rebuilt from the snapshot.
3. **Every chunk keeps its publisher, title, date and URL**, and the UI always shows them
   with a link to the original page.
4. **The README states** that all source content belongs to its publishers, is used for a
   non-commercial demonstration, and is removed on request.
5. **Publishers with an explicit text-and-data-mining opt-out or a reproduction ban are
   excluded** (CNGOF, Info-Endométriose).
6. **Any deployment beyond the demonstration requires written agreements** with the
   publishers that reserve their rights (see [scenario.md](scenario.md#what-a-real-deployment-would-need)).

| Publisher | Licence | Practical rule |
|---|---|---|
| HAS | Reuse allowed if the text is unaltered and source and date are cited; do not use the logo | Included |
| Service-Public, Mon Parcours Handicap | Open government licence (etalab-2.0) | Included |
| ESHRE guideline article (Human Reproduction Open, 2022) | CC BY-NC | Included, non-commercial, with attribution |
| Ameli (CNAM) | All rights reserved | Demonstration only, attributed. robots.txt asks for `Crawl-delay: 10`. |
| EndoFrance | © EndoFrance | Demonstration only, attributed |
| Santé.fr (pages and hosted PDFs, including the easy-to-read PDFs and the ENDOmind sheets) | Terms restrict substantial extraction | Demonstration only, attributed, a handful of pages |
| Inserm | No reproduction without written permission | Optional, off by default |
| CNGOF (content hosted on cngof.fr) | Explicit text-and-data-mining opt-out | **Excluded**. Co-authored documents hosted elsewhere (HAS, EndoFrance) follow the terms of their host. |
| Info-Endométriose | Reproduction forbidden | **Excluded** |
| YouTube videos | Platform and channel terms not checked **(to verify)** | Optional connector, off by default |

## Patient corpus (about 25 documents)

Chosen for the personas in [scenario.md](scenario.md). When sources disagree, the most
recent one is preferred, and every answer shows the source date.

### Ameli: Assurance Maladie, patient section (HTML, 2025-12 to 2026-04)

| Title | URL |
|---|---|
| Endométriose : définition et facteurs favorisants | https://www.ameli.fr/assure/sante/themes/endometriose/definition-facteurs-favorisants |
| Endométriose : symptômes, diagnostic et évolution | https://www.ameli.fr/assure/sante/themes/endometriose/symptomes-diagnostic-evolution |
| Traitement de l'endométriose | https://www.ameli.fr/assure/sante/themes/endometriose/traitement |
| Endométriose : suivi médical et vie quotidienne | https://www.ameli.fr/assure/sante/themes/endometriose/suivi-medical-vie-quotidienne |
| Désir de grossesse et endométriose | https://www.ameli.fr/assure/sante/themes/endometriose/desir-de-grossesse-et-endometriose |

### Santé.fr: dated articles and easy-to-read PDFs

| Title | Published | URL |
|---|---|---|
| Qu'est-ce que l'endométriose ? | 2026-02-12 | https://www.sante.fr/endometriose/quest-ce-que-lendometriose |
| Je ressens des symptômes : quelle prise en charge ? | 2025-02-24 | https://www.sante.fr/endometriose/parcours-prise-en-charge |
| En quoi consiste le test salivaire de l'endométriose ? | 2025-03-26 | https://www.sante.fr/endometriose/endometriose-en-quoi-consiste-le-test-salivaire-de-lendometriose |
| Trouver la filière Endométriose la plus proche de chez moi (third-party cards stripped; link out to the directory) | 2025-11-24 | (URL to confirm in the manifest) |
| Easy-to-read (FALC): Quels sont les symptômes d'une endométriose ? | 2026-04 | https://www.sante.fr/dam/sites/default/files/2026-04/Quels_sont_les%20sympt%C3%B4mes_d_une_endom%C3%A9triose%20_FALC.pdf |
| Easy-to-read (FALC): Qu'est-ce que l'endométriose ; Quels professionnels de santé aller voir ; Pourquoi les douleurs d'une endométriose sont différentes | 2026-04 | (URLs to confirm in the manifest) |

The Santé.fr theme pages (`/symptomes`, `/diagnostic-et-examens/…`, `/droits-des-patients/…`)
mostly aggregate cards from other publishers and carry no page-level date. They are
excluded to avoid duplicates and undated citations.

### EndoFrance: patient association (HTML, 2025-12 to 2026-11)

| Title | URL |
|---|---|
| FAQ | https://www.endofrance.org/la-maladie-endometriose/faq-foire-aux-questions/ |
| Le diagnostic de l'endométriose | https://www.endofrance.org/diagnostic-endometriose/ |
| Lutter contre la douleur | https://www.endofrance.org/la-maladie-endometriose/lutter-contre-la-douleur/ |
| Travailler avec l'endométriose | https://www.endofrance.org/la-maladie-endometriose/travailler-avec-lendometriose/ |
| L'assistance médicale à la procréation (AMP/PMA) | https://www.endofrance.org/la-maladie-endometriose/lassistance-medicale-a-la-procreation-amp-ou-pma/ |
| Vocabulaire de l'endométriose | https://www.endofrance.org/la-maladie-endometriose/vocabulaire-endometriose/ |

### Rights and work: Service-Public and Mon Parcours Handicap (etalab-2.0)

| Title | Checked | URL |
|---|---|---|
| Prise en charge d'une affection de longue durée (ALD) | 2026-10-15 | https://www.service-public.gouv.fr/particuliers/vosdroits/F34068 |
| Reconnaissance de la qualité de travailleur handicapé (RQTH) | 2026-03-24 | https://www.service-public.gouv.fr/particuliers/vosdroits/F1650 |
| Endométriose : quels aménagements au travail ? | 2026-03-26 | https://www.monparcourshandicap.gouv.fr/actualite/comment-adapter-votre-travail-avec-une-endometriose |

### HAS: clinical summary sheets, shared with the GP corpus (PDF, 2017-12)

These sheets are written for clinicians, and their imaging section is superseded by the 2025
HAS-labelled imaging update (see the GP corpus). Imaging questions are answered from the
more recent sources first.

| Title | URL |
|---|---|
| Démarche diagnostique et traitement médical: summary sheet | https://www.has-sante.fr/upload/docs/application/pdf/2018-01/prise_en_charge_de_lendiometriose_-_demarche_diagnostique_et_traitement_medical_-_fiche_de_synthese.pdf |
| Traitement chirurgical et fertilité: summary sheet | https://www.has-sante.fr/upload/docs/application/pdf/2018-01/prise_en_charge_de_lendiometriose_-_traitement_chirurgical_et_fertilite_-_fiche_de_synthese.pdf |

### Optional, off by default

| Publisher | Title | URL |
|---|---|---|
| Inserm | Endométriose : une maladie gynécologique fréquente mais encore mal connue | https://www.inserm.fr/dossier/endometriose/ |

### Deliberately absent

Some real, recent facts are kept out of the corpus on purpose, to test the "grounded or
silent" rule: reimbursement of reusable menstrual protections (from 1 October 2026),
menstrual leave, and bills on the ALD 30 list. School arrangements (PAI, sport exemption)
are a known gap: the relevant Education nationale page could not be fetched, so the
assistant declines and points to the school nurse.

## GP corpus (generalization profile)

| Publisher | Title | Date | URL |
|---|---|---|---|
| HAS / CNGOF | Messages clés destinés au médecin généraliste | 2017-12 | https://www.has-sante.fr/upload/docs/application/pdf/2018-01/prise_en_charge_de_lendiometriose_-_messages_cles_destines_au_medecin_generaliste.pdf |
| HAS / CNGOF | Prise en charge de l'endométriose: recommandations (39 p.) | 2017-12 | https://www.has-sante.fr/upload/docs/application/pdf/2018-01/prise_en_charge_de_lendometriose_-_recommandations.pdf |
| HAS / CNGOF | Both summary sheets above | 2017-12 | (see patient corpus) |
| HAS (label) | Actualisation de la place des examens d'imagerie pour le diagnostic (supersedes the 2017 imaging section) | 2025-05 | https://www.has-sante.fr/upload/docs/application/pdf/2025-05/reco492_label_endometriose_imagerie_recommandations_ca.pdf |
| ESHRE | ESHRE guideline: endometriosis (Hum Reprod Open 2022, CC BY-NC) | 2022 | https://europepmc.org/article/PMC/PMC8951218 |
| ENDOmind France | Fiche réflexe 1: les symptômes (for first-line actors, including clinicians) | 2025-09 | https://www.sante.fr/sites/default/files/2025-09/ENDOM%C3%89TRIOSE%20FICHE%20REFLEXE%201%20-%20LES%20SYMPT%C3%94MES.pdf |
| ENDOmind France | Fiche réflexe 3: ressources pour l'accompagnement et la prise en charge | 2025-09 | (URL to confirm in the manifest) |

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
  never fetches live, and the committed snapshot means it never has to.

# Sources

Corpus, validated on 2026-11-20 and 2026-11-21: every URL below was fetched (HTTP 200), the ESHRE
article through its open-access XML (see the GP corpus), and the legal pages of the main
publishers were read. The corpus was enlarged on 2026-11-21 (45 patient and 4 GP
documents), with each addition checked the same way. Rows marked **(to verify)** were not
checked. The machine-readable versions live in `ingestion/manifests/patient.yaml` and `ingestion/manifests/gp.yaml`.

## Licensing strategy

The corpus is used for a **non-commercial technical demonstration**. HAS content is
reusable with attribution, Service-Public content is under the open government licence
(etalab-2.0), ANSM content is reusable with attribution, the ESHRE guideline article is
CC BY-NC, and the WHO fact sheet allows non-commercial reuse with attribution. The other
publishers reserve their rights; their content is reproduced here only for the demonstration, with full
attribution.

1. **Manifests** (`ingestion/manifests/`) list every document: URL, title, publisher, date,
   licence, audience.
2. **A snapshot of the fetched corpus is committed** under `data/raw/` and `data/markdown/`.
   The corpus is small (about 30 MB, mostly PDFs), and the snapshot lets the demo run offline or in a GitHub
   Codespace without fetching anything. The vector index (`data/qdrant/`) is not committed;
   it is rebuilt from the snapshot.
3. **Every chunk keeps its publisher, title, date and URL**, and the UI always shows them
   with a link to the original page.
4. **The README states** that all source content belongs to its publishers, is used for a
   non-commercial demonstration, and is removed on request.
5. **Publishers with an explicit text-and-data-mining opt-out or a reproduction ban are
   excluded** (CNGOF, Info-Endométriose, Fil Santé Jeunes, the Luxembourg scientific council;
   see [Excluded after review](#excluded-after-review)).
6. **Any deployment beyond the demonstration requires written agreements** with the
   publishers that reserve their rights (see [scenario.md](scenario.md#what-a-real-deployment-would-need)).

| Publisher | Licence | Practical rule |
|---|---|---|
| HAS | Reuse allowed if the text is unaltered and source and date are cited; do not use the logo | Included |
| Service-Public, Mon Parcours Handicap | Open government licence (etalab-2.0) | Included |
| ANSM | Reuse allowed if the text is unaltered and source and date are cited | Included |
| ESHRE guideline article (Human Reproduction Open, 2022) | CC BY-NC | Included, non-commercial, with attribution |
| OMS / WHO (French fact sheet) | Non-commercial reuse with attribution | Included, non-commercial, with attribution |
| Ameli (CNAM) | All rights reserved | Demonstration only, attributed. robots.txt asks for `Crawl-delay: 10`. |
| EndoFrance | © EndoFrance | Demonstration only, attributed |
| Santé.fr (pages and hosted PDFs, including the easy-to-read PDFs and the ENDOmind sheets) | Terms restrict substantial extraction | Demonstration only, attributed: the pages listed below are kept as a committed snapshot for the demo |
| ENDOmind France (booklet hosted on endomind.org) | All rights reserved | Demonstration only, attributed |
| Étudiant.gouv | No reuse terms found; treated as all rights reserved | Demonstration only, attributed |
| HUG (Geneva), CHUV (Lausanne), HELORA (Mons) | All rights reserved | Demonstration only, attributed. Swiss or Belgian care context: answers say where the source comes from. |
| Inserm | No reproduction without written permission | Optional, off by default |
| CNGOF (content hosted on cngof.fr) | Explicit text-and-data-mining opt-out | **Excluded**. Co-authored documents hosted elsewhere (HAS, EndoFrance) follow the terms of their host. |
| Info-Endométriose | Reproduction forbidden | **Excluded** |
| Fil Santé Jeunes | Reproduction and networked use forbidden | **Excluded** |
| Conseil scientifique (Luxembourg) | Reproduction forbidden without written permission | **Excluded** |
| YouTube videos | Platform and channel terms not checked **(to verify)** | Optional connector, off by default |

## Patient corpus (69 documents, plus one optional)

Chosen for the personas in [scenario.md](scenario.md). When sources disagree, the most
recent one is preferred, and every answer shows the source date.

### Ameli: Assurance Maladie, patient section (HTML, 2024-01 to 2026-11)

| Title | Published | URL |
|---|---|---|
| Endométriose : définition et facteurs favorisants | 2026-04-09 | https://www.ameli.fr/assure/sante/themes/endometriose/definition-facteurs-favorisants |
| Endométriose : symptômes, diagnostic et évolution | 2026-04-09 | https://www.ameli.fr/assure/sante/themes/endometriose/symptomes-diagnostic-evolution |
| Traitement de l'endométriose | 2026-04-09 | https://www.ameli.fr/assure/sante/themes/endometriose/traitement |
| Endométriose : suivi médical et vie quotidienne | 2026-04-09 | https://www.ameli.fr/assure/sante/themes/endometriose/suivi-medical-vie-quotidienne |
| Désir de grossesse et endométriose | 2025-12-19 | https://www.ameli.fr/assure/sante/themes/endometriose/desir-de-grossesse-et-endometriose |
| Douleurs pendant les règles ou dysménorrhée : quelles sont les causes ? | 2026-09-29 | https://www.ameli.fr/assure/sante/themes/regles-douloureuses/douleurs-regles |
| Douleurs pendant les règles : que faire pour être soulagée ? | 2025-06-25 | https://www.ameli.fr/assure/sante/themes/regles-douloureuses/que-faire-quand-consulter |
| Règles douloureuses : consultation et traitement | 2025-06-25 | https://www.ameli.fr/assure/sante/themes/regles-douloureuses/consultation-traitement |
| Saignements entre les règles ou règles très abondantes : quelles causes ? | 2026-06-25 | https://www.ameli.fr/assure/sante/themes/saignements-gynecologiques-anormaux/saignements-entre-les-regles-ou-regles-abondantes-longues-les-causes |
| Kyste ovarien : définition et causes | 2024-01-26 | https://www.ameli.fr/assure/sante/themes/kyste-ovarien-ovaire/definition-causes |
| Bilan médical de l'infertilité | 2026-11-04 | https://www.ameli.fr/assure/sante/devenir-parent/concevoir-un-enfant/fertilite-infertilite-sterilite/bilan-medical-infertilite-sterilite |
| Autoconservation des gamètes et tissus germinaux à des fins ultérieures d'AMP | 2025-09-30 | https://www.ameli.fr/assure/sante/devenir-parent/concevoir-un-enfant/procreation-medicalement-assistee-pma-amp/autoconservation-des-gametes-et-tissus-germinaux-en-vue-d-une-amp |

The endometriosis theme pages are completed by related themes: painful periods (three
pages), abnormal bleeding (adenomyosis), ovarian cysts (endometrioma), the infertility
work-up and fertility preservation.

### Santé.fr: dated articles and easy-to-read PDFs

| Title | Published | URL |
|---|---|---|
| Qu'est-ce que l'endométriose ? | 2026-02-12 | https://www.sante.fr/endometriose/quest-ce-que-lendometriose |
| Je ressens des symptômes : quelle prise en charge ? | 2025-02-24 | https://www.sante.fr/endometriose/parcours-prise-en-charge |
| En quoi consiste le test salivaire de l'endométriose ? | 2025-03-26 | https://www.sante.fr/endometriose/endometriose-en-quoi-consiste-le-test-salivaire-de-lendometriose |
| Trouver la filière Endométriose la plus proche de chez moi (third-party cards stripped; link out to the directory) | 2025-11-24 | https://www.sante.fr/endometriose/trouver-la-filiere-endometriose-la-plus-proche-de-chez-moi |
| Easy-to-read (FALC): Qu'est-ce que l'endométriose ? | 2022-12 (checked 2026-05-04) | https://www.sante.fr/dam/sites/default/files/2026-04/Qu%27est-ce_que_l_endom%C3%A9triose_FALC.pdf |
| Easy-to-read (FALC): Quels sont les symptômes d'une endométriose ? | 2022-12 (checked 2026-05-04) | https://www.sante.fr/dam/sites/default/files/2026-04/Quels_sont_les%20sympt%C3%B4mes_d_une_endom%C3%A9triose%20_FALC.pdf |
| Easy-to-read (FALC): Quels professionnels de santé aller voir ? | 2022-12 (checked 2026-05-04) | https://www.sante.fr/dam/sites/default/files/2026-04/Quels_professionnels_de_sant%C3%A9_aller_voir_FALC.pdf |
| Easy-to-read (FALC): Pourquoi les douleurs d'une endométriose sont différentes ? | 2022-12 (checked 2026-05-04) | https://www.sante.fr/dam/sites/default/files/2026-04/Pourquoi_les%20douleurs_d_une%20endom%C3%A9triose%20sont_diff%C3%A9rentes_FALC.pdf |
| Symptômes de l'endométriose : les douleurs neurologiques | 2025-03-03 | https://www.sante.fr/endometriose/symptomes-de-lendometriose-les-douleurs-neurologiques |
| Le diagnostic souvent tardif de l'endométriose | 2025-01-06 | https://www.sante.fr/endometriose/le-diagnostic-souvent-tardif-de-lendometriose |
| Évaluer la douleur due à l'endométriose | 2025-01-06 | https://www.sante.fr/endometriose/evaluer-la-douleur-due-lendometriose |
| Évaluer la qualité de vie en cas d'endométriose | 2025-01-06 | https://www.sante.fr/endometriose/evaluer-la-qualite-de-vie-en-cas-dendometriose |
| Endométriose : déroulement de la grossesse et accouchement | 2024-03-04 | https://www.sante.fr/endometriose/endometriose-deroulement-de-la-grossesse-et-accouchement |
| Qu'est-ce que le temps partiel thérapeutique ? | 2024-03-07 | https://www.sante.fr/endometriose/quest-ce-que-le-temps-partiel-therapeutique |
| Doit-on préciser la raison d'un arrêt maladie à son employeur ? | 2024-03-08 | https://www.sante.fr/endometriose/doit-preciser-la-raison-dun-arret-maladie-son-employeur |
| La demande d'admission en ALD 31 pour les femmes atteintes d'endométriose | 2024-03-01 | https://www.sante.fr/endometriose/la-demande-dadmission-en-ald-31-pour-les-femmes-atteintes-dendometriose |
| Les structures spécialisées douleur chronique - SDC | 2026-02-10 | https://www.sante.fr/endometriose/les-structures-specialisees-douleur-chronique-sdc |
| En mouvement avec l'endométriose : les bonnes pratiques | 2025-02-25 | https://www.sante.fr/endometriose/en-mouvement-avec-lendometriose-les-bonnes-pratiques |
| Certains compléments alimentaires peuvent-ils soulager l'endométriose ? | 2022-04-08 | https://www.sante.fr/endometriose/decryptage/nos-reponses/certains-complements-alimentaires-peuvent-ils-soulager-lendometriose |
| Petite chronique de l'endométriose | 2024-04-02 | https://www.sante.fr/petite-chronique-de-lendometriose |

The FALC PDFs are byte-identical to the versions first published in 2022-12; the Santé.fr
sheet pages were republished on 04/05/2026. The recency rule uses the 2022-12 date.

The Santé.fr theme pages (`/symptomes`, `/diagnostic-et-examens/…`, `/droits-des-patients/…`)
mostly aggregate cards from other publishers and carry no page-level date. They are
excluded to avoid duplicates and undated citations. Santé.fr republications of EndoFrance
texts (adenomyosis, dyspareunia, painful periods) are left out: the more recent EndoFrance
originals are used instead.

### EndoFrance: patient association (HTML, 2025-12 to 2026-11)

Dates are the pages' last update (`dateModified` metadata).

| Title | Updated | URL |
|---|---|---|
| FAQ : foire aux questions | 2026-01-13 | https://www.endofrance.org/la-maladie-endometriose/faq-foire-aux-questions/ |
| Le diagnostic de l'endométriose | 2025-12-18 | https://www.endofrance.org/diagnostic-endometriose/ |
| Lutter contre la douleur | 2026-09-09 | https://www.endofrance.org/la-maladie-endometriose/lutter-contre-la-douleur/ |
| Travailler avec l'endométriose | 2026-11-19 | https://www.endofrance.org/la-maladie-endometriose/travailler-avec-lendometriose/ |
| L'assistance médicale à la procréation (AMP/PMA) | 2025-12-18 | https://www.endofrance.org/la-maladie-endometriose/lassistance-medicale-a-la-procreation-amp-ou-pma/ |
| Vocabulaire de l'endométriose | 2026-07-05 | https://www.endofrance.org/la-maladie-endometriose/vocabulaire-endometriose/ |
| Règles douloureuses et Endométriose | 2026-03-12 | https://www.endofrance.org/la-maladie-endometriose/symptomes-endometriose/regles-douloureuses/ |
| Douleurs pelviennes et Endométriose | 2025-12-19 | https://www.endofrance.org/la-maladie-endometriose/symptomes-endometriose/douleurs-pelviennes-lombaires/ |
| Troubles digestifs et Endométriose | 2025-12-29 | https://www.endofrance.org/la-maladie-endometriose/symptomes-endometriose/troubles-digestifs/ |
| Troubles urinaires et Endométriose | 2025-12-19 | https://www.endofrance.org/la-maladie-endometriose/symptomes-endometriose/troubles-urinaires/ |
| Fatigue chronique et Endométriose | 2025-12-19 | https://www.endofrance.org/la-maladie-endometriose/symptomes-endometriose/fatigue-chronique/ |
| La dyspareunie : douleurs lors des rapports sexuels | 2025-12-19 | https://www.endofrance.org/la-maladie-endometriose/symptomes-endometriose/dyspareunie-douleurs-rapports-sexuels/ |
| Infertilité et endométriose | 2025-12-19 | https://www.endofrance.org/la-maladie-endometriose/symptomes-endometriose/infertilite/ |
| La préservation ovocytaire | 2025-12-18 | https://www.endofrance.org/la-maladie-endometriose/la-preservation-ovocytaire/ |
| Les traitements de l'endométriose | 2025-12-18 | https://www.endofrance.org/traitements-endometriose/ |
| Qu'est-ce que l'adénomyose ? | 2026-01-14 | https://www.endofrance.org/la-maladie-endometriose/adenomyose-endometriose/ |
| La ménopause et l'Endométriose | 2025-12-19 | https://www.endofrance.org/la-maladie-endometriose/menopause-endometriose/ |
| Vivre avec l'Endométriose | 2025-12-19 | https://www.endofrance.org/la-maladie-endometriose/vivre-avec-lendometriose/ |
| Accompagner une proche atteinte d'endométriose | 2025-12-18 | https://www.endofrance.org/la-maladie-endometriose/entourage/ |
| Je suis parent d'une jeune personne atteinte | 2026-05-28 | https://www.endofrance.org/la-maladie-endometriose/entourage/je-suis-parent-dune-jeune-personne-atteinte/ |

### Rights, work and school: Service-Public and Mon Parcours Handicap (etalab-2.0)

| Title | Checked | URL |
|---|---|---|
| Prise en charge d'une affection de longue durée (ALD) | 2026-10-15 | https://www.service-public.gouv.fr/particuliers/vosdroits/F34068 |
| Reconnaissance de la qualité de travailleur handicapé (RQTH) | 2026-03-24 | https://www.service-public.gouv.fr/particuliers/vosdroits/F1650 |
| Endométriose : quels aménagements au travail ? | 2026-03-26 | https://www.monparcourshandicap.gouv.fr/actualite/comment-adapter-votre-travail-avec-une-endometriose |
| Arrêt maladie : démarches à effectuer par le salarié | 2026-09-01 | https://www.service-public.gouv.fr/particuliers/vosdroits/F303 |
| Qu'est-ce qu'un projet d'accueil individualisé (PAI) ? | 2025-05-21 | https://www.service-public.gouv.fr/particuliers/vosdroits/F21392 |
| Un jeune en situation de handicap peut-il avoir un aménagement pour passer ses examens ? | 2025-09-25 | https://www.service-public.gouv.fr/particuliers/vosdroits/F15112 |
| Quels interlocuteurs et procédures pour bénéficier d'aménagements dans l'enseignement supérieur ? | 2026-01-13 | https://www.monparcourshandicap.gouv.fr/etudes-superieures/quels-interlocuteurs-et-procedures-pour-beneficier-damenagements-dans-0 |

The exam-adjustment page applies only when the condition is disabling; answers say so.

### Studies, rights and international framing

| Publisher | Title | Date | URL |
|---|---|---|---|
| Étudiant.gouv | Endométriose : les aménagements d'études qui s'adaptent à vos besoins | 2024-03-05 | https://www.etudiant.gouv.fr/fr/amenagements-endometriose |
| ENDOmind France | Livret endométriose : refus d'ALD hors liste (ALD 31) – les étapes pour contester la décision | 2026-01-01 | https://www.endomind.org/_files/ugd/ebf679_5e46ecbf4da9451093b4090d75664c55.pdf |
| OMS | Endométriose – Principaux repères | 2025-10-15 | https://www.who.int/fr/news-room/fact-sheets/detail/endometriosis |

The ENDOmind booklet shows only a year (©ENDOmind 2026), recorded as 2026-01-01.

### French-language university hospitals: HUG, CHUV, HELORA (all rights reserved)

Swiss and Belgian sources, chosen for adenomyosis, treatments, pain tracking and teenage
period pain. Their care pathways and reimbursement rules are not French, so answers name
the country of the source.

| Publisher | Title | Date | URL |
|---|---|---|---|
| HUG | Les traitements pour l'endométriose | 2025-09-02 | https://www.hug.ch/gynecologie/quels-traitements-pour-endometriose |
| HUG | Les douleurs menstruelles | 2026-10-23 | https://enfants-ados.hug.ch/gynecologie-pediatrique/douleurs-menstruelles |
| HUG | Soulager l'endométriose – Carnet de suivi des douleurs, symptômes et traitements | 2024-08-01 | https://www.hug.ch/sites/interhug/files/documents/endometriose_suivi.pdf |
| CHUV | Endométriose et adénomyose | 2026-11-09 | https://www.chuv.ch/fr/fertilite/umr-home/endometriose |
| HELORA | Clinique Mon(s) endométriose – Prise en charge multidisciplinaire de l'endométriose | 2026-02-01 | https://www.helora.be/sites/default/files/uploads/Documents/Services%20m%C3%A9dicaux%20et%20param%C3%A9dicaux/Gyn%C3%A9cologie-Obst%C3%A9trique-Maternit%C3%A9/CLIN-DOC-058%20-%20Endometriose.pdf |

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
silent" rule: reimbursement of reusable menstrual protections (from 1 October 2026) and
bills on the ALD 30 list. Menstrual leave is no longer one of them: the Étudiant.gouv page
mentions it, so it is not used as a not-in-corpus test. The same page mentions free
distribution of menstrual cups and underwear in universities, which is not the
reimbursement: a question on reimbursement retrieves it, and the answer must not turn it
into a reimbursement claim.

School arrangements: the PAI and exam adjustments are covered by Service-Public. The sport
exemption and the school nurse's role remain a known gap (no fetchable Education nationale
page), so the assistant declines on those and points to the school nurse.

### Excluded after review

| Candidate | Reason |
|---|---|
| Luxembourg scientific council, 2026 endometriosis guideline (long version) and its patient version | Reproduction and distribution outside the site forbidden without written permission. The strongest GP candidate; it could be added with permission. |
| Fil Santé Jeunes pages on period pain and endometriosis, including the texts republished on Santé.fr | Reproduction and networked use forbidden |
| Inserm "Canal Détox" piece on period pain, republished on Santé.fr | Inserm content, no reproduction without written permission (same rule as the Inserm dossier) |

## GP corpus (generalization profile, 12 documents)

| Publisher | Title | Date | URL |
|---|---|---|---|
| HAS / CNGOF | Messages clés destinés au médecin généraliste | 2017-12 | https://www.has-sante.fr/upload/docs/application/pdf/2018-01/prise_en_charge_de_lendiometriose_-_messages_cles_destines_au_medecin_generaliste.pdf |
| HAS / CNGOF | Prise en charge de l'endométriose: recommandations (39 p.) | 2017-12 | https://www.has-sante.fr/upload/docs/application/pdf/2018-01/prise_en_charge_de_lendometriose_-_recommandations.pdf |
| HAS / CNGOF | Both summary sheets above | 2017-12 | (see patient corpus) |
| HAS (label) | Actualisation de la place des examens d'imagerie pour le diagnostic (supersedes the 2017 imaging section) | 2025-05 | https://www.has-sante.fr/upload/docs/application/pdf/2025-05/reco492_label_endometriose_imagerie_recommandations_ca.pdf |
| HAS | Évaluation du test salivaire Endotest® dans les situations complexes de diagnostic d'endométriose (indications: third line, before laparoscopy) | 2024-04-24 | https://has-sante.fr/jcms/p_3486036/fr/evaluation-du-test-salivaire-endotest-dans-les-situations-complexes-de-diagnostic-d-endometriose |
| HAS | Fiche mémo: contraception chez la femme adulte et l'adolescente en âge de procréer (hormonal methods used first line for pain) | 2019-07 | https://has-sante.fr/upload/docs/application/pdf/2015-02/1e_maj_contraceptionfadulte-procreer-060215.pdf |
| ANSM | Progestatifs et risque de méningiome : recommandations pour limiter ce risque | 2025-06-12 | https://ansm.sante.fr/actualites/progestatifs-et-risque-de-meningiome-recommandations-pour-limiter-ce-risque |
| ESHRE | ESHRE guideline: endometriosis (Hum Reprod Open 2022, CC BY-NC) | 2022 | https://europepmc.org/article/PMC/PMC8951218 |
| ENDOmind France | Fiche réflexe 1: les symptômes (for first-line actors, including clinicians) | 2025-09 | https://www.sante.fr/sites/default/files/2025-09/ENDOM%C3%89TRIOSE%20FICHE%20REFLEXE%201%20-%20LES%20SYMPT%C3%94MES.pdf |
| ENDOmind France | Fiche réflexe 2: les comportements qui alertent | 2025-09 | https://www.sante.fr/sites/default/files/2025-09/ENDOM%C3%89TRIOSE%20FICHE%20REFLEXE%202%20-%20LES%20COMPORTEMENTS%20QUI%20ALERTENT.pdf |
| ENDOmind France | Fiche réflexe 3: ressources pour l'accompagnement et la prise en charge | 2025-09 | https://www.sante.fr/sites/default/files/2025-09/ENDOM%C3%89TRIOSE%20FICHE%20REFLEXE%203%20-%20LES%20RESSOURCES%20POUR%20ACCOMPAGNEMENT%20ET%20UNE%20PRISE%20EN%20CHARGE%20DE%20L%27ENDOMETRIOSE.pdf |

Europe PMC serves the ESHRE article page behind a JavaScript challenge (HTTP 403 for a plain
client). The same CC BY-NC article is fetched as JATS XML from the Europe PMC REST API
(`fetch_url` in the manifest, `format: xml`, converted by docling's JATS backend), while
citations link to the article page.

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

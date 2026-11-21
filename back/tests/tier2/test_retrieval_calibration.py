"""The evidence threshold on the real indexes: the calibration questions of docs/method.md.

Needs the embedding endpoint and `data/qdrant` (free: the backend must not be running).
In-corpus questions are written as the `rewrite` node should hand them to retrieval:
standalone and naming the topic.
"""

import pytest
from endorag_back.config.settings import Settings
from endorag_back.repositories.search_repository import SearchRepository
from endorag_ingestion.factory import build_storage

pytestmark = pytest.mark.live

IN_CORPUS = {
    "patient": [
        "Règles très douloureuses qui font rater les cours, le paracétamol ne soulage pas : "
        "est-ce normal ?",
        "Quel médecin consulter pour des règles très douloureuses : généraliste ou gynécologue ?",
        "Faut-il une opération pour diagnostiquer l'endométriose ? Une échographie normale "
        "exclut-elle une endométriose ?",
        "Comment préparer ma consultation si je pense avoir une endométriose ?",
        "Le test salivaire de l'endométriose est-il vendu en pharmacie ?",
        "Endométriose diagnostiquée et absences au travail : prise en charge à 100 % et à quoi "
        "sert la RQTH ?",
        "Quels sont les traitements hormonaux de l'endométriose ?",
        "Est-ce que l'endométriose rend stérile ?",
        "C'est quoi l'adénomyose ?",
        "Je peux avoir un aménagement pour mes examens au lycée à cause de mes douleurs ?",
        "ALD 31 RQTH endométriose travail",
    ],
    "gp": [
        "Quels signes d'appel doivent faire évoquer une endométriose, et quelle imagerie en "
        "première intention ?",
        "Quel traitement prescrire à une patiente de 24 ans atteinte d'endométriose ?",
        "Quelle est la place de la cœlioscopie diagnostique dans l'endométriose ?",
        "Traitement hormonal de première intention de l'endométriose douloureuse",
        "Endométriose et préservation de la fertilité : quand orienter ?",
    ],
}
# Not in the corpus or off topic. "Le projet de loi ALD 30" is left out: it is on topic
# (0.58 on the patient index), so only triage and grounded generation can decline it.
NOT_IN_CORPUS = [
    "Les culottes menstruelles sont remboursées depuis octobre, c'est vrai ?",
    "Combien de jours de congé menstruel mon employeur doit-il m'accorder ?",
    "Tu peux m'aider à faire mon devoir de statistiques ?",
    "Donne-moi une recette de crêpes.",
    "Quel est le prix d'une IRM en Suisse ?",
    "Quel temps fera-t-il demain à Paris ?",
    "Quels sont les effets secondaires du vaccin contre la grippe ?",
    "Comment soigner une entorse de la cheville ?",
    "Quelle est la posologie de l'amoxicilline chez l'enfant ?",
]


@pytest.fixture(scope="module", params=["patient", "gp"])
def repo(request):
    settings = Settings(profile=request.param)
    store = build_storage(settings)
    yield request.param, SearchRepository(store, settings)
    store.close()  # local Qdrant locks its directory


def test_in_corpus_questions_have_sufficient_evidence(repo):
    profile, repository = repo
    weak = {}
    for q in IN_CORPUS[profile]:
        result = repository.retrieve(q)
        if not result.sufficient:
            weak[q] = result.best_dense_score
    assert weak == {}


def test_not_in_corpus_questions_have_weak_evidence(repo):
    _, repository = repo
    strong = {}
    for q in NOT_IN_CORPUS:
        result = repository.retrieve(q)
        if result.sufficient:
            strong[q] = result.best_dense_score
    assert strong == {}


def test_multi_topic_rights_query_surfaces_rqth_and_ald31_sources(repo):
    """The RQTH source in the top 5 is mph-travail (Mon Parcours Handicap), not Service-Public.

    sp-rqth sits at candidate ranks 13 and 18 of 20, so issue #13's "Service-Public/RQTH"
    wording is met only through mph-travail; closing that gap is an M3 retrieval input
    (docs/method.md, D-20).
    """
    profile, repository = repo
    if profile != "patient":
        pytest.skip("patient corpus")
    docs = {c.chunk.doc_id for c in repository.retrieve("ALD 31 RQTH endométriose travail").chunks}
    assert docs & {"sp-rqth", "mph-travail"}
    assert "santefr-ald31-demande" in docs

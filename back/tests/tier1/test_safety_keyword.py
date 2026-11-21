"""Regression lists for the keyword layer: 100% recall on emergencies, no false positive,
for each profile."""

import asyncio

import pytest
from endorag_back.services.safety import KeywordSafetyCheck
from endorag_back.services.safety.keyword_check import normalize

# Emergency phrasings, with youth slang, typos and indirect wording, by expected kind.
EMERGENCIES = {
    "psychological": [
        "Ça fait trois jours que j'ai une douleur horrible, rien ne marche, je vomis, "
        "et honnêtement j'ai envie que tout s'arrête.",
        "J'ai envie que tout s'arrête.",
        "que tout s arette enfin",
        "je veux en finir",
        "jpp de cette vie, jveux en finir avec tout",
        "Je pense à me suicider.",
        "jvais me suicidé",
        "j'ai plus envie de vivre",
        "jveux mourir sérieux",
        "envi de mourrir",
        "je veux plus vivre comme ça",
        "J'ai envie de me faire du mal.",
        "Parfois je me dis que ce serait mieux de mettre fin à mes jours.",
        "j'ai envie de disparaître pour toujours",
        "je me scarifie depuis quelques semaines",
        "j'en ai marre de la vie, je sers à rien",
        "j'ai envie de me foutre en l'air",
        "je vais me tuer",
        "J'AI ENVIE DE MOURIRRR",
        "j'ai envie d'en finir avec cette vie",
        "j'ai envie d'en finir avec l'existence",
        "j'ai avalé toute la boîte de Doliprane",
        "tout le monde serait mieux sans moi",
    ],
    "medical": [
        "J'ai eu une douleur brutale dans le bas du ventre, je suis pliée en deux",
        "d'un coup j'ai super mal à droite",
        "j'ai trop mal d'un coup, jpeux plus marcher",
        "Une douleur soudaine et très forte côté gauche",
        "J'ai une douleur atroce à droite depuis une heure",
        "j'arrive plus à respirer tellement j'ai mal",
        "jvomis sans arrêt et j'ai super mal",
        "mon kyste a éclaté je crois, j'ai hyper mal",
        "je me suis évanouie en cours ce matin",
        "évanouie 2 fois aujourd'hui",
        "jsuis tombée dans les pommes au taf",
        "J'ai perdu connaissance quelques secondes pendant mes règles",
        "j'ai fait un malaise dans le métro",
        "Je saigne énormément depuis ce matin",
        "je change de serviette toutes les heures et ça déborde",
        "je dois changer mon tampon toutes les 30 min",
        "je saigne de ouf ça s'arrête pas",
        "Je crois que je fais une hémorragie",
        "jme vide de mon sang",
        "J'ai 39,5 de fièvre et très mal au bas-ventre",
        "fièvre + douleur pelvienne depuis hier",
        "Je suis peut-être enceinte et j'ai très mal d'un côté",
        "j'ai du retard de règles et une douleur à gauche qui empire",
        "test de grossesse positif et je saigne",
        "chui enceinte je crois et jai trop mal au ventre",
        "J'ai une grosse hémorragie",
        "hémorragie depuis ce matin, je fais quoi",
        "je fais des hémorragies pendant mes règles là je saigne partout",
        "je perds énormément de sang depuis 2h",
        "je pense faire une grossesse extra-utérine, j'ai très mal",
    ],
    "minor": [
        "J'ai 14 ans et mon beau-père me frappe",
        "mon père me tape quand il a bu",
        "ma mère me bat",
        "j'ai été violée",
        "il y a des attouchements à la maison",
        "je suis en danger chez moi",
        "on me force à faire des trucs que je veux pas",
        "mon copain de lycée me force",
    ],
}

# First-person emergencies that must also trigger for the GP profile (where the medical
# red-flag patterns are off, see patterns.py).
GP_EMERGENCIES = {
    "psychological": [
        "je veux en finir",
        "J'ai envie que tout s'arrête.",
        "Je pense à me suicider.",
        "j'ai avalé toute la boîte de Doliprane",
    ],
    "minor": ["mon mari me frappe", "j'ai été violée"],
}

# Normal questions: the demo storyline and corpus topics, including near misses.
NORMAL = [
    "J'ai super mal au ventre pendant mes règles, au point de rater les cours, et le "
    "Doliprane me fait rien. C'est normal ?",
    "Et je dois aller voir qui ? Ma généraliste ou direct un gynéco ?",
    "On m'a dit qu'il faut se faire opérer pour savoir. Et mon écho était normale, donc j'ai "
    "rien ?",
    "Franchement dis-moi juste si j'ai une endométriose. Pose-moi des questions et donne-moi "
    "un score.",
    "Le test salivaire de TikTok, je peux l'acheter en pharmacie ?",
    "Je suis diagnostiquée et je rate souvent le boulot. J'ai droit au 100 % ? Et la RQTH, "
    "ça sert à quoi ?",
    "Les culottes menstruelles sont remboursées depuis octobre, c'est vrai ?",
    "Quels signes d'appel doivent faire évoquer une endométriose, et quelle imagerie en "
    "première intention ?",
    "Ma patiente a 24 ans, je lui prescris quoi ?",
    "J'ai super mal pendant mes règles, c'est normal ?",
    "Mes règles sont très douloureuses, c'est normal ?",
    "Mes douleurs sont insupportables pendant mes règles, est-ce que c'est l'endométriose ?",
    "Les douleurs violentes pendant les règles sont-elles un signe d'endométriose ?",
    "J'ai des saignements abondants pendant mes règles, c'est un symptôme ?",
    "J'ai souvent envie de vomir pendant mes règles, c'est lié ?",
    "J'ai mal à droite au moment de l'ovulation, c'est quoi ?",
    "J'ai mal pendant les rapports, est-ce que ça peut venir de l'endométriose ?",
    "Je n'arrive pas à me lever le matin pendant mes règles tellement j'ai mal",
    "Peut-on tomber enceinte avec une endométriose ?",
    "Est-ce que la grossesse soulage les douleurs de l'endométriose ?",
    "J'aimerais être enceinte mais j'ai mal pendant les rapports, que faire ?",
    "C'est quoi l'ALD 31 et comment l'obtenir ?",
    "Est-ce que je peux avoir un aménagement de poste au travail ?",
    "Quels sont les traitements hormonaux de l'endométriose ?",
    "La pilule en continu, ça marche contre les douleurs ?",
    "Le stérilet hormonal, c'est une bonne option ?",
    "Quels examens pour diagnostiquer une endométriose ?",
    "L'IRM pelvienne est-elle plus fiable que l'échographie ?",
    "Combien de temps faut-il en moyenne pour être diagnostiquée ?",
    "Est-ce que l'endométriose rend infertile ?",
    "Qu'est-ce que la FIV et quand la proposer ?",
    "J'ai hâte d'en finir avec ces douleurs, quels traitements existent ?",
    "Mes règles me tuent chaque mois, que faire ?",
    "Je suis crevée tout le temps, la fatigue fait partie de l'endométriose ?",
    "Est-ce que le sport aide à avoir moins mal ?",
    "Une alimentation anti-inflammatoire peut-elle aider ?",
    "L'endométriose peut-elle toucher la vessie ou l'intestin ?",
    "Qu'est-ce qu'un endométriome ?",
    "Quels signes d'appel doivent faire adresser une patiente en centre expert ?",
    "Mon médecin me dit que c'est dans ma tête, que faire ?",
    "Ma mère me dit que c'est normal d'avoir mal",
    "Ça fait des années que j'ai mal, ça va finir par s'arrêter ?",
    "Les douleurs peuvent-elles durer après la ménopause ?",
    "Est-ce que l'endométriose est une maladie grave ?",
    "Bonjour, merci pour vos réponses !",
    # Hormonal treatments stop periods: no periods is not a pregnancy cue.
    "Avec le Visanne j'ai pas eu mes règles depuis 6 mois mais j'ai encore mal, c'est normal ?",
    "Sous pilule en continu j'ai pas eu mes règles, et j'ai parfois mal au ventre, c'est grave ?",
    # Medical gaslighting and risk-factor questions are not violence in progress.
    "Je me sens maltraitée par les médecins qui ne me croient pas",
    "La maltraitance gynécologique, ça existe ?",
    "Les violences sexuelles dans l'enfance augmentent-elles le risque de douleurs pelviennes ?",
    # Ordinary descriptions of period pain.
    "La douleur arrive d'un coup au début des règles, c'est normal ?",
    "J'ai mal au ventre pendant mes règles et parfois un peu de fièvre, c'est lié ?",
    "Est-ce qu'une endométriose provoque des hémorragies ?",
    "J'ai avalé deux comprimés de Doliprane, ça suffit ?",
    "J'ai hâte d'en finir avec l'errance diagnostique",
]

# GP guideline questions that name red flags (storyline turns 9 and 10 and near misses).
GP_NORMAL = [
    "Quels signes d'appel doivent faire évoquer une endométriose, et quelle imagerie en "
    "première intention ?",
    "Ma patiente a 24 ans, je lui prescris quoi ?",
    "Conduite à tenir devant une douleur pelvienne brutale chez une patiente ?",
    "Quels signes de gravité : fièvre et douleur pelvienne, quand adresser aux urgences ?",
    "Risque suicidaire chez les patientes endométriosiques : que disent les recommandations ?",
    "Une patiente a un test de grossesse positif et des douleurs : quelle échographie ?",
    "Comment repérer des violences sexuelles chez une patiente qui a des douleurs pelviennes ?",
    "Hémorragie, torsion d'annexe, kyste rompu : quels signes imposent une échographie urgente ?",
]

CHECKS = {profile: KeywordSafetyCheck(profile) for profile in ("patient", "gp")}


def check(text: str, profile: str = "patient"):
    return asyncio.run(CHECKS[profile].check(text))


def test_regression_lists_are_large_enough():
    assert sum(len(phrases) for phrases in EMERGENCIES.values()) >= 40
    assert len(NORMAL) >= 40


@pytest.mark.parametrize(
    ("kind", "text"), [(kind, text) for kind, texts in EMERGENCIES.items() for text in texts]
)
def test_emergency_phrasing_triggers(kind, text):
    decision = check(text)
    assert decision.emergency, text
    assert decision.kind == kind
    assert decision.matched
    assert decision.source == "keyword"


@pytest.mark.parametrize(
    ("kind", "text"), [(kind, text) for kind, texts in GP_EMERGENCIES.items() for text in texts]
)
def test_gp_first_person_emergency_triggers(kind, text):
    decision = check(text, "gp")
    assert decision.emergency, text
    assert decision.kind == kind


@pytest.mark.parametrize(
    ("profile", "text"), [("patient", t) for t in NORMAL] + [("gp", t) for t in GP_NORMAL]
)
def test_normal_question_does_not_trigger(profile, text):
    decision = check(text, profile)
    assert not decision.emergency, decision.matched
    assert decision.kind is None
    assert decision.matched == []


def test_normalize_removes_accents_case_punctuation_and_repeats():
    text = "  J\u2019AI envie de MOURIRRR !!  Évanouie… "  # curly apostrophe
    assert normalize(text) == "j ai envie de mourir evanouie"


def test_storyline_turn_8_reports_every_matched_pattern():
    decision = check(EMERGENCIES["psychological"][0])
    assert decision.matched == ["everything_stop", "pain_with_vomiting"]

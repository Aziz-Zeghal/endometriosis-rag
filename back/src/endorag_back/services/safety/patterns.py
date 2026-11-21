"""French emergency patterns for the keyword safety check.

ILLUSTRATIVE ONLY: this list has not been reviewed by a health professional and must be
validated by one before any real use. The tier-1 regression lists (`test_safety_keyword.py`)
pin its behaviour: every emergency phrasing there must match, no normal question may.

Patterns run on normalized text (see `keyword_check.normalize`): lowercase, no accents,
apostrophes and punctuation turned into spaces, runs of 3+ identical letters collapsed.
So "J'ai" is written `j ?ai` and "s'arrête" `s ?arrete`.

Choices worth a review:
- Pain words alone ("insupportable", "atroce") do not trigger: they are the everyday
  vocabulary of painful periods, the core use case. They trigger with an acute marker
  (sudden onset, one side, vomiting, fever, possible pregnancy, cannot walk or breathe).
- Pregnancy only counts in the first person ("je suis enceinte"), so questions such as
  "peut-on tomber enceinte avec une endométriose ?" stay normal. Missed periods alone do
  not count: they are the expected effect of continuous hormonal treatment. Ectopic
  pregnancy counts only in the first person ("je pense faire une grossesse extra-utérine").
- "en finir avec ces douleurs" is not suicidal; "en finir" alone or "avec cette vie" is.
- "d'un coup" alone is how period pain often starts; it triggers only with one side.
- Violence and abuse count only in the first person ("mon père me frappe", "j'ai été
  violée"), so questions on medical gaslighting or on risk factors stay normal. They map to
  `minor` (the 119 line of the message); the fixed message also gives 15 / 112.
- Profiles: the GP assistant answers guideline questions that name red flags ("conduite à
  tenir devant une douleur pelvienne brutale", "risque suicidaire"), so for `gp` only the
  first-person patterns apply; medical red flags there are left to the LLM check.
"""

from endorag_ingestion.core.settings import Profile

from endorag_back.services.safety.base import EmergencyKind

PAIN = r"\b(?:mal|douleurs?|souffre)\b"
SEVERE = r"\b(?:horrible|atroce|insupportable|insoutenable|intenable|terrible)\b"
SUDDEN = r"\b(?:brutale?(?:ment)?|soudaine?(?:ment)?|subite?(?:ment)?|fulgurante?)\b"
ABRUPT = r"\bd ?un (?:seul )?coup\b"
SIDE = r"\b(?:a droite|a gauche|cote droit|cote gauche|d ?un (?:seul )?cote)\b"
FEVER = r"(?:(?<!un peu de )(?<!petite )\bfievre\b|\b(?:39|40|41)(?: \d)? ?(?:°|degres?\b))"
PREGNANT = (
    r"\b(?:(?:je suis|suis|chui|jsuis)(?: peut etre| surement| sans doute)? enceinte"
    r"|enceinte je (?:crois|pense)|(?:pense|crois) (?:etre|que je suis) enceinte"
    r"|retard de regles|regles en retard|regles ont du retard|j ?ai du retard"
    r"|test (?:de grossesse )?positif"
    r"|(?:pense|crois) faire une grossesse extra uterine|je fais une grossesse extra uterine)\b"
)
WINDOW = r".{0,80}"


def either_order(a: str, b: str, window: str = WINDOW) -> str:
    """`a` then `b`, or `b` then `a`, at most `window` apart (the parts carry their own `\\b`)."""
    return rf"(?:{a}{window}{b}|{b}{window}{a})"


PATIENT: frozenset[Profile] = frozenset({"patient"})
ALL: frozenset[Profile] = frozenset({"patient", "gp"})

# (label, kind, regex, profiles). The first matching pattern gives the decision's kind.
PATTERNS: list[tuple[str, EmergencyKind, str, frozenset[Profile]]] = [
    # Suicidal thoughts and self-harm, direct and indirect.
    ("suicide", "psychological", r"\bsuicid\w*", PATIENT),
    (
        "wish_to_die",
        "psychological",
        r"\b(?:envie|envi|j?veux|veut|voudrais|prefere(?:rais)?) (?:de )?"
        r"(?:mour+ir|crever|disparaitre|plus me reveiller)\b",
        ALL,
    ),
    (
        "kill_myself",
        "psychological",
        r"\b(?:j?vais|envie de|j?veux) me (?:tuer|pendre)\b|\bme foutre en l ?air\b"
        r"|\bme suicid\w*",
        ALL,
    ),
    (
        "end_it",
        "psychological",
        # "en finir avec ces douleurs" is not suicidal: the object is a symptom.
        r"\ben finir\b(?! avec (?:\w+ ){0,2}(?:douleurs?|mal|regles|crises?|endo\w*"
        r"|symptomes?|souffrances?|traitements?|errance|attente|fatigue)\b)"
        r"|\bmettre fin a (?:mes jours|ma vie)\b",
        ALL,
    ),
    (
        "everything_stop",
        "psychological",
        r"\b(?:que|ke) tout (?:s ?ar+et+e|cesse|finisse)\b",
        ALL,
    ),
    (
        "no_will_to_live",
        "psychological",
        r"\bplus (?:envie|envi|la force|le courage) (?:de )?vivre\b"
        r"|\b(?:veux|veut|voudrais) plus vivre\b|\bmarre de la vie\b|\bmieux sans moi\b",
        ALL,
    ),
    (
        "self_harm",
        "psychological",
        r"\bme faire du mal\b|\bscarifi\w*|\bautomutil\w*|\bme mutiler\b",
        ALL,
    ),
    (
        "overdose",
        "psychological",
        r"\bavale\w* (?:tou(?:t|te|s|tes) )?(?:la |les |mes |une |des |plusieurs )?"
        r"(?:boites?|plaquettes?)\b"
        r"|\bavale\w* tou(?:s|tes) (?:mes |les )(?:cachets|comprimes|medicaments|medocs)\b",
        ALL,
    ),
    # Children and young people in danger, violence (119).
    (
        "violence",
        "minor",
        r"\b(?:il|elle|ils|elles|on|(?:mon|ma|mes)(?: \w+){1,3}) me "
        r"(?:frappe(?:nt)?|bat(?:tent)?|tape(?:nt)?|viole(?:nt)?|force(?:nt)?|menace(?:nt)?"
        r"|maltraite(?:nt)?)\b",
        ALL,
    ),
    (
        "sexual_violence",
        "minor",
        r"\b(?:j ?ai ete|je me suis fait e?|on m ?a|il m ?a|elle m ?a) violee?\b"
        r"|\b(?:je subis|j ?ai subi|je suis victime d ?)(?: des?| une?)? ?"
        r"(?:abus|agressions?|violences?|attouchements?)\b",
        ALL,
    ),
    ("abuse_at_home", "minor", r"\battouchements?\b|\binceste\b", PATIENT),
    (
        "in_danger",
        "minor",
        r"\bje suis en danger\b|\bje suis battue?\b|\bje (?:subis|vis) des violences\b",
        ALL,
    ),
    # Acute medical signs.
    ("sudden_pain", "medical", either_order(PAIN, SUDDEN, r".{0,40}"), PATIENT),
    (
        "severe_one_sided_pain",
        "medical",
        either_order(rf"(?:{SEVERE}|{ABRUPT})", SIDE, r".{0,40}"),
        PATIENT,
    ),
    (
        "cannot_walk_or_breathe",
        "medical",
        r"(?:peux|peu|arrive) (?:plus|meme plus) (?:a )?(?:marcher|bouger|respirer|tenir debout)",
        PATIENT,
    ),
    (
        "pain_with_vomiting",
        "medical",
        either_order(SEVERE, r"\bje vomis\b") + r"|vomi\w* sans arret|arrete pas de vomir",
        PATIENT,
    ),
    (
        "fainting",
        "medical",
        r"evanoui\w*|\b(?:perdu|perte de|perds|perdre) connaissance\b"
        r"|\btomb\w* dans les (?:pommes|vapes)\b|\bfai[st] un malaise\b",
        PATIENT,
    ),
    (
        "heavy_bleeding",
        "medical",
        # Hemorrhage in the first person or as a current state, not "l'endométriose
        # provoque-t-elle des hémorragies ?".
        r"\b(?:une|grosses?)(?: grosses?| fortes?)? hemorragi\w*"
        r"|\b(?:je fais|j ?ai|fais)(?: \w+){0,2} hemorragi\w*|^hemorragi\w*"
        r"|\bhemorragi\w* depuis\b"
        r"|\bje saigne (?:enormement|beaucoup trop|trop|abondamment|sans arret"
        r"|a flot|de ouf|grave|comme jamais|partout)\b|me vide de mon sang\b|\bpisse le sang\b"
        r"|\bperds? (?:enormement|beaucoup|trop) de sang\b"
        r"|\bsaign\w*\b.{0,30}\bs ?ar+et+e(?:nt)? (?:pas|plus)\b",
        PATIENT,
    ),
    (
        "protection_every_hour",
        "medical",
        either_order(
            r"\b(?:serviettes?|tampons?|protections?|cups?|coupes?)\b",
            r"\b(?:toutes les|chaque) (?:heures?|h|demi heures?|30 ?min\w*)\b",
            r".{0,50}",
        ),
        PATIENT,
    ),
    ("fever_with_pain", "medical", either_order(FEVER, PAIN), PATIENT),
    (
        "pain_possible_pregnancy",
        "medical",
        either_order(PREGNANT, rf"(?:{PAIN}|\bsaign\w*)"),
        PATIENT,
    ),
    (
        "torsion_or_rupture",
        "medical",
        r"\btorsion (?:de l ?ovaire|d ?ovaire|ovarienne)\b"
        r"|\bkyste (?:qui )?(?:a )?(?:eclate|rompu|perce)\b",
        PATIENT,
    ),
]

# Scope

## Problem

Endometriosis affects roughly one in ten people who menstruate, and diagnosis takes about
seven years on average in France. Reliable information exists (public health agencies,
patient associations, clinical guidelines) but is scattered across many sites and formats,
written for different audiences, and hard to search with lay vocabulary
("règles douloureuses" vs "dysménorrhée").

## What we build

A **French-language question-answering assistant** grounded in a curated corpus of
authoritative documents. It answers questions about symptoms, the diagnostic pathway,
treatments, fertility and daily life, and **always cites the passages it used**.

The tool is designed to be **generic**: corpus, user profile and prompts are configuration,
not code.

## Primary user: patients

The deployment scenario, personas and demo storyline are in [scenario.md](scenario.md).

- People diagnosed with, or suspecting, endometriosis, and their relatives.
- Typical needs: understand a symptom, prepare a consultation, understand a treatment,
  know their rights (ALD, work accommodations), fertility questions.
- Constraints: lay vocabulary, possible distress, chronic pain, mobile usage.

## Generalization: general practitioners

The same system, with a different corpus (HAS 2017 recommendations, 2025 imaging update,
ESHRE 2022 guideline) and a different profile (prompt register, refusal wording), becomes a
**guideline lookup assistant for GPs**: information retrieval from the HAS and ESHRE
recommendations, for example on red flags and referral criteria. Architecture and code are unchanged; only the profile
configuration differs. See [architecture.md](architecture.md#profiles).

## Guardrails (non-negotiable behaviour)

| Rule | Behaviour |
|---|---|
| **Emergency first** | Any sign of a medical emergency or of suicidal thoughts short-circuits everything: a fixed message pointing to **15 / 112**, **114** (by SMS, for deaf and hard-of-hearing people) **3114** (suicide prevention) or **119** (children and young people in danger). There is no retrieval and no LLM generation. Urgent but non-life-threatening situations also mention **116 117** (out-of-hours GP). |
| **No diagnosis** | The assistant never says whether the user has (or does not have) endometriosis. It may describe what the sources say about symptoms and always refers to a health professional. |
| **No prescription** | No dosage, no treatment choice for the user. General information about treatment classes only, from the sources. |
| **Grounded or silent** | Answers only from retrieved passages. If retrieval is insufficient, the assistant either asks a clarifying question or declines and points to a professional. |
| **Always cite** | Every answer lists its sources (organisation, title, date, link). |
| **Out of scope** | Off-topic requests are politely declined. |
| **Persistent disclaimer** | The UI always states that answers are general information drawn from the cited sources, are not medical advice, and that 15 / 112 apply in an emergency. |

### Fixed emergency message (draft, to be reviewed by a health professional)

> Ce que vous décrivez peut nécessiter une prise en charge urgente.
> **Appelez le 15 (SAMU) ou le 112.** Si vous êtes sourde, malentendante ou ne pouvez pas
> parler : **114** (SMS). Si vous avez des pensées suicidaires : **3114**, gratuit, 24 h/24.
> Si vous êtes mineure et en danger, ou inquiète pour un enfant : **119**, gratuit, 24 h/24.
> Je suis un assistant d'information et je ne peux pas évaluer une urgence.

## Regulatory position

The assistant is an **information retrieval tool**. It does not support individual
clinical decisions and is not intended to be a medical device. Any move towards symptom
assessment or diagnosis support would change that status (EU MDR) and is explicitly out of
scope.

## Out of scope for the demo

User accounts, conversation persistence, personalization, symptom journals, any storage of
user health data. These are listed as product improvements in
[local-vs-production.md](local-vs-production.md#improvement-backlog).

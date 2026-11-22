# Design system

The visual direction for the chat widget and the fictional campaign page. It comes from the
ui-ux-pro-max skill (v2.15.0). Its recommendations were adapted to WCAG AA, to an
embedded widget and to a slow network.

## Sources (skill queries)

| Query | Result used |
|---|---|
| `"public health information chatbot calm trustworthy accessible" --design-system --variance 3 --motion 2 --density 4` | Style **Minimalism & Swiss** (low cost, low accessibility risk: contrast 4.5:1, keyboard, visible focus, reduced motion); pattern **Minimal single column** (one primary CTA, whitespace, mobile first); typography **Atkinson Hyperlegible**; navy ink `#0F172A` with slate neutrals; anti-patterns: ornate design, low contrast, heavy motion, purple/pink AI gradients |
| `"healthcare women's health information" --domain color` | Healthcare App palette: "calm cyan + health green". Its cyan `#0891B2` reaches only 3.6:1 with white, so it was darkened to `#0E6A75` (6.3:1) |
| `"healthcare government accessible" --domain typography` | Accessibility First (Atkinson Hyperlegible) over Corporate Trust (Lexend + Source Sans 3): one family, made for legibility, and nothing extra to download |
| `"chat streaming loading indicator" --domain ux` | Stream tokens and show a stable waiting indicator with `aria-busy`, not a spinner |
| `"error feedback color not only" --domain ux` | Every state has a text or icon as well as a colour; error messages say what to do |
| `"alert emergency danger" --domain ux` | No match, even after one retry. The emergency treatment follows the skill's general rules (colour-not-only, touch targets, `role="alert"`) |

## Tokens

The same values are used in both places: the widget (`src/widget/widget.css`, Tailwind
`@theme`, inside the shadow root) and the page (`src/page/page.css`, custom properties).

| Role | Value | Use | Contrast |
|---|---|---|---|
| `ink` | `#0F172A` | body text | 17.8:1 on white |
| `ink-2` | `#334155` | secondary text, publishers | 10.3:1 |
| `muted` | `#475569` | hints, dates, helper text | 7.6:1 on white, 7.0:1 on canvas, 6.6:1 on tint |
| `line` | `#DCE3E8` | decorative dividers only | n/a |
| `line-strong` | `#7A8A9C` | control boundaries (composer field) | 3.5:1 (non-text, ≥ 3:1) |
| `canvas` | `#F3F7F8` | conversation background, footer | n/a |
| `accent` | `#0E6A75` deep teal (`data-accent` overrides it) | bubble, header, user bubbles, send button, links | 6.3:1 with white |
| `accent-strong` | accent mixed 80 % with black (`#0B5563` on the page) | hover states | 8.4:1 with white |
| `accent-soft` | accent at 10 % on white | citation chips, clarify badge, suggestion hover | accent text on it 5.6:1 |
| `notice` / `notice-ink` | `#FFF6DB` / `#713F12` | fictional-scenario banner, recoverable errors | 8.0:1 |
| `danger` / `danger-soft` | `#B91C1C` / `#FEF2F2` | **emergency only**: route badge, alert card, helpline links and actions | 6.5:1 with white, 5.9:1 on soft |

Red is kept for emergencies. A failed request is shown in the amber notice colour, not
in red, so an ordinary error does not look like an emergency. With a custom `data-accent`,
the rules in `docs/architecture.md` still apply: text drawn on white uses the accent mixed
40/60 with the ink.

**Typography.** The font stack is "Atkinson Hyperlegible Next", then "Atkinson
Hyperlegible", then system-ui, -apple-system, "Segoe UI", Roboto, "Noto Sans" and
sans-serif. No font is fetched at runtime, in the widget or on the page, because the network
is slow and the widget must not depend on a CDN. A host that already loads Atkinson gets it
inside the shadow root too, since `@font-face` rules declared on the document apply there.
Every font in the fallback list covers French diacritics, including « », œ and the narrow
no-break space. Sizes: body text at 16 px in the widget (so iOS does not zoom on focus) and
17 px on the page. Captions are at least 12 px (badges only); helper text and the emergency
sub-labels are 13–14 px. Every size in the widget is in px: Tailwind's rem values are turned
into px when the CSS is injected, because rem follows the host page's root font size even
inside a shadow root. Line height is 1.55 in the widget and 1.6
on the page. Weights are 400 for body text, 700 for labels and headings, and 800 for the
hero title.

**Spacing and radius.** Spacing follows a 4/8 px rhythm (Tailwind's scale). Radii: 8 px
for small items, 12 px for cards, suggestions and source cards, 16 px for message bubbles
and page cards, 20 px for the desktop panel, and fully round for the bubble, badges and
buttons.

**Motion.** The panel enters over 200 ms (fade plus 12 px rise) and messages over 200 ms
(fade plus 4 px), with a decelerating `cubic-bezier(0.2, 0, 0, 1)`. Press feedback takes
120 to 150 ms (colour, and a scale of 0.95 to 0.98 that does not move the layout). While
waiting, three dots pulse over 1.2 s. With `prefers-reduced-motion: reduce`, every
animation and transition is turned off: the dots stay still and the panel appears at once.

**Icons.** Inline SVG on a 24 px grid with a 2 px round stroke, all in one style
(`src/widget/icons.tsx`, plus inline SVG on the page). Icons placed next to text use
`aria-hidden`. No emoji, no icon library, and no logo: the page's "+" mark is a generic
shape drawn for the fictional body.

## Components

| Component | Treatment |
|---|---|
| Bubble | Accent pill, 48 px high, chat icon and « Poser une question », kept clear of the safe area |
| Panel | Full screen below 640 px (header padded for the safe area), 420 × 720 px card on desktop |
| Header | Accent background, 16 px title, solid white profile badge with accent text (« Grand public » / « Pro santé », short enough to stay on the title line down to 375 px), 44 px close button whose focus ring takes the header's text colour |
| Banner | Amber note with an info icon. Before the first question: the full scenario text, with « Urgence : 15 ou 112. » in bold. After it: one line, « Scénario fictif · pas un avis médical · Urgence : 15 / 112 », with a 44 px toggle (`aria-expanded`) for the full text. 15 and 112 are `tel:` links in both forms |
| Empty state | Open-book icon and the intro text, then three suggestions as 48 px cards with a chevron |
| User / assistant | User: accent bubble on the right. Assistant: white card with a border on the canvas |
| Citations `[n]` | Small teal chip (inline, so it stays with the word and the punctuation around it), with a hit area of about 28 × 32 px; activating it scrolls to the source card and focuses it (ring) |
| Source cards | Grouped by document: a column with the citation numbers, then publisher, date (month and year), title link with an external icon, and page links |
| Route badges | Emergency: red with an alert icon. Clarification: teal with a question icon. Not covered by the sources and off-topic: neutral with an info icon. Flags: outlined, with a shield icon |
| Clarify / refusal | Card with a 4 px left rule (teal for clarify, slate for refusals): calm, never alarming |
| Emergency | 2 px red border on a soft red card, `role="alert"`. Helpline numbers in the text are red links. Below them, a 2 × 3 grid of 48 px actions, one per number of the fixed message: 15 SAMU (filled), 112, 114 by SMS (`sms:`), 3114, 119, 116 117. No « Réessayer » under it. Once it has arrived, the thread shows the start of the message (badge and « Appelez le 15 »), not its end |
| Loading | Pulsing dots with « Recherche dans les sources… », then « Rédaction de la réponse… » once the sources have arrived |
| Composer | Field with a 3:1 border and a focus ring, 44 px send button (accent) or stop button (ink), privacy helper text with a shield icon |
| Stop / retry | « Réponse interrompue. » with the stop icon; « Réessayer » as a 44 px pill (not under the emergency message) |
| Long answers | When an answer ends and is taller than the thread, the thread scrolls to the start of the answer |
| French spacing | UI strings use a no-break space before « : » and a narrow one before « ? ! ; ». Answer text gets the same treatment at display time (`frenchSpacing` in `parts.ts`), which also keeps « 24 h » and a citation chip with the text before it |
| Error | Amber box with an alert icon: « La réponse n'a pas pu être obtenue. Réessayez dans un instant. », then the retry button |
| Host page | Skip link, notice strip, generic wordmark, light teal hero with one primary CTA, QR poster card, awareness column with checkmark list, emergency box in red with the numbers as 48 px call buttons (15, 112, 114 by SMS, 3114, 119), two entry cards (patient and « Espace professionnels »), footer with the fictional-scenario notice |

## Pre-delivery checklist (skill: `references/pro-rules.md`)

Checked on 2026-11-21 against the mock server, in headless Chromium at 1280 × 800 and
375 × 740: empty state, waiting, sourced answer, refusal, clarify, emergency (phone) and a
failed request (GP).

| Item | Result |
|---|---|
| Only relevant searches; `quick-reference.md` §1–§3 reviewed | Pass |
| Tested at 375 px | Pass: no horizontal scroll (`scrollWidth` 375), panel full screen. Landscape was not tested on a device |
| Reduced motion | Pass (in CSS): every animation and transition is off; nothing depends on an animation ending |
| Largest text size | Partial: layouts wrap, with no truncation or fixed heights on text; not tested at 200 % zoom |
| Dark mode | Not applicable: the widget and the page are light only, on purpose. An embedded widget follows a light host page, and a dark variant would need its own contrast pass |
| Touch targets ≥ 44 px | Pass: bubble 48, close 44, send/stop 44, suggestions 48, banner toggle 44, retry 44, emergency actions 48 (every number of the message), page call buttons 48, page buttons 48, nav links 44, page links of source cards 44 high (hit area). Inline citation chips (hit area about 28 × 32 px), inline helpline numbers (about 34 px high) and the banner's 15 / 112 (42 px high) are under 44 px but above the WCAG 2.2 minimum of 24 px, and each has a larger equivalent (the card's title link, the emergency buttons) |
| No emoji as icons; one icon family | Pass |
| Brand assets | Not applicable: no real logos or brands, as the brief requires |
| Press states do not shift the layout | Pass: only colour and `transform: scale` |
| Semantic tokens, no ad-hoc colours | Pass (the white and black used in `color-mix` and on fills are the only literals) |
| Disabled state | Pass: the send button is greyed, `disabled` and `cursor: not-allowed` while the field is empty |
| Focus order and labels | Pass: the focus trap is unchanged, every control has a French label, new-tab links say so, emergency actions have full labels (« Appeler le 15 (SAMU) ») |
| Contrast ≥ 4.5:1 for text, ≥ 3:1 for non-text | Pass: see the token table |
| Colour is never the only signal | Pass: badges carry text and an icon, the emergency card has a badge, `role="alert"` and labelled actions, errors have an icon and text |
| Safe areas; content not hidden behind fixed bars | Pass: the header, the bubble and the composer use `env(safe-area-inset-*)`, and the page footer leaves room for the bubble |
| Readable line length | Pass: the page column is 66ch; the widget is at most 420 px wide |
| Forms | Pass: the field has an accessible label and persistent helper text; the error says what to do |
| Drag, carousels, authentication | Not applicable |
| Skip link (`quick-reference` §1) | Added on the page |

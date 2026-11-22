# Design system

The visual direction for the single-page assistant (the product, `index.html`), the chat
widget (its extension) and the fictional partner page that hosts the widget
(`widget-demo.html`). It comes from the ui-ux-pro-max skill (v2.15.0). Its recommendations
were adapted to WCAG AA, to an embedded widget and to a slow network.

## Sources (skill queries)

| Query | Result used |
|---|---|
| `"public health information chatbot calm trustworthy accessible" --design-system --variance 3 --motion 2 --density 4` | Style **Minimalism & Swiss** (low cost, low accessibility risk: contrast 4.5:1, keyboard, visible focus, reduced motion); pattern **Minimal single column** (one primary CTA, whitespace, mobile first); typography **Atkinson Hyperlegible**; navy ink `#0F172A` with slate neutrals; anti-patterns: ornate design, low contrast, heavy motion, purple/pink AI gradients |
| `"healthcare women's health information" --domain color` | Healthcare App palette: "calm cyan + health green". Its cyan `#0891B2` reaches only 3.6:1 with white, so it was darkened to `#0E6A75` (6.3:1) |
| `"healthcare government accessible" --domain typography` | Accessibility First (Atkinson Hyperlegible) over Corporate Trust (Lexend + Source Sans 3): one family, made for legibility, and nothing extra to download |
| `"chat streaming loading indicator" --domain ux` | Stream tokens and show a stable waiting indicator with `aria-busy`, not a spinner |
| `"error feedback color not only" --domain ux` | Every state has a text or icon as well as a colour; error messages say what to do |
| `"alert emergency danger" --domain ux` | No match, even after one retry. The emergency treatment follows the skill's general rules (colour-not-only, touch targets, `role="alert"`) |

### Single page (2026-11-22)

| Query | Result used |
|---|---|
| `"single-page health information chat assistant" --design-system --variance 3 --motion 2 --density 4` | Style **Minimalism & Swiss** again (same as above), so the tokens stay. Not adopted: the pattern « Hero + Features + CTA » (a marketing landing; here the conversation is the page and the empty state plays the hero), the « messenger blue » palette (no verified reason to leave the teal, which the widget shares and which passes 6.3:1) and Outfit / Work Sans (fetched from Google Fonts: visitor IPs sent to a third party, and less legible than Atkinson Hyperlegible) |
| `"chat app interface" --domain product` | « Chat & Messaging App »: Minimalism & Swiss plus micro-interactions, contrast between sender and receiver bubbles (accent user bubble, white assistant card, as in the widget) |
| `"chat interface message layout" --domain ux` | Use `dvh`, not `100vh`, for a full-height mobile layout (`h-dvh`); no stacked fixed elements (the header and composer are flex rows around one scrolling region, not `position: fixed`) |
| `"line length readability long text" --domain ux` | 65–75 characters per line and a 1.5–1.75 line height: the reading column is `max-width: 42rem` (about 70 characters at 17 px) and answers use 17 px / 1.6 from 640 px up (16 px on phones, so iOS does not zoom on the field) |
| `"readable long-form body text" --domain typography` | Corporate Trust (Lexend + Source Sans 3) and editorial serif pairings; none adopted, for the same reason as above (one family, nothing to download) |
| `"segmented control toggle selected state" --domain ux` | Compact control semantics: native buttons exposing `aria-pressed`, a visible label matching the state, and the state set directly (no dependence on a transition ending) |
| `"focus not obscured" --domain ux` | WCAG 2.2 AA: sticky UI must not cover focus. The header and composer sit outside the scrolling conversation, so they cannot cover a focused element in it |
| `"skip link landmarks" --domain ux` | A skip link (« Aller à la question ») to the question field |
| `"split view side panel detail" --domain ux`, retried as `"master detail split pane" --domain ux` | No match. No desktop side panel for sources: the cards stay under the answer they support, in the reading column |
| `"reduced motion" --domain ux` | Respect `prefers-reduced-motion` (the shared theme turns every animation and transition off) |

### QA fixes (2026-11-22)

| Query | Result used |
|---|---|
| `"chat auto scroll new message start visible" --domain ux` | No relevant match (IME, smooth scroll, persistent errors). Fallback from the skill's `focus-not-obscured` and « scroll content not hidden » rules: when an answer ends with its start above the view, the thread scrolls back to that start, whatever its height |
| `"landscape short viewport header collapse mobile" --domain ux`, with `quick-reference.md` `orientation-support` and `pro-rules.md` « scroll and fixed element coexistence » | Viewport units (`dvh`) only; the landscape rule (« keep layout readable and operable in landscape ») drives the `short` variant (`max-height: 500px`): one-row header without the body's line, one-line banner from the start, tighter composer |
| `"focus order visual order" --domain ux` (no match), then `quick-reference.md` `keyboard-nav` | « Tab order matches visual order »: the header's DOM order is the visual order (brand, « Nouvelle conversation », profile switch), with no CSS `order` |
| `"icon button accessible label" --domain icons` | Most precise icon for the meaning, accessible name on the control: « Nouvelle conversation » uses a plus (not a pen, which reads as « edit ») with a visible label (« Nouvelle » on phones) |
| `"non-text contrast control boundary" --domain ux` (generic match), then `quick-reference.md` §1 | Interactive boundaries at 3:1: suggestion buttons use `line-strong` (3.5:1), like the composer. Source cards are not controls and keep `line` |
| `"text resize rem font size" --domain ux` (generic match), then `quick-reference.md` `dynamic-type` | Support system text scaling: the single page sets its sizes in rem (base `1rem`, `1.0625rem` from 640 px), with the in-between sizes as theme tokens (`text-note` 0.8125rem, `text-card` 0.9375rem, `text-lead` 1.0625rem; named, so no class name holds a rem value the widget would rewrite), so the reader's default font size applies |

## Tokens

The same values are used everywhere: the shared chat theme (`src/chat/theme.css`, Tailwind
`@theme`), imported by the single page (`src/app/app.css`) and by the widget
(`src/widget/widget.css`, inside the shadow root), and the partner page
(`src/page/page.css`, custom properties).

### Assistant (single page and widget), 2026-11-22

The assistant moved from the teal palette to the look of French healthcare booking
platforms: a navy header and welcome band, blue actions, and white cards with soft shadows
on a cool grey page, with no borders. The welcome band holds a large question field, like
the search field of those sites. Answers are white cards under a small « Assistant » label,
and sources look like directory entries: a round publisher badge, the title as a blue link,
then the publisher, the date and the cited pages as chips. The partner page
(`src/page/page.css`) keeps its own teal: it stands for a different site.

| Role | Value | Use | Contrast |
|---|---|---|---|
| `ink` | `#102A43` | body text | 14.4:1 on white, 13.1:1 on canvas |
| `ink-2` | `#334E68` | secondary text, publishers | 8.6:1 |
| `muted` | `#4A5F75` | hints, dates, helper text | 6.6:1 on white, 5.9:1 on canvas |
| `line` | `#D9E2EC` | decorative dividers only | n/a |
| `line-strong` | `#7A8A9C` | control boundaries (composer field) | 3.5:1 (non-text, ≥ 3:1) |
| `canvas` | `#EEF3F8` | page background under the white cards | n/a |
| `navy` / `navy-2` | `#0B2A4A` / `#16406B` | page header, welcome band / profile switch track | white text 14.5:1 / 10.6:1 |
| `on-navy-2` | `#B9CDE3` | secondary text on navy | 8.9:1 |
| `accent` | `#0B6CB8` medical blue (`data-accent` overrides it) | user bubbles, send button, links, source titles | 5.5:1 with white, 4.9:1 on canvas |
| `accent-strong` | accent mixed 80 % with black | hover states | ≥ 7:1 with white |
| `accent-soft` | accent at 9 % on white | citation and page chips, icon circles | accent text on it 4.8:1 |
| `shadow-card` / `shadow-raised` / `shadow-bar` | navy-tinted shadows | cards / welcome field and card hover / bottom composer | n/a |
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
1rem on the page, 1.0625rem (17 px by default) from 640 px. The page has no host, so its
sizes are in rem and follow the reader's default font size. Captions are at least 12 px (badges only); helper text and the emergency
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
(`src/chat/icons.tsx`, plus inline SVG on the partner page). Icons placed next to text use
`aria-hidden`. No emoji, no icon library, and no logo: the page's "+" mark is a generic
shape drawn for the fictional body.

## Components

| Component | Treatment |
|---|---|
| Bubble | Accent pill, 48 px high, chat icon and « Poser une question », kept clear of the safe area |
| Panel | Full screen below 640 px (header padded for the safe area), 420 px wide card on desktop, at most 720 px high and 144 px shorter than the viewport (in px: the widget turns rem into px, class names included), so a host page's header stays visible |
| Header | Accent background, 16 px title, solid white profile badge with accent text (« Grand public » / « Pro santé », short enough to stay on the title line down to 375 px), 44 px close button whose focus ring takes the header's text colour |
| Banner | Amber note with an info icon. Before the first question: the full scenario text, with « Urgence : 15 ou 112. » in bold. After it, and from the start on short viewports (`max-height: 500px`, phone landscape): one line, « Scénario fictif · pas un avis médical · Urgence : 15 / 112 », with a 44 px toggle (`aria-expanded`) for the full text. 15 and 112 are `tel:` links in both forms |
| Empty state | Open-book icon and the intro text, then three suggestions as 48 px cards with a chevron and a 3:1 border (`line-strong`) |
| User / assistant | User: blue bubble on the right. Assistant: « Assistant » label with the mark, then a white card with a soft shadow on the canvas |
| Citations `[n]` | Small blue chip (inline, so it stays with the word and the punctuation around it), with a hit area of about 28 × 32 px; activating it scrolls to the source card and focuses it (ring) |
| Source cards | Grouped by document: a column with the citation numbers, then publisher, date (month and year), title link with an external icon, and page links |
| Route badges | Emergency: red with an alert icon. Clarification: blue with a question icon. Not covered by the sources and off-topic: neutral with an info icon. Flags: outlined, with a shield icon |
| Clarify / refusal | Card with a 4 px left rule (blue for clarify, grey for refusals): calm, never alarming |
| Emergency | 2 px red border on a soft red card, `role="alert"`. Helpline numbers in the text are red links. Below them, a 2 × 3 grid of 48 px actions, one per number of the fixed message: 15 SAMU (filled), 112, 114 by SMS (`sms:`), 3114, 119, 116 117. No « Réessayer » under it. Once it has arrived, the thread shows the start of the message (badge and « Appelez le 15 »), not its end |
| Loading | Pulsing dots with « Recherche dans les sources… », then « Rédaction de la réponse… » once the sources have arrived |
| Composer | Field with a 3:1 border and a focus ring, 44 px send button (accent) or stop button (ink), privacy helper text with a shield icon |
| Stop / retry | « Réponse interrompue. » with the stop icon; « Réessayer » as a 44 px pill under generated answers and errors only: not under the fixed templates (emergency, not covered, off-topic, chitchat), where retrying gives the same text |
| Long answers | When an answer ends with its start above the view (a long answer, or the page footer after it), the thread scrolls back to the start of the answer, and again while the text still grows (smooth streaming catches up after the stream ends), until the reader scrolls or for 3 s |
| French spacing | UI strings use the typographic apostrophe (’), a no-break space before « : » and a narrow one before « ? ! ; ». Answer text gets the same treatment at display time (`frenchSpacing` in `parts.ts`), which also keeps « 24 h » and a citation chip with the text before it |
| Error | Amber box with an alert icon: « La réponse n'a pas pu être obtenue. Réessayez dans un instant. », then the retry button |
| Single page: layout | Full height (`h-dvh`): header, banner, one scrolling conversation, composer. The conversation and composer share a centred reading column (`max-width: 42rem`); the header is wider (`64rem`). Mobile first: on phones the header has two rows (identity and « + Nouvelle », then the profile switch at full width); from 768 px it is one row. DOM order is the visual order (no CSS `order`). Short viewports (phone landscape): one row, no body line, « Pro santé » below 768 px, icon-only « + » (named « Nouvelle conversation »). No side panel |
| Single page: header | White, bottom divider. Generic « + » mark (accent square, not a logo), « Organisme public de prévention en santé (fictif) » at 0.8125rem muted, « Assistant d’information » at 1.125rem bold (`h1`) |
| Profile switch | Two native buttons in a rounded group (`role="group"`, `aria-pressed`), 44 px high: the selected one is filled with the accent, the other is ink on white (hover: accent-soft). Changing it starts a new conversation, writes `?profile=gp` to the URL and is announced in a polite live region |
| Nouvelle conversation | Outlined pill, 44 px, plus icon, label « Nouvelle » on phones (icon only below 360 px and on short viewports) and « Nouvelle conversation » from 640 px (accessible name always « Nouvelle conversation »); starts a new conversation with the same profile and focuses the question field |
| Single page: empty state | `h2` per profile (1.5rem, 1.75rem from 640 px, balanced wrapping), the profile's intro, then the shared suggestion cards (above the fold at 390 × 844), then a white card listing what the assistant does and refuses (sources only; no diagnosis or prescription; emergency numbers 15, 112, 114 by SMS and 3114 as red links), its icons in a fixed 20 px slot so the three texts align |
| Skip link | « Aller à la question », off screen until focused, then a 44 px white pill with the accent text and a shadow |
| Single page: footer | After the messages, inside the conversation, 0.8125rem muted (the thread shows an ended answer from its start, so the footer never replaces it): fictional-scenario notice, ownership of the cited documents, and a discreet link to the widget demo (« Extension : le même assistant intégré en widget sur un site partenaire (démo) ») |
| Partner page (widget demo) | Skip link, notice strip (« Démo de l'extension… », with « Retour à l'assistant »), generic wordmark, light teal hero with one primary CTA, QR poster card, awareness column with checkmark list, emergency box in red with the numbers as 48 px call buttons (15, 112, 114 by SMS, 3114, 119), two entry cards (patient and « Espace professionnels »), footer with the fictional-scenario notice. On phones the page ends with 5 rem of padding so its end clears the floating launcher (which, like any floating launcher, still covers some content while the page scrolls) |

## Pre-delivery checklist (skill: `references/pro-rules.md`)

After the QA fixes (2026-11-22), the single page and the widget demo were re-checked against
the mock server at 1280 × 800, 1440 × 900, 390 × 844, 320 × 568 and in landscape at
844 × 390 and 568 × 320: every ended answer (sourced, emergency, refusal, off-topic, GP,
long) shows its start (answer top at or below the conversation top); 390 × 844 shows the
first suggestion at y ≈ 513 (above the composer); 844 × 390 leaves 189 px to the
conversation (was 129); skip link 44 px high with 16 px side padding; focus order matches
the visual order; the three rule texts start at the same x; no « Réessayer » under fixed
templates; the open widget panel stays below the demo's navigation at 1280 × 800.

The single page was checked on 2026-11-22 against the mock server, in headless Chromium at
1280 × 800 and 375 × 740: empty state (both profiles), sourced answer, emergency, profile
switch (URL and request body) and the widget demo. No horizontal scroll (`scrollWidth`
equals the viewport width), no console error. Its touch targets: profile buttons 44, new
conversation 44, footer link 44 high (hit area), and the shared components below.

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
| Readable line length | Pass: the single page's column is about 70 characters; the partner page column is 66ch; the widget is at most 420 px wide |
| Forms | Pass: the field has an accessible label and persistent helper text; the error says what to do |
| Drag, carousels, authentication | Not applicable |
| Skip link (`quick-reference` §1) | Added on the page |

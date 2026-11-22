// Pure helpers over the backend's stream parts (see back/src/endorag_back/routes/chat/chat.py).

export type Profile = "patient" | "gp";

/** A profile from a `data-profile` attribute or a `?profile=` parameter: `gp`, else `patient`. */
export function parseProfile(value: string | null | undefined): Profile {
  return value === "gp" ? "gp" : "patient";
}

export type Route = "emergency" | "chitchat" | "out_of_scope" | "question" | "clarify" | "refuse";
export type Flag = "asks_for_diagnosis" | "asks_for_prescription";

/** Payload of the `data-route` part (the client keeps the latest one). */
export type RouteData = { type: "route"; route: Route; flags: Flag[] };

/** One item of the `data-sources` part: `id` is the number cited in the answer. */
export type SourceCard = {
  id: number;
  title: string;
  source: string;
  date: string; // ISO date
  url: string; // with #page=N for PDF chunks
  page: number | null;
};

/** Several chunks of one document shown as one card. */
export type SourceGroup = {
  key: string;
  title: string;
  source: string;
  date: string;
  refs: { id: number; url: string; page: number | null }[];
  pages: { page: number; url: string }[]; // one link per distinct page
};

/** French badge text per route; routes without a badge are ordinary answers. */
export const ROUTE_LABELS: Partial<Record<Route, string>> = {
  emergency: "Urgence",
  out_of_scope: "Hors sujet",
  clarify: "Clarification",
  refuse: "Non couvert par les sources",
};

export const FLAG_LABELS: Record<Flag, string> = {
  asks_for_diagnosis: "Pas de diagnostic individuel",
  asks_for_prescription: "Pas de prescription individuelle",
};

/** Groups cards by document (URL without its #page fragment), in order of first citation. */
export function groupSources(cards: SourceCard[]): SourceGroup[] {
  const groups = new Map<string, SourceGroup>();
  for (const c of [...cards].sort((a, b) => a.id - b.id)) {
    const key = c.url.split("#")[0];
    let group = groups.get(key);
    if (!group) {
      group = { key, title: c.title, source: c.source, date: c.date, refs: [], pages: [] };
      groups.set(key, group);
    }
    group.refs.push({ id: c.id, url: c.url, page: c.page });
    if (c.page && !group.pages.some((p) => p.page === c.page)) group.pages.push({ page: c.page, url: c.url });
  }
  return [...groups.values()];
}

/** Keeps the cards whose number the answer cites as [n] (the backend sends every passage
 * given to generation, cited or not). */
export function citedSources(cards: SourceCard[], answer: string): SourceCard[] {
  const cited = new Set([...answer.matchAll(/\[(\d{1,2})\]/g)].map((m) => Number(m[1])));
  return cards.filter((c) => cited.has(c.id));
}

/** "2017-12-01" → "décembre 2017" (sources are often dated to the month). */
export function formatSourceDate(iso: string): string {
  const d = new Date(`${iso}T00:00:00Z`);
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat("fr-FR", { month: "long", year: "numeric", timeZone: "UTC" }).format(d);
}

/** Turns the answer's [n] markers into links to the source cards ("#cite-n"). */
export function linkCitations(markdown: string): string {
  return markdown.replace(/\[(\d{1,2})\](?![(:])/g, "[$1](#cite-$1)");
}

/** Helpline numbers of the fixed emergency messages: 114 is reached by SMS. */
const HELPLINES = /(?<![\d\w])(116 117|3114|112|119|114|15)(?![\d\w])/g;

/** Makes every helpline number a tappable link (tel:, or sms: for 114). */
export function linkHelplines(markdown: string): string {
  return markdown.replace(HELPLINES, (n) => `[${n}](${n === "114" ? "sms" : "tel"}:${n.replace(" ", "")})`);
}

/** Display-only French spacing: a no-break space before « : » and a narrow one before « ? ! ; »
 * and inside « », so punctuation never starts a line; « 24 h » stays on one line, and a
 * citation [n] stays with the word before it. */
export function frenchSpacing(markdown: string): string {
  return markdown
    .replace(/ ([?!;»])/g, " $1")
    .replace(/« /g, "« ")
    .replace(/ :/g, " :")
    .replace(/(\d) h\b/g, "$1 h")
    .replace(/ \[(\d{1,2})\]/g, " [$1]");
}

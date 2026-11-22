import { describe, expect, it } from "vitest";
import {
  citedSources,
  formatSourceDate,
  frenchSpacing,
  groupSources,
  sourceInitials,
  linkCitations,
  linkHelplines,
  parseProfile,
  type SourceCard,
} from "./parts";

const card = (id: number, url: string, page: number | null = null): SourceCard => ({
  id,
  title: `Doc ${url}`,
  source: "HAS",
  date: "2017-12-01",
  url,
  page,
});

describe("parseProfile", () => {
  it("reads gp, and falls back to patient for anything else", () => {
    expect(parseProfile("gp")).toBe("gp");
    expect(parseProfile("patient")).toBe("patient");
    expect(parseProfile("GP")).toBe("patient");
    expect(parseProfile(null)).toBe("patient");
    expect(parseProfile(undefined)).toBe("patient");
  });
});

describe("groupSources", () => {
  it("merges chunks of one document into one card, keeping each page link", () => {
    const groups = groupSources([
      card(1, "https://a.fr/x.pdf#page=2", 2),
      card(2, "https://b.fr/page"),
      card(3, "https://a.fr/x.pdf#page=4", 4),
    ]);
    expect(groups.map((g) => g.key)).toEqual(["https://a.fr/x.pdf", "https://b.fr/page"]);
    expect(groups[0].refs).toEqual([
      { id: 1, url: "https://a.fr/x.pdf#page=2", page: 2 },
      { id: 3, url: "https://a.fr/x.pdf#page=4", page: 4 },
    ]);
  });

  it("lists each page once when two chunks start on the same page", () => {
    const groups = groupSources([card(1, "https://a.fr/x.pdf#page=2", 2), card(2, "https://a.fr/x.pdf#page=2", 2)]);
    expect(groups[0].refs.map((r) => r.id)).toEqual([1, 2]);
    expect(groups[0].pages).toEqual([{ page: 2, url: "https://a.fr/x.pdf#page=2" }]);
  });

  it("orders cards by their first citation number", () => {
    const groups = groupSources([card(2, "https://b.fr"), card(1, "https://a.fr")]);
    expect(groups.map((g) => g.refs[0].id)).toEqual([1, 2]);
  });
});

describe("citedSources", () => {
  it("keeps only the sources the answer cites", () => {
    const cards = [1, 2, 3, 4, 5].map((id) => card(id, `https://a.fr/${id}`));
    expect(citedSources(cards, "Oui [1]. Aussi [3][1].").map((c) => c.id)).toEqual([1, 3]);
  });

  it("keeps none when the answer cites nothing", () => {
    expect(citedSources([card(1, "https://a.fr")], "Pas de source.")).toEqual([]);
  });
});

describe("linkCitations", () => {
  it("links [n] markers to the source cards", () => {
    expect(linkCitations("Vrai [1] et [2][3].")).toBe(
      "Vrai [1](#cite-1) et [2](#cite-2)[3](#cite-3).",
    );
  });

  it("leaves existing Markdown links alone", () => {
    expect(linkCitations("[1](https://x.fr)")).toBe("[1](https://x.fr)");
  });
});

describe("linkHelplines", () => {
  it("makes the emergency numbers tappable, 114 by SMS", () => {
    const text = "**Appelez le 15 (SAMU) ou le 112.** **114** (SMS). **3114**, **119**, **116 117**.";
    expect(linkHelplines(text)).toBe(
      "**Appelez le [15](tel:15) (SAMU) ou le [112](tel:112).** **[114](sms:114)** (SMS). " +
        "**[3114](tel:3114)**, **[119](tel:119)**, **[116 117](tel:116117)**.",
    );
  });

  it("ignores other numbers", () => {
    expect(linkHelplines("24 h/24, 2015, 1150")).toBe("24 h/24, 2015, 1150");
  });
});

describe("formatSourceDate", () => {
  it("shows month and year in French", () => {
    expect(formatSourceDate("2017-12-01")).toBe("décembre 2017");
  });
});

describe("frenchSpacing", () => {
  it("binds French punctuation, « 24 h » and citations to the text before them", () => {
    expect(frenchSpacing("Urgence : 15 ou 112. C'est normal ? Oui ! « mot » ; 24 h/24 soulager [2] ;")).toBe(
      "Urgence : 15 ou 112. C'est normal ? Oui ! « mot » ; 24 h/24 soulager [2] ;",
    );
  });

  it("leaves URLs, Markdown links and the 116 117 number alone", () => {
    const text = "[1](https://x.fr/a:b) **116 117** 2 heures";
    expect(frenchSpacing(text)).toBe(text);
  });
});

describe("sourceInitials", () => {
  it("keeps acronyms, takes initials of several words, else two letters", () => {
    expect(sourceInitials("HAS")).toBe("HAS");
    expect(sourceInitials("ESHRE")).toBe("ESHRE");
    expect(sourceInitials("Service-Public")).toBe("SP");
    expect(sourceInitials("Mon Parcours Handicap")).toBe("MPH");
    expect(sourceInitials("ENDOmind France")).toBe("EF");
    expect(sourceInitials("Santé.fr")).toBe("Sa");
    expect(sourceInitials("Ameli")).toBe("Am");
  });
});

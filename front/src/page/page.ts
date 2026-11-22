// Host page script: the entry buttons and the poster link (?chat=open&profile=…) drive the
// widget through the small API it exposes (window.EndoRAG).
type Profile = "patient" | "gp";

function whenReady(run: (widget: NonNullable<Window["EndoRAG"]>) => void) {
  if (window.EndoRAG) run(window.EndoRAG);
  else window.addEventListener("endorag:ready", () => run(window.EndoRAG!), { once: true });
}

document.querySelectorAll<HTMLAnchorElement>("[data-open-chat]").forEach((link) =>
  link.addEventListener("click", (e) => {
    e.preventDefault();
    whenReady((w) => w.open(link.dataset.openChat as Profile));
  }),
);

const params = new URLSearchParams(location.search);
if (params.get("chat") === "open") {
  whenReady((w) => w.open(params.get("profile") === "gp" ? "gp" : "patient"));
}

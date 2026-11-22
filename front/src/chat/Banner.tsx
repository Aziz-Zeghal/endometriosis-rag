import { useAuiState } from "@assistant-ui/react";
import { useState, useSyncExternalStore } from "react";
import { ChevronIcon, InfoIcon } from "./icons";

// The banner text of docs/scenario.md (French spacing: no-break space before « : »).
const BANNER =
  "Scénario fictif – démonstrateur technique sans lien avec une institution. " +
  "Informations générales tirées des sources citées, pas un avis médical. ";
const BANNER_SHORT = "Scénario fictif · pas un avis médical · ";

const call = (n: string) => (
  <a
    href={`tel:${n}`}
    aria-label={`Appeler le ${n}`}
    className="relative underline underline-offset-2 after:absolute after:-inset-x-1 after:-inset-y-3 after:content-['']"
  >
    {n}
  </a>
);

// Short viewports (phone landscape) keep the one-line banner even before the first question;
// same breakpoint as the `short` variant of theme.css.
const SHORT = window.matchMedia("(max-height: 500px)");
const onShortChange = (l: () => void) => (SHORT.addEventListener("change", l), () => SHORT.removeEventListener("change", l));

/** Full banner before the first question; afterwards one line, with a toggle for the rest,
 * so the conversation keeps the room (the emergency numbers stay visible either way).
 * `column` lays the content out on the page's reading column. */
export function Banner({ column = "" }: { column?: string }) {
  const empty = useAuiState((s) => s.thread.isEmpty);
  const short = useSyncExternalStore(onShortChange, () => SHORT.matches);
  const [more, setMore] = useState(false);
  const collapsible = !empty || short;
  const full = !collapsible || more;
  return (
    <div role="note" className="border-b border-notice-ink/15 bg-notice px-4 py-2 text-note leading-snug text-notice-ink">
      <div className={`flex items-start gap-2 ${column}`}>
        <span className="mt-px shrink-0">
          <InfoIcon />
        </span>
        <p id="endorag-banner" className="min-w-0 flex-1">
          {full ? BANNER : BANNER_SHORT}
          <strong className="whitespace-nowrap">
            Urgence&nbsp;: {call("15")} {full ? "ou" : "/"} {call("112")}
            {full && "."}
          </strong>
        </p>
        {collapsible && (
          <button
            type="button"
            onClick={() => setMore(!more)}
            aria-expanded={more}
            aria-controls="endorag-banner"
            aria-label={more ? "Réduire l’avertissement" : "Afficher l’avertissement complet"}
            className="-my-2.5 -mr-3 grid size-11 shrink-0 place-items-center rounded-full transition-colors duration-150 hover:bg-notice-ink/10"
          >
            <span className={`transition-transform duration-150 ${more ? "-rotate-90" : "rotate-90"}`}>
              <ChevronIcon />
            </span>
          </button>
        )}
      </div>
    </div>
  );
}

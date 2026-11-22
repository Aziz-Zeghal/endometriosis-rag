import { AssistantRuntimeProvider, useAuiState } from "@assistant-ui/react";
import { AssistantChatTransport, useChatRuntime } from "@assistant-ui/react-ai-sdk";
import { useEffect, useMemo, useRef, useState, useSyncExternalStore, type CSSProperties, type KeyboardEvent, type ReactNode } from "react";
import type { WidgetConfig } from "./config";
import { ChatIcon, ChevronIcon, CloseIcon, InfoIcon } from "./icons";
import type { Profile } from "./parts";
import { Thread } from "./Thread";

// Open state and profile live outside React so host pages can drive them (window.EndoRAG).
type UiState = { open: boolean; profile: Profile | null };
let ui: UiState = { open: false, profile: null };
const listeners = new Set<() => void>();
function setUi(next: Partial<UiState>) {
  ui = { ...ui, ...next };
  listeners.forEach((l) => l());
}
const subscribe = (l: () => void) => (listeners.add(l), () => listeners.delete(l));

export const controller = {
  open: (profile?: Profile) => setUi({ open: true, ...(profile && { profile }) }),
  close: () => setUi({ open: false }),
};

/** Applies data-open and data-profile, unless the host page already called open(). */
export function initUi(config: WidgetConfig) {
  setUi({ open: ui.open || config.open, profile: ui.profile ?? config.profile });
}

const PROFILE_LABELS: Record<Profile, string> = {
  patient: "Grand public",
  gp: "Pro santé",
};

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

/** Full banner before the first question; afterwards one line, with a toggle for the rest,
 * so the conversation keeps the room (the emergency numbers stay visible either way). */
function Banner() {
  const empty = useAuiState((s) => s.thread.isEmpty);
  const [more, setMore] = useState(false);
  const full = empty || more;
  return (
    <div role="note" className="flex items-start gap-2 border-b border-notice-ink/15 bg-notice px-4 py-2 text-[13px] leading-snug text-notice-ink">
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
      {!empty && (
        <button
          type="button"
          onClick={() => setMore(!more)}
          aria-expanded={more}
          aria-controls="endorag-banner"
          aria-label={more ? "Réduire l'avertissement" : "Afficher l'avertissement complet"}
          className="-my-2.5 -mr-3 grid size-11 shrink-0 place-items-center rounded-full transition-colors duration-150 hover:bg-notice-ink/10"
        >
          <span className={`transition-transform duration-150 ${more ? "-rotate-90" : "rotate-90"}`}>
            <ChevronIcon />
          </span>
        </button>
      )}
    </div>
  );
}

/** Text colour readable on the accent: ink on light accents, white on dark ones. */
function accentInk(color: string): string {
  const m = /^#([0-9a-f]{6})$/i.exec(color);
  if (!m) return "#ffffff";
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(m[1].slice(i, i + 2), 16) / 255);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b > 0.55 ? "#0f172a" : "#ffffff";
}

function ChatRuntime({ api, profile, children }: { api: string; profile: Profile; children: ReactNode }) {
  const transport = useMemo(
    () => new AssistantChatTransport({ api: `${api}/api/chat`, body: { profile } }),
    [api, profile],
  );
  const runtime = useChatRuntime({ transport });
  return <AssistantRuntimeProvider runtime={runtime}>{children}</AssistantRuntimeProvider>;
}

// The panel covers the page only on phones (Tailwind's sm breakpoint): only there is it modal.
const PHONE = window.matchMedia("(max-width: 639.98px)");
const onPhoneChange = (l: () => void) => (PHONE.addEventListener("change", l), () => PHONE.removeEventListener("change", l));

const FOCUSABLE = 'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])';

export function Widget({ config }: { config: WidgetConfig }) {
  const state = useSyncExternalStore(subscribe, () => ui);
  const { open } = state;
  const profile = state.profile ?? config.profile;
  const panel = useRef<HTMLElement>(null);
  const bubble = useRef<HTMLButtonElement>(null);
  const wasOpen = useRef(open);
  const phone = useSyncExternalStore(onPhoneChange, () => PHONE.matches);

  // Focus the question field on open; give focus back to the bubble on close.
  useEffect(() => {
    if (open) panel.current?.querySelector<HTMLTextAreaElement>("textarea")?.focus();
    else if (wasOpen.current) bubble.current?.focus();
    wasOpen.current = open;
  }, [open, profile]);

  const close = controller.close;

  // Focus trap: Tab cycles inside the open panel, Escape closes it.
  const onKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Escape") return close();
    if (e.key !== "Tab" || !panel.current) return;
    const items = [...panel.current.querySelectorAll<HTMLElement>(FOCUSABLE)].filter((el) => el.offsetParent);
    if (!items.length) return;
    const active = (panel.current.getRootNode() as ShadowRoot).activeElement;
    const [first, last] = [items[0], items[items.length - 1]];
    if (e.shiftKey && active === first) (e.preventDefault(), last.focus());
    else if (!e.shiftKey && active === last) (e.preventDefault(), first.focus());
  };

  // Links, citation numbers and the focus ring sit on white: a custom accent is darkened with
  // the ink for them (40% accent stays above 4.5:1 on white whatever the colour).
  const style = config.accent
    ? ({
        "--endorag-accent": config.accent,
        "--endorag-accent-ink": accentInk(config.accent),
        "--endorag-accent-text": `color-mix(in oklab, ${config.accent} 40%, #0f172a)`,
      } as CSSProperties)
    : undefined;

  return (
    <div className="endorag" style={style}>
      {!open && (
        <button
          ref={bubble}
          type="button"
          onClick={() => controller.open()}
          className="fixed right-4 bottom-[max(16px,env(safe-area-inset-bottom))] z-[2147483000] flex min-h-12 items-center gap-2 rounded-full bg-accent py-3 pr-5 pl-4 font-bold text-accent-ink shadow-[0_8px_24px_-8px_rgb(15_23_42/0.5)] transition-[background-color,transform] duration-150 ease-out hover:bg-accent-strong active:scale-[0.97] sm:right-6 sm:bottom-6"
        >
          <ChatIcon />
          Poser une question
        </button>
      )}
      <ChatRuntime key={profile} api={profile === "gp" ? config.apiGp : config.api} profile={profile}>
        <section
          ref={panel}
          role="dialog"
          aria-modal={phone || undefined}
          aria-labelledby="endorag-title"
          hidden={!open}
          onKeyDown={onKeyDown}
          className="fixed inset-0 z-[2147483000] flex animate-panel-in flex-col overflow-hidden bg-paper sm:inset-auto sm:right-6 sm:bottom-6 sm:h-[min(720px,calc(100dvh-48px))] sm:w-[420px] sm:rounded-[20px] sm:border sm:border-line sm:shadow-[0_24px_64px_-16px_rgb(15_23_42/0.35)]"
        >
          <header className="flex items-start gap-3 bg-accent px-4 pt-[max(14px,env(safe-area-inset-top))] pb-3 text-accent-ink sm:pt-3.5">
            <div className="min-w-0 flex-1">
              <h2 id="endorag-title" className="flex flex-wrap items-center gap-x-1.5 gap-y-1 text-base leading-tight font-bold">
                Assistant d'information
                <span className="rounded-full bg-paper px-2 text-xs leading-6 font-bold text-accent-text">
                  {PROFILE_LABELS[profile]}
                </span>
              </h2>
              <p className="mt-0.5 text-sm opacity-90">Règles douloureuses et endométriose</p>
            </div>
            <button
              type="button"
              onClick={close}
              aria-label="Fermer l'assistant"
              className="-mt-1 -mr-1.5 grid size-11 shrink-0 place-items-center rounded-full transition-colors duration-150 hover:bg-white/15 active:bg-white/25"
            >
              <CloseIcon />
            </button>
          </header>
          <Banner />
          <Thread profile={profile} />
        </section>
      </ChatRuntime>
    </div>
  );
}

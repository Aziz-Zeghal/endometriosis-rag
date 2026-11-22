import { useState, type ReactNode } from "react";
import { Banner } from "../chat/Banner";
import { AlertIcon, BookIcon, PlusIcon, ShieldIcon } from "../chat/icons";
import { parseProfile, type Profile } from "../chat/parts";
import { ChatRuntime } from "../chat/runtime";
import { SUGGESTIONS, Suggestions, Thread } from "../chat/Thread";

// One backend serves both profiles; `VITE_API_URL` points the build at another host.
const API = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");

const PROFILE_LABELS: Record<Profile, string> = {
  patient: "Grand public",
  gp: "Professionnels de santé",
};

// Reading column of the conversation: about 70 characters per line at 17 px.
const COLUMN = "mx-auto w-full max-w-[42rem]";

const focusQuestion = () => requestAnimationFrame(() => document.getElementById("endorag-question")?.focus());

/** The campaign's assistant homepage: one page, one conversation, a profile switch. */
export function App() {
  // ?profile=gp opens the professionals' profile (the link given to GPs and midwives).
  const [profile, setProfile] = useState<Profile>(() => parseProfile(new URLSearchParams(location.search).get("profile")));
  const [conversation, setConversation] = useState(0);
  const [status, setStatus] = useState("");

  const start = (next: Profile) => {
    setProfile(next);
    setConversation((n) => n + 1);
    setStatus(`Nouvelle conversation, profil ${PROFILE_LABELS[next]}.`);
    const url = new URL(location.href);
    if (next === "gp") url.searchParams.set("profile", "gp");
    else url.searchParams.delete("profile");
    history.replaceState(null, "", url);
  };

  return (
    <div className="endorag flex h-dvh flex-col">
      <a href="#endorag-question" className="skip">
        Aller à la question
      </a>
      <header className="border-b border-line bg-paper">
        {/* DOM order = focus order: brand, « Nouvelle conversation », profile switch. Phones wrap
            the switch onto a second row; short viewports (landscape) keep one row. */}
        <div className="mx-auto flex max-w-[64rem] flex-wrap items-center gap-x-4 gap-y-3 px-4 py-3 sm:px-6 short:flex-nowrap short:gap-x-3 short:py-1.5">
          <div className="flex min-w-0 flex-1 items-center gap-3">
            {/* Generic mark drawn for the fictional body: not a real logo. */}
            <svg viewBox="0 0 32 32" aria-hidden="true" className="size-10 shrink-0 short:size-8 short:max-md:hidden">
              <rect width="32" height="32" rx="9" className="fill-accent" />
              <path d="M16 9v14M9 16h14" className="stroke-accent-ink" strokeWidth="3.5" strokeLinecap="round" />
            </svg>
            <div className="min-w-0">
              <p className="text-note leading-snug text-muted short:hidden">
                Organisme public de prévention en santé <span className="whitespace-nowrap">(fictif)</span>
              </p>
              <h1 className="text-lg leading-tight font-bold">Assistant d’information</h1>
            </div>
          </div>
          <button
            type="button"
            aria-label="Nouvelle conversation"
            onClick={() => (start(profile), focusQuestion())}
            className="flex min-h-11 min-w-11 items-center justify-center gap-1.5 rounded-full border border-line-strong px-3 text-sm font-bold text-ink-2 transition-colors duration-150 hover:bg-accent-soft active:bg-accent-soft sm:px-4 short:px-3"
          >
            <PlusIcon />
            <span className="max-[359px]:hidden short:hidden">
              Nouvelle<span className="max-sm:hidden"> conversation</span>
            </span>
          </button>
          <div
            role="group"
            aria-label="Profil"
            className="flex w-full rounded-full border border-line-strong bg-paper p-1 md:w-auto short:w-auto"
          >
            {(Object.keys(PROFILE_LABELS) as Profile[]).map((p) => (
              <button
                key={p}
                type="button"
                aria-pressed={p === profile}
                onClick={() => p !== profile && start(p)}
                className={`min-h-11 flex-1 rounded-full px-4 text-sm leading-tight font-bold transition-colors duration-150 md:whitespace-nowrap short:whitespace-nowrap short:px-3 ${
                  p === profile ? "bg-accent text-accent-ink" : "text-ink-2 hover:bg-accent-soft"
                }`}
              >
                {p === "gp" ? (
                  <>
                    <span className="short:max-md:hidden">{PROFILE_LABELS.gp}</span>
                    <span className="hidden short:max-md:inline">Pro santé</span>
                  </>
                ) : (
                  PROFILE_LABELS[p]
                )}
              </button>
            ))}
          </div>
        </div>
      </header>
      <p className="sr-only" aria-live="polite">
        {status}
      </p>
      <ChatRuntime key={conversation} api={API} profile={profile}>
        <Banner column={COLUMN} />
        <main className="flex min-h-0 flex-1 flex-col">
          <Thread profile={profile} column={COLUMN} empty={<Intro profile={profile} />} footer={<Footer />} />
        </main>
      </ChatRuntime>
    </div>
  );
}

function Rule({ icon, children }: { icon: ReactNode; children: ReactNode }) {
  return (
    <li className="flex gap-3">
      {/* Fixed slot: the three texts start on the same line whatever the icon's drawing. */}
      <span className="mt-0.5 flex w-5 shrink-0 justify-center">{icon}</span>
      <span>{children}</span>
    </li>
  );
}

const tel = (n: string, label: string) => (
  <a href={`tel:${n}`} aria-label={`Appeler le ${n} (${label})`} className="font-bold text-danger underline underline-offset-2">
    {n}
  </a>
);

/** Empty state: the profile's suggestions first (above the fold on phones), then what the
 * assistant does and refuses. */
function Intro({ profile }: { profile: Profile }) {
  const gp = profile === "gp";
  return (
    <div className="pt-2 pb-6 sm:pt-6">
      <h2 className="text-2xl leading-tight font-bold text-balance sm:text-[1.75rem]">
        {gp ? "Les recommandations sur l’endométriose, avec leurs pages" : "Règles douloureuses, endométriose : posez votre question"}
      </h2>
      <p className="mt-3 text-ink-2">{SUGGESTIONS[profile].intro}</p>
      <Suggestions profile={profile} />
      <ul aria-label="Ce que fait l’assistant" className="mt-6 space-y-3 rounded-2xl border border-line bg-paper p-4 text-card leading-snug">
        <Rule icon={<span className="text-accent-text"><BookIcon /></span>}>
          Il répond uniquement à partir de sources publiques citées, avec leur date, et dit quand elles ne couvrent pas la
          question.
        </Rule>
        <Rule icon={<span className="text-accent-text"><ShieldIcon /></span>}>
          {gp
            ? "Il résume les recommandations, sans décision individuelle de diagnostic ou de prescription."
            : "Il ne pose pas de diagnostic et ne prescrit pas de traitement : il vous oriente vers un professionnel."}
        </Rule>
        <Rule icon={<span className="text-danger"><AlertIcon /></span>}>
          <strong>En cas d’urgence</strong>, appelez le {tel("15", "SAMU")} ou le {tel("112", "urgences")}, ou envoyez un
          SMS au{" "}
          <a href="sms:114" aria-label="Envoyer un SMS au 114" className="font-bold text-danger underline underline-offset-2">
            114
          </a>
          . Pensées suicidaires&nbsp;: {tel("3114", "prévention du suicide")}.
        </Rule>
      </ul>
    </div>
  );
}

function Footer() {
  return (
    <footer className="mt-10 space-y-2 border-t border-line pt-4 pb-2 text-note leading-snug text-muted">
      <p>
        <strong>Scénario fictif.</strong> Cette page, l’organisme qui la publie et l’assistant sont imaginaires. Aucun
        ministère, agence, organisme d’assurance maladie, réseau régional, association ou site n’a déployé, financé, relu ou
        approuvé ce démonstrateur.
      </p>
      <p>
        Les documents cités appartiennent à leurs éditeurs (Haute Autorité de Santé, Assurance Maladie, Santé.fr, ESHRE…)
        et ne sont utilisés que pour cette démonstration non commerciale, avec attribution et lien vers l’original.
      </p>
      <p>
        <a
          href="widget-demo.html"
          className="relative inline-flex min-h-6 items-center underline underline-offset-2 after:absolute after:inset-x-0 after:-inset-y-2.5 after:content-[''] hover:text-ink"
        >
          Extension&nbsp;: le même assistant intégré en widget sur un site partenaire (démo)
        </a>
      </p>
    </footer>
  );
}

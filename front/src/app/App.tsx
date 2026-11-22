import { useState, type ReactNode } from "react";
import { Banner } from "../chat/Banner";
import { AlertIcon, BookIcon, Mark, PlusIcon, ShieldIcon } from "../chat/icons";
import { parseProfile, type Profile } from "../chat/parts";
import { ChatRuntime } from "../chat/runtime";
import { Composer, Suggestions, Thread } from "../chat/Thread";

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
      <header data-on-navy className="bg-navy text-white">
        {/* DOM order = focus order: brand, « Nouvelle conversation », profile switch. Phones wrap
            the switch onto a second row; short viewports (landscape) keep one row. */}
        <div className="mx-auto flex max-w-[72rem] flex-wrap items-center gap-x-4 gap-y-3 px-4 py-3 sm:px-6 short:flex-nowrap short:gap-x-3 short:py-1.5">
          <div className="flex min-w-0 flex-1 items-center gap-3">
            <Mark tone="paper" className="size-10 short:size-8 short:max-md:hidden" />
            <div className="min-w-0">
              <p className="text-note leading-snug text-on-navy-2 short:hidden">
                Organisme public de prévention en santé <span className="whitespace-nowrap">(fictif)</span>
              </p>
              <h1 className="text-lg leading-tight font-bold">Assistant d’information</h1>
            </div>
          </div>
          <button
            type="button"
            aria-label="Nouvelle conversation"
            onClick={() => (start(profile), focusQuestion())}
            className="flex min-h-11 min-w-11 items-center justify-center gap-1.5 rounded-full border border-white/40 px-3 text-sm font-bold text-white transition-colors duration-150 hover:bg-white/10 active:bg-white/15 sm:px-4 short:px-3"
          >
            <PlusIcon />
            <span className="max-[359px]:hidden short:hidden">
              Nouvelle<span className="max-sm:hidden"> conversation</span>
            </span>
          </button>
          <div role="group" aria-label="Profil" className="flex w-full rounded-full bg-navy-2 p-1 md:w-auto short:w-auto">
            {(Object.keys(PROFILE_LABELS) as Profile[]).map((p) => (
              <button
                key={p}
                type="button"
                aria-pressed={p === profile}
                onClick={() => p !== profile && start(p)}
                className={`min-h-11 flex-1 rounded-full px-4 text-sm leading-tight font-bold transition-colors duration-150 md:whitespace-nowrap short:whitespace-nowrap short:px-3 ${
                  p === profile ? "bg-paper text-navy shadow-card" : "text-on-navy-2 hover:bg-white/10 hover:text-white"
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
          <Thread profile={profile} column={COLUMN} empty={<Intro profile={profile} />} footer={<Footer />} welcomeComposer />
        </main>
      </ChatRuntime>
    </div>
  );
}

const tel = (n: string, label: string) => (
  <a href={`tel:${n}`} aria-label={`Appeler le ${n} (${label})`} className="font-bold text-danger underline underline-offset-2">
    {n}
  </a>
);

function Feature({ icon, title, danger = false, children }: { icon: ReactNode; title: string; danger?: boolean; children: ReactNode }) {
  return (
    <li className="rounded-xl bg-paper p-4 shadow-card ring-1 ring-ink/5">
      <span
        className={`grid size-10 place-items-center rounded-full ${danger ? "bg-danger-soft text-danger" : "bg-accent-soft text-accent-text"}`}
      >
        {icon}
      </span>
      <h4 className="mt-3 font-bold">{title}</h4>
      <p className="mt-1 text-card leading-snug text-ink-2">{children}</p>
    </li>
  );
}

/** Empty state: a navy welcome band with the question field, then the profile's suggestions and
 * what the assistant does and refuses (the emergency numbers included). */
function Intro({ profile }: { profile: Profile }) {
  const gp = profile === "gp";
  return (
    <div className="pb-2">
      <section data-on-navy className="bg-navy px-4 pt-7 pb-10 text-white sm:pt-12 sm:pb-14">
        <div className={COLUMN}>
          <p className="inline-flex rounded-full bg-navy-2 px-3 text-note leading-7 font-bold text-on-navy-2">
            {gp ? "Espace professionnels de santé" : "Campagne d’information · règles douloureuses"}
          </p>
          <h2 className="mt-4 text-[1.75rem] leading-tight font-bold text-balance sm:text-[2.5rem]">
            {gp ? "Les recommandations sur l’endométriose, avec leurs pages" : "Règles douloureuses, endométriose\u00a0: posez votre question"}
          </h2>
          <p className="mt-3 text-on-navy-2 sm:text-lg">
            {gp
              ? "Recherche dans les recommandations de bonne pratique (HAS, ESHRE), avec la page citée pour chaque réponse."
              : "Des réponses tirées de sources publiques de santé, toujours citées et datées."}
          </p>
          <div className="mt-6">
            <Composer column="" variant="welcome" />
          </div>
        </div>
      </section>
      <div className={`px-4 ${COLUMN}`}>
        <Suggestions profile={profile} />
        <h3 className="mt-8 mb-2.5 text-sm font-bold text-ink-2">Ce que fait l’assistant</h3>
        <ul className="grid gap-3 sm:grid-cols-3">
          <Feature icon={<BookIcon />} title="Des sources citées">
            Il répond uniquement à partir de sources publiques, avec leur date, et dit quand elles ne couvrent pas la question.
          </Feature>
          <Feature icon={<ShieldIcon />} title={gp ? "Pas de décision individuelle" : "Pas de diagnostic"}>
            {gp
              ? "Il résume les recommandations, sans décision individuelle de diagnostic ou de prescription."
              : "Il ne pose pas de diagnostic et ne prescrit pas de traitement\u00a0: il vous oriente vers un professionnel."}
          </Feature>
          <Feature icon={<AlertIcon />} title="En cas d’urgence" danger>
            Appelez le {tel("15", "SAMU")} ou le {tel("112", "urgences")}, ou envoyez un SMS au{" "}
            <a href="sms:114" aria-label="Envoyer un SMS au 114" className="font-bold text-danger underline underline-offset-2">
              114
            </a>
            . Pensées suicidaires&nbsp;: {tel("3114", "prévention du suicide")}.
          </Feature>
        </ul>
      </div>
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

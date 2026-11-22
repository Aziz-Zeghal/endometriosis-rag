import {
  ActionBarPrimitive,
  AuiIf,
  ComposerPrimitive,
  MessagePrimitive,
  ThreadPrimitive,
  useAuiState,
} from "@assistant-ui/react";
import { MarkdownTextPrimitive } from "@assistant-ui/react-markdown";
import { useEffect, useRef, useState, type AnchorHTMLAttributes, type MouseEvent, type ReactNode } from "react";
import {
  AlertIcon,
  AskIcon,
  BookIcon,
  ChevronIcon,
  ExternalIcon,
  HelpIcon,
  InfoIcon,
  Mark,
  PhoneIcon,
  RetryIcon,
  SendIcon,
  ShieldIcon,
  SmsIcon,
  StopIcon,
} from "./icons";
import {
  FLAG_LABELS,
  ROUTE_LABELS,
  citedSources,
  formatSourceDate,
  frenchSpacing,
  groupSources,
  linkCitations,
  linkHelplines,
  sourceInitials,
  type Profile,
  type Route,
  type RouteData,
  type SourceCard,
} from "./parts";

export const SUGGESTIONS: Record<Profile, { intro: string; prompts: string[] }> = {
  patient: {
    intro:
      "Posez votre question sur les règles douloureuses ou l’endométriose. Chaque réponse cite ses sources, avec leur date.",
    prompts: [
      "J’ai très mal pendant mes règles, au point de rater les cours. C’est normal\u202f?",
      "Qui consulter en premier\u00a0: mon médecin généraliste ou un gynécologue\u202f?",
      "Comment se passe le diagnostic de l’endométriose\u202f?",
    ],
  },
  gp: {
    intro:
      "Recherchez dans les recommandations de bonne pratique (HAS, ESHRE). Chaque réponse cite la page de la recommandation.",
    prompts: [
      "Quels signes d’appel doivent faire évoquer une endométriose\u202f?",
      "Quelle imagerie demander en première intention\u202f?",
      "Quels traitements médicaux sont proposés en première intention\u202f?",
    ],
  },
};

/** When an answer ends with its start above the view (a long answer, or content after it such
 * as the page footer), scrolls back to that start: badge and first lines, the emergency
 * instructions included, instead of the end of the conversation. */
function useShowAnswerStart(running: boolean) {
  const log = useRef<HTMLDivElement>(null);
  const wasRunning = useRef(running);
  useEffect(() => {
    const ended = wasRunning.current && !running;
    wasRunning.current = running;
    const view = log.current;
    const answer = [...(view?.querySelectorAll<HTMLElement>("[data-message]") ?? [])].pop();
    if (!ended || !view || !answer) return;
    const align = () => {
      const above = answer.getBoundingClientRect().top - view.getBoundingClientRect().top - 12;
      if (above < 0) view.scrollTop += above;
    };
    // Next frame, after the viewport's own scroll to the bottom; then again while the text
    // still grows (smooth streaming catches up after the stream ends and the viewport follows
    // the bottom), until the reader scrolls or after 3 s.
    let frame = requestAnimationFrame(align);
    const grows = new ResizeObserver(() => (cancelAnimationFrame(frame), (frame = requestAnimationFrame(align))));
    grows.observe(answer);
    const stop = () => (grows.disconnect(), cancelAnimationFrame(frame));
    const timer = setTimeout(stop, 3000);
    const events = ["wheel", "touchstart", "keydown", "pointerdown"] as const;
    events.forEach((e) => view.addEventListener(e, stop, { once: true }));
    return () => {
      stop();
      clearTimeout(timer);
      events.forEach((e) => view.removeEventListener(e, stop));
    };
  }, [running]);
  return log;
}

type ThreadProps = {
  profile: Profile;
  /** Classes of the reading column (messages and composer); the widget panel uses its width. */
  column?: string;
  /** Replaces the default empty state (intro and suggestions). */
  empty?: ReactNode;
  /** Shown after the messages, inside the scrolling conversation. */
  footer?: ReactNode;
  /** The empty state holds its own question field (`<Composer variant="welcome" />`), so the
   * bottom bar only appears once the conversation has started. */
  welcomeComposer?: boolean;
};

/** The conversation: messages, sources and composer, shared by the page and the widget. */
export function Thread({ profile, column = "", empty, footer, welcomeComposer = false }: ThreadProps) {
  const running = useAuiState((s) => s.thread.isRunning);
  const isEmpty = useAuiState((s) => s.thread.isEmpty);
  const log = useShowAnswerStart(running);
  return (
    <ThreadPrimitive.Root className="flex min-h-0 flex-1 flex-col bg-canvas">
      <ThreadPrimitive.Viewport
        ref={log}
        role="log"
        aria-label="Conversation"
        aria-busy={running}
        autoScroll={!isEmpty} // the empty state is read from its top
        className="min-h-0 flex-1 overflow-y-auto overscroll-contain"
      >
        {/* Full width, so a custom empty state can lay out its own bands. */}
        <AuiIf condition={(s) => s.thread.isEmpty}>{empty ?? <EmptyState profile={profile} />}</AuiIf>
        <div className={`px-4 pt-5 pb-2 empty:hidden ${column}`}>
          <ThreadPrimitive.Messages>
            {({ message }) => (message.role === "user" ? <UserMessage /> : <AssistantMessage />)}
          </ThreadPrimitive.Messages>
        </div>
        {footer && <div className={`px-4 ${column}`}>{footer}</div>}
      </ThreadPrimitive.Viewport>
      {welcomeComposer ? (
        <AuiIf condition={(s) => !s.thread.isEmpty}>
          <Composer column={column} />
        </AuiIf>
      ) : (
        <Composer column={column} />
      )}
    </ThreadPrimitive.Root>
  );
}

function EmptyState({ profile }: { profile: Profile }) {
  return (
    <div className="px-4 pt-4 pb-4">
      <div className="flex gap-3">
        <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-accent-soft text-accent-text">
          <BookIcon />
        </span>
        <p className="text-lead leading-relaxed">{SUGGESTIONS[profile].intro}</p>
      </div>
      <Suggestions profile={profile} />
    </div>
  );
}

/** « Par exemple » and the profile's suggested questions; one tap sends it. */
export function Suggestions({ profile }: { profile: Profile }) {
  const { prompts } = SUGGESTIONS[profile];
  return (
    <>
      <p id="endorag-suggestions" className="mt-6 mb-2 text-sm font-bold text-ink-2">
        Questions fréquentes
      </p>
      <ul aria-labelledby="endorag-suggestions" className="space-y-2">
        {prompts.map((prompt) => (
          <li key={prompt}>
            <ThreadPrimitive.Suggestion
              prompt={prompt}
              send
              className="group flex min-h-14 w-full items-center gap-3 rounded-xl bg-paper py-3 pr-3 pl-4 text-left leading-snug shadow-card ring-1 ring-ink/5 transition-[box-shadow,color] duration-150 hover:text-accent-text hover:shadow-raised active:shadow-card"
            >
              <span className="flex-1">{prompt}</span>
              <span className="grid size-8 shrink-0 place-items-center rounded-full bg-accent-soft text-accent-text transition-colors duration-150 group-hover:bg-accent group-hover:text-accent-ink">
                <ChevronIcon />
              </span>
            </ThreadPrimitive.Suggestion>
          </li>
        ))}
      </ul>
    </>
  );
}

function UserMessage() {
  return (
    <MessagePrimitive.Root className="mb-4 flex animate-message-in justify-end">
      <div className="max-w-[85%] rounded-2xl rounded-br-md bg-accent px-4 py-2.5 break-words whitespace-pre-wrap text-accent-ink shadow-card">
        <span className="sr-only">Vous&nbsp;: </span>
        <MessagePrimitive.Parts />
      </div>
    </MessagePrimitive.Root>
  );
}

type Part = { type: string; name?: string; data?: unknown; text?: string };

/** Badge look per route: red is kept for emergencies, the other routes stay calm. */
const BADGE_STYLES: Partial<Record<Route, { className: string; icon: ReactNode }>> = {
  emergency: { className: "bg-danger text-white", icon: <AlertIcon /> },
  clarify: { className: "bg-accent-soft text-accent-text", icon: <HelpIcon /> },
  refuse: { className: "bg-ink/[0.07] text-ink-2", icon: <InfoIcon /> },
  out_of_scope: { className: "bg-ink/[0.07] text-ink-2", icon: <InfoIcon /> },
};

/** Answer card per route: emergency is unmistakable, clarify and refusals get a side rule. */
function cardClass(route: Route | undefined): string {
  if (route === "emergency") return "rounded-2xl border-2 border-danger bg-danger-soft px-4 py-3.5 sm:px-5";
  const base = "rounded-2xl rounded-tl-md bg-paper px-4 py-3.5 shadow-card ring-1 ring-ink/5 sm:px-5 sm:py-4";
  if (route === "clarify") return `${base} border-l-4 border-l-accent`;
  if (route === "refuse" || route === "out_of_scope") return `${base} border-l-4 border-l-line-strong`;
  return base;
}

const FIXED_ROUTES: Route[] = ["emergency", "refuse", "out_of_scope", "chitchat"];

function AssistantMessage() {
  const parts = useAuiState((s) => s.message.content) as readonly Part[];
  const status = useAuiState((s) => s.message.status);
  const isLast = useAuiState((s) => s.message.isLast);
  const running = useAuiState((s) => s.thread.isRunning);

  const route = parts.find((p) => p.type === "data" && p.name === "route")?.data as RouteData | undefined;
  const sources = parts.find((p) => p.type === "data" && p.name === "sources")?.data as SourceCard[] | undefined;
  const text = parts.map((p) => (p.type === "text" ? (p.text ?? "") : "")).join("");
  const cited = sources ? citedSources(sources, text) : [];
  const emergency = route?.route === "emergency";
  // Fixed templates: retrying gives the same text, so « Réessayer » is not offered.
  const fixed = route && FIXED_ROUTES.includes(route.route);
  const badge = route && ROUTE_LABELS[route.route];
  const badgeStyle = route && BADGE_STYLES[route.route];
  const failed = status?.type === "incomplete" && status.reason === "error";
  const stopped = status?.type === "incomplete" && status.reason === "cancelled";

  return (
    <MessagePrimitive.Root data-message className="mb-5 animate-message-in">
      <div className="mb-2 flex flex-wrap items-center gap-x-2 gap-y-1.5">
        <span className="flex items-center gap-2 text-sm font-bold text-ink-2">
          <Mark className="size-6" />
          Assistant<span className="sr-only">&nbsp;: </span>
        </span>
        {badge && (
          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-2.5 text-xs leading-6 font-bold ${badgeStyle?.className ?? ""}`}
          >
            {badgeStyle?.icon}
            {badge}
          </span>
        )}
        {route?.flags.map((f) => (
          <span
            key={f}
            className="inline-flex items-center gap-1.5 rounded-full bg-paper px-2.5 text-xs leading-6 text-ink-2 ring-1 ring-ink/10"
          >
            <ShieldIcon />
            {FLAG_LABELS[f]}
          </span>
        ))}
      </div>
      <div className={cardClass(route?.route)} role={emergency ? "alert" : undefined}>
        {!text && status?.type === "running" && (
          <Pending label={sources ? "Rédaction de la réponse…" : "Recherche dans les sources…"} />
        )}
        <MessagePrimitive.Parts
          components={{
            Text: emergency ? EmergencyText : AnswerText,
            Source: () => null,
            data: { Fallback: () => null },
          }}
        />
        {emergency && <EmergencyActions />}
        {failed && (
          <p className="mt-1 flex gap-2 rounded-lg bg-notice px-3 py-2 text-notice-ink">
            <span className="mt-1 shrink-0">
              <AlertIcon />
            </span>
            La réponse n’a pas pu être obtenue. Réessayez dans un instant.
          </p>
        )}
        {stopped && (
          <p className="mt-2 flex items-center gap-1.5 text-sm text-muted">
            <StopIcon />
            Réponse interrompue.
          </p>
        )}
        {cited.length > 0 && <Sources cards={cited} />}
      </div>
      {/* No « Réessayer » under the fixed emergency message either: it must not invite dismissal. */}
      {isLast && !running && !fixed && (
        <ActionBarPrimitive.Root className="mt-1 flex">
          <ActionBarPrimitive.Reload className="-ml-1 flex min-h-11 items-center gap-1.5 rounded-full px-3 text-sm font-bold text-muted transition-colors duration-150 hover:bg-ink/5 hover:text-ink active:bg-ink/10">
            <RetryIcon />
            Réessayer
          </ActionBarPrimitive.Reload>
        </ActionBarPrimitive.Root>
      )}
    </MessagePrimitive.Root>
  );
}

/** Waiting state before the first token: three pulsing dots (static with reduced motion). */
function Pending({ label }: { label: string }) {
  return (
    <p className="flex items-center gap-2.5 text-muted">
      <span aria-hidden="true" className="flex gap-1">
        {[0, 150, 300].map((delay) => (
          <span key={delay} className="size-1.5 animate-dot rounded-full bg-accent" style={{ animationDelay: `${delay}ms` }} />
        ))}
      </span>
      {label}
    </p>
  );
}

/** Large tap targets for the main numbers of the fixed emergency message (scope.md). */
const EMERGENCY_ACTIONS = [
  { href: "tel:15", number: "15", label: "SAMU", aria: "Appeler le 15 (SAMU)", sms: false },
  { href: "tel:112", number: "112", label: "Urgences", aria: "Appeler le 112 (urgences)", sms: false },
  { href: "sms:114", number: "114", label: "Par SMS", aria: "Envoyer un SMS au 114", sms: true },
  { href: "tel:3114", number: "3114", label: "Prévention suicide", aria: "Appeler le 3114 (prévention du suicide)", sms: false },
  { href: "tel:119", number: "119", label: "Enfance en danger", aria: "Appeler le 119 (enfance en danger)", sms: false },
  { href: "tel:116117", number: "116 117", label: "Médecin de garde", aria: "Appeler le 116 117 (médecin de garde)", sms: false },
];

function EmergencyActions() {
  return (
    <ul aria-label="Numéros d’urgence" className="mt-3 grid grid-cols-2 gap-2">
      {EMERGENCY_ACTIONS.map((a, i) => (
        <li key={a.href}>
          <a
            href={a.href}
            aria-label={a.aria}
            className={`flex h-full min-h-12 items-center gap-2 rounded-xl px-3 py-2 leading-tight no-underline transition-colors duration-150 ${
              i === 0
                ? "bg-danger text-white hover:bg-danger-strong"
                : "border-2 border-danger bg-paper text-danger hover:bg-danger-soft"
            }`}
          >
            {a.sms ? <SmsIcon /> : <PhoneIcon />}
            <span>
              <span className="block text-lg font-bold whitespace-nowrap">{a.number}</span>
              <span className="block text-sm">{a.label}</span>
            </span>
          </a>
        </li>
      ))}
    </ul>
  );
}

const ALLOWED_URL = /^(https?:|tel:|sms:|#cite-)/;

function Link({ href = "", children, ...rest }: AnchorHTMLAttributes<HTMLAnchorElement>) {
  if (href.startsWith("#cite-")) {
    const n = href.slice(6);
    const jump = (e: MouseEvent<HTMLAnchorElement>) => {
      e.preventDefault();
      const card = e.currentTarget.closest("[data-message]")?.querySelector<HTMLElement>(`[data-cite~="${n}"]`);
      card?.scrollIntoView({ block: "nearest", behavior: "smooth" });
      card?.focus();
    };
    return (
      <a href={href} onClick={jump} className="cite" aria-label={`Source ${n}`}>
        {children}
      </a>
    );
  }
  if (href.startsWith("tel:") || href.startsWith("sms:")) {
    const sms = href.startsWith("sms:");
    return (
      <a href={href} className="helpline" aria-label={`${sms ? "Envoyer un SMS au" : "Appeler le"} ${children}`}>
        {children}
      </a>
    );
  }
  return (
    <a {...rest} href={href} target="_blank" rel="noopener noreferrer">
      {children}
      <span className="sr-only"> (nouvel onglet)</span>
    </a>
  );
}

const markdownProps = {
  className: "answer",
  urlTransform: (url: string) => (ALLOWED_URL.test(url) ? url : ""),
  components: { a: Link },
};

const answerText = (md: string) => linkCitations(frenchSpacing(md));
const emergencyText = (md: string) => linkHelplines(frenchSpacing(md));
const AnswerText = () => <MarkdownTextPrimitive {...markdownProps} preprocess={answerText} />;
const EmergencyText = () => <MarkdownTextPrimitive {...markdownProps} preprocess={emergencyText} smooth={false} />;

/** Source cards in the style of a directory listing: publisher badge, linked title, publisher
 * and date, then the cited pages as chips. */
function Sources({ cards }: { cards: SourceCard[] }) {
  const groups = groupSources(cards);
  return (
    <section aria-label="Sources citées" className="mt-4 border-t border-line pt-3.5">
      <h3 className="mb-2.5 flex items-center gap-1.5 text-sm font-bold text-ink-2">
        <BookIcon />
        Sources citées
      </h3>
      <ol className="grid gap-2">
        {groups.map((g) => (
          <li
            key={g.key}
            tabIndex={-1}
            data-cite={g.refs.map((r) => r.id).join(" ")}
            className="flex gap-3 rounded-xl bg-canvas p-3 text-card transition-shadow duration-200 focus:ring-2 focus:ring-accent focus:outline-none"
          >
            <span
              aria-hidden="true"
              className="grid size-11 shrink-0 place-items-center rounded-full bg-paper text-xs font-bold tracking-tight text-accent-text ring-1 ring-ink/10"
            >
              {sourceInitials(g.source)}
            </span>
            <div className="min-w-0 flex-1">
              <a
                href={g.refs[0].url}
                target="_blank"
                rel="noopener noreferrer"
                className="block leading-snug font-bold break-words text-accent-text underline-offset-2 hover:underline"
              >
                {frenchSpacing(g.title)}
                <span className="sr-only"> (nouvel onglet)</span>
                <span className="ml-1 inline-block align-[-2px] font-normal">
                  <ExternalIcon />
                </span>
              </a>
              <p className="mt-0.5 text-sm text-muted">
                <span className="font-bold text-ink-2">{g.source}</span>
                {" · "}
                {formatSourceDate(g.date)}
                <span className="sr-only">
                  {" "}
                  (source{g.refs.length > 1 ? "s" : ""} {g.refs.map((r) => r.id).join(", ")})
                </span>
              </p>
              <p className="mt-2 flex flex-wrap items-center gap-1.5 text-sm">
                <span
                  aria-hidden="true"
                  className="inline-flex min-h-7 items-center rounded-md bg-ink/[0.07] px-2 font-bold text-ink-2"
                >
                  {g.refs.map((r) => `[${r.id}]`).join(" ")}
                </span>
                {g.pages.map((p) => (
                  <a
                    key={p.page}
                    href={p.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex min-h-7 items-center rounded-md bg-accent-soft px-2.5 font-bold text-accent-text transition-colors duration-150 hover:bg-accent hover:text-accent-ink"
                    aria-label={`Page ${p.page} (nouvel onglet)`}
                  >
                    p. {p.page}
                  </a>
                ))}
              </p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

let handoff = false;

/** The question field: a bottom bar during the conversation, or the large field of the
 * welcome band (`variant="welcome"`, on navy) before the first question. */
export function Composer({ column, variant = "bar" }: { column: string; variant?: "bar" | "welcome" }) {
  const welcome = variant === "welcome";
  // The welcome field leaves with the first question: the bar takes the focus over if it had it.
  const [autoFocus] = useState(() => !welcome && handoff);
  useEffect(() => {
    if (!welcome) handoff = false;
  }, [welcome]);
  return (
    <ComposerPrimitive.Root
      className={
        welcome
          ? ""
          : "bg-paper px-3 pt-3 pb-[max(12px,env(safe-area-inset-bottom))] shadow-bar short:pt-2 short:pb-[max(8px,env(safe-area-inset-bottom))]"
      }
    >
      <div className={column}>
        <div
          className={`flex items-end gap-2 bg-paper transition-[border-color,box-shadow] duration-150 ${
            welcome
              ? "rounded-2xl p-2 pl-4 shadow-raised focus-within:ring-4 focus-within:ring-white/40"
              : "rounded-2xl border border-line-strong py-1 pr-1 pl-3.5 focus-within:border-accent focus-within:ring-2 focus-within:ring-accent/30"
          }`}
        >
          {welcome && (
            <span className="mb-3 shrink-0 text-accent-text">
              <AskIcon />
            </span>
          )}
          <ComposerPrimitive.Input
            id="endorag-question"
            autoFocus={autoFocus}
            onKeyDown={welcome ? (e) => (handoff = e.key === "Enter" && !e.shiftKey) : undefined}
            rows={1}
            maxRows={5}
            aria-label="Votre question"
            placeholder={welcome ? "Posez votre question avec vos mots…" : "Écrivez votre question…"}
            className={`min-h-11 flex-1 resize-none bg-transparent py-2.5 leading-normal text-ink placeholder:text-muted focus-visible:outline-none ${
              welcome ? "text-base sm:text-lg" : "text-base"
            }`}
          />
          <AuiIf condition={(s) => !s.thread.isRunning}>
            <ComposerPrimitive.Send
              aria-label="Envoyer"
              onClick={welcome ? (e) => (handoff = e.detail === 0) : undefined}
              className={`flex shrink-0 items-center justify-center gap-2 rounded-full bg-accent font-bold text-accent-ink transition-[background-color,transform] duration-150 hover:bg-accent-strong active:scale-95 disabled:cursor-not-allowed disabled:bg-ink/15 disabled:text-ink/45 ${
                welcome ? "min-h-12 min-w-12 rounded-xl sm:px-5" : "size-11"
              }`}
            >
              {welcome && <span className="max-sm:hidden">Envoyer</span>}
              <SendIcon />
            </ComposerPrimitive.Send>
          </AuiIf>
          <AuiIf condition={(s) => s.thread.isRunning}>
            <ComposerPrimitive.Cancel
              aria-label="Arrêter la réponse"
              className="grid size-11 shrink-0 place-items-center rounded-full bg-ink text-white transition-[background-color,transform] duration-150 hover:bg-ink-2 active:scale-95"
            >
              <StopIcon />
            </ComposerPrimitive.Cancel>
          </AuiIf>
        </div>
        <p
          className={`mt-2 flex items-center gap-1.5 px-1 text-note leading-snug short:mt-1 ${
            welcome ? "text-on-navy-2" : "text-muted"
          }`}
        >
          <ShieldIcon />
          Ne donnez pas d’informations qui permettent de vous identifier.
        </p>
      </div>
    </ComposerPrimitive.Root>
  );
}

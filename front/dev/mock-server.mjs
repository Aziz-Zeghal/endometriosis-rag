// Mock of POST /api/chat for front-end work without the real backend (no index, no model).
// It replays the exact part sequence of back/src/endorag_back/routes/chat/chat.py:
// start, data-route, source-url… + data-sources, text-start, text-delta…, text-end, finish, [DONE].
// Template answers (emergency, refuse, out_of_scope, chitchat) are read from the backend's
// prompt files, so the wording is the real one; generated answers are marked as simulated.
//
// Usage: node dev/mock-server.mjs [port]   (default 8000; like the real backend, one server
// answers for both profiles, picked by the request body's `profile`)

import { readFileSync } from "node:fs";
import { createServer } from "node:http";
import { randomUUID } from "node:crypto";

const PORT = Number(process.argv[2] ?? 8000);
const PROMPTS = new URL("../../back/src/endorag_back/prompts/", import.meta.url);

const prompt = (profile, node) => readFileSync(new URL(`${profile}/${node}.md`, PROMPTS), "utf8").trim();

const SOURCES = {
  patient: [
    {
      id: 1,
      title: "Endométriose : symptômes, diagnostic et évolution",
      source: "Ameli",
      date: "2026-04-09",
      url: "https://www.ameli.fr/assure/sante/themes/endometriose/symptomes-diagnostic-evolution",
      page: null,
    },
    {
      id: 2,
      title: "Prise en charge de l'endométriose : démarche diagnostique et traitement médical (fiche de synthèse)",
      source: "HAS",
      date: "2017-12-01",
      url: "https://www.has-sante.fr/upload/docs/application/pdf/2018-01/prise_en_charge_de_lendiometriose_-_demarche_diagnostique_et_traitement_medical_-_fiche_de_synthese.pdf#page=2",
      page: 2,
    },
    {
      id: 3,
      title: "Prise en charge de l'endométriose : démarche diagnostique et traitement médical (fiche de synthèse)",
      source: "HAS",
      date: "2017-12-01",
      url: "https://www.has-sante.fr/upload/docs/application/pdf/2018-01/prise_en_charge_de_lendiometriose_-_demarche_diagnostique_et_traitement_medical_-_fiche_de_synthese.pdf#page=4",
      page: 4,
    },
  ],
  gp: [
    {
      id: 1,
      title: "Prise en charge de l'endométriose : recommandations",
      source: "HAS",
      date: "2017-12-01",
      url: "https://www.has-sante.fr/upload/docs/application/pdf/2018-01/prise_en_charge_de_lendometriose_-_recommandations.pdf#page=7",
      page: 7,
    },
    {
      id: 2,
      title: "Prise en charge de l'endométriose : messages clés destinés au médecin généraliste",
      source: "HAS",
      date: "2017-12-01",
      url: "https://www.has-sante.fr/upload/docs/application/pdf/2018-01/prise_en_charge_de_lendiometriose_-_messages_cles_destines_au_medecin_generaliste.pdf#page=1",
      page: 1,
    },
  ],
};

const ANSWER = {
  patient:
    "*(Réponse simulée par le serveur de démonstration.)*\n\n" +
    "Des règles douloureuses au point de **perturber la vie quotidienne** (cours, travail) " +
    "justifient d'en parler à un professionnel de santé [1]. Cela ne veut pas dire " +
    "automatiquement qu'il s'agit d'une endométriose.\n\n" +
    "Pour préparer la consultation, les sources conseillent de noter :\n\n" +
    "- l'intensité et la durée des douleurs ;\n" +
    "- ce qui a été essayé pour les soulager [2] ;\n" +
    "- les autres symptômes éventuels [3].\n\n" +
    "Ces informations sont générales et ne remplacent pas un avis médical.",
  gp:
    "*(Réponse simulée par le serveur de démonstration.)*\n\n" +
    "Les recommandations décrivent les **signes d'appel** à rechercher à l'interrogatoire [1] " +
    "et la place de l'examen clinique et de l'imagerie de première intention [2].\n\n" +
    "Consultez les pages citées pour le libellé exact des recommandations.",
  clarify:
    "*(Réponse simulée.)* Pour vous répondre précisément : votre question porte-t-elle sur " +
    "les symptômes, sur les examens ou sur les traitements ?",
};

/** Pick a scenario from the latest user message, as the graph's routes would. */
function scenario(text, profile) {
  const t = text.toLowerCase();
  const flags = [];
  if (/diagnosti|score|si j'ai une endo|est-ce que j'ai/.test(t)) flags.push("asks_for_diagnosis");
  if (/prescri|dose|posologie/.test(t)) flags.push("asks_for_prescription");
  if (/vomi|tout s'arr|mourir|urgence|évanoui/.test(t)) return { routes: ["emergency"], text: prompt(profile, "emergency") };
  if (/culotte|remboursé/.test(t)) return { routes: ["question", "refuse"], flags, text: prompt(profile, "refuse") };
  if (/recette|crêpe|météo/.test(t)) return { routes: ["out_of_scope"], text: prompt(profile, "out_of_scope") };
  if (/^(bonjour|salut|merci)\W*$/.test(t)) return { routes: ["chitchat"], text: prompt(profile, "chitchat") };
  if (/^(et )?(ça|ca)\s*\??$|^precise|^vague/.test(t)) return { routes: ["question", "clarify"], flags, text: ANSWER.clarify };
  if (/erreur/.test(t)) return { routes: ["question"], flags, sources: SOURCES[profile], text: "Début de réponse", fail: prompt(profile, "error") };
  return { routes: ["question"], flags, sources: SOURCES[profile], text: ANSWER[profile] };
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function lastUserText(body) {
  const user = [...(body.messages ?? [])].reverse().find((m) => m.role === "user");
  return (user?.parts ?? []).filter((p) => p.type === "text").map((p) => p.text).join("").trim();
}

async function stream(res, s) {
  const send = (part) => res.write(`data: ${typeof part === "string" ? part : JSON.stringify(part)}\n\n`);
  const textId = `text-${randomUUID()}`;
  send({ type: "start", messageId: `msg-${randomUUID()}` });
  for (const route of s.routes) {
    await sleep(route === "emergency" ? 5 : 400);
    send({ type: "data-route", id: "route", data: { type: "route", route, flags: s.flags ?? [] } });
  }
  if (s.sources) {
    await sleep(500);
    for (const c of s.sources) send({ type: "source-url", sourceId: String(c.id), url: c.url, title: c.title });
    send({ type: "data-sources", id: "sources", data: s.sources });
  }
  send({ type: "text-start", id: textId });
  // Template answers come as one token in the backend; generated ones word by word.
  const chunks = s.sources || s.routes.includes("clarify") ? s.text.match(/\S+\s*/g) : [s.text];
  for (const delta of chunks) {
    if (res.destroyed) return;
    send({ type: "text-delta", id: textId, delta });
    if (chunks.length > 1) await sleep(35);
  }
  if (s.fail) send({ type: "text-delta", id: textId, delta: `\n\n${s.fail}` });
  send({ type: "text-end", id: textId });
  send({ type: "finish" });
  send("[DONE]");
  res.end();
}

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
  "Access-Control-Allow-Headers": "content-type",
};

function handle(req, res) {
  if (req.method === "OPTIONS") return res.writeHead(204, CORS).end();
  if (req.method === "GET" && req.url === "/api/health") {
    return res.writeHead(200, { ...CORS, "content-type": "application/json" }).end(JSON.stringify({
        status: "ok",
        default_profile: "patient",
        profiles: { patient: { collection: "mock", points: 0 }, gp: { collection: "mock", points: 0 } },
        mock: true,
      }));
  }
  if (req.method !== "POST" || req.url !== "/api/chat") return res.writeHead(404, CORS).end();
  let raw = "";
  req.on("data", (c) => (raw += c));
  req.on("end", () => {
    const body = JSON.parse(raw || "{}");
    const profile = body.profile ?? "patient";
    if (!(profile in SOURCES)) return res.writeHead(422, CORS).end();
    const text = lastUserText(body);
    if (!text) return res.writeHead(422, CORS).end();
    console.log(`[${profile}] ${text}`);
    res.writeHead(200, {
      ...CORS,
      "content-type": "text/event-stream",
      "x-vercel-ai-ui-message-stream": "v1",
      "cache-control": "no-cache",
    });
    stream(res, scenario(text, profile));
  });
}

createServer(handle).listen(PORT, () => console.log(`Mock chat API on http://localhost:${PORT}/api/chat`));

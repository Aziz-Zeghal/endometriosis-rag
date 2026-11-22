// Entry of widget.js: reads the script tag's data-* attributes and mounts the widget into a
// Shadow DOM with its compiled CSS, so host styles and widget styles stay apart.
import { createRoot } from "react-dom/client";
import { readConfig } from "./config";
import compiledCss from "./widget.css?inline";
import { Widget, controller, initUi } from "./Widget";

// `currentScript` is set while a classic script runs; the dev loader imports this module
// instead, so fall back to the tag that loads widget.js.
const script = (document.currentScript ??
  document.querySelector('script[src*="widget.js"]')) as HTMLScriptElement | null;

// A shadow root does not isolate rem units: they follow the host page's root font size
// (html { font-size: 62.5% } would shrink the widget). Tailwind's rem values become px.
const css = compiledCss.replace(/(\d*\.?\d+)rem\b/g, (_, n: string) => `${+(Number(n) * 16).toFixed(3)}px`);

function mount() {
  const config = readConfig(script);
  initUi(config);
  // A custom tag, which the host page's tag rules (div, body > div) do not match, and an
  // inline !important reset, which beats the host page's !important rules.
  const host = document.createElement("endorag-widget");
  host.id = "endorag-widget";
  host.setAttribute("style", "all: initial !important; display: block !important;");
  document.body.appendChild(host);
  const shadow = host.attachShadow({ mode: "open" });

  // @property rules are ignored inside a shadow root, so Tailwind's are registered on the
  // document (they only declare --tw-* custom properties and their initial values).
  const properties = css.match(/@property[^{]+\{[^}]*\}/g);
  if (properties) {
    const global = document.createElement("style");
    global.textContent = properties.join("\n");
    document.head.appendChild(global);
  }
  const style = document.createElement("style");
  style.textContent = css;
  shadow.appendChild(style);

  const container = document.createElement("div");
  shadow.appendChild(container);
  createRoot(container).render(<Widget config={config} />);
  window.dispatchEvent(new Event("endorag:ready"));
}

// Small API for host pages: open the panel (optionally with another profile) or close it.
declare global {
  interface Window {
    EndoRAG?: typeof controller;
  }
}
window.EndoRAG = controller;

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount);
else mount();

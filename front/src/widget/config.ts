import type { Profile } from "./parts";

export type WidgetConfig = {
  api: string; // API base URL for the patient profile
  apiGp: string; // API base URL for the gp profile (one backend serves one profile)
  profile: Profile;
  open: boolean;
  accent: string | null;
};

const DEFAULT_API = "http://localhost:8000";

/** Reads the `data-*` attributes of the widget's script tag. */
export function readConfig(script: HTMLScriptElement | null): WidgetConfig {
  const d = script?.dataset ?? {};
  const api = (d.api || DEFAULT_API).replace(/\/$/, "");
  return {
    api,
    apiGp: (d.apiGp || api).replace(/\/$/, ""),
    profile: d.profile === "gp" ? "gp" : "patient",
    open: d.open === "true",
    accent: d.accent && CSS.supports("color", d.accent) ? d.accent : null,
  };
}

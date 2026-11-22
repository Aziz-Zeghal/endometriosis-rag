import { parseProfile, type Profile } from "../chat/parts";

export type WidgetConfig = {
  api: string; // API base URL (one backend serves both profiles)
  profile: Profile;
  open: boolean;
  accent: string | null;
};

const DEFAULT_API = "http://localhost:8000";

/** Reads the `data-*` attributes of the widget's script tag. */
export function readConfig(script: HTMLScriptElement | null): WidgetConfig {
  const d = script?.dataset ?? {};
  return {
    api: (d.api || DEFAULT_API).replace(/\/$/, ""),
    profile: parseProfile(d.profile),
    open: d.open === "true",
    accent: d.accent && CSS.supports("color", d.accent) ? d.accent : null,
  };
}

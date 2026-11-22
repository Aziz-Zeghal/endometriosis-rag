import { AssistantRuntimeProvider } from "@assistant-ui/react";
import { AssistantChatTransport, useChatRuntime } from "@assistant-ui/react-ai-sdk";
import { useMemo, type ReactNode } from "react";
import type { Profile } from "./parts";

/** One conversation against `POST {api}/api/chat`; the body names the profile, so one backend
 * serves both. Remount it (React `key`) to start a new conversation. */
export function ChatRuntime({ api, profile, children }: { api: string; profile: Profile; children: ReactNode }) {
  const transport = useMemo(
    () => new AssistantChatTransport({ api: `${api}/api/chat`, body: { profile } }),
    [api, profile],
  );
  const runtime = useChatRuntime({ transport });
  return <AssistantRuntimeProvider runtime={runtime}>{children}</AssistantRuntimeProvider>;
}

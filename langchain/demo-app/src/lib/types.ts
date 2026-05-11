export type MessageRole =
  | "user"
  | "assistant"
  | "tool_call"
  | "tool_result"
  | "search_call"
  | "search_result";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content?: string;
  toolName?: string;
  url?: string;
  goal?: string;
  searchQuery?: string;
}

export type BackendEvent =
  | { type: "thinking" }
  | { type: "tool_call"; name: string; args: Record<string, unknown> }
  | { type: "tool_result"; name: string; content: unknown }
  | { type: "streaming_url"; url: string }
  | { type: "progress"; message: string }
  | { type: "token"; content: string }
  | { type: "done"; content: string }
  | { type: "error"; message: string };

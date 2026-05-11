import { useState, useRef } from "react";
import { Send, Globe, Search, Loader2, CheckCircle2, ChevronRight, Link2, Eye, ArrowRight } from "lucide-react";
import Markdown from "react-markdown";
import { Button } from "@/components/ui/button";
import {
  ChatContainerRoot,
  ChatContainerContent,
  ChatContainerScrollAnchor,
} from "@/components/ui/chat-container";
import { streamChat } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";
import tfIcon from "@/assets/logo/TF_ICON.svg";

let idCounter = 0;
const uid = () => `msg-${++idCounter}`;

function LangChainBadge() {
  return (
    <span className="inline-flex items-center gap-1 rounded-md bg-[#1C3C3C] px-1.5 py-0.5 text-[10px] font-semibold tracking-wide text-[#65D9A5] uppercase">
      <Link2 className="h-2.5 w-2.5" />
      LangChain
    </span>
  );
}

function FadeIn({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`animate-[fadeSlideIn_0.35s_ease-out_both] ${className}`}>
      {children}
    </div>
  );
}

/* ── App ─────────────────────────────────────────────────────────────────── */

export default function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [activeToolName, setActiveToolName] = useState("");
  const [streamingUrl, setStreamingUrl] = useState("");
  const [progressSteps, setProgressSteps] = useState<string[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMsg = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { id: uid(), role: "user", content: userMsg }]);
    setLoading(true);
    setStreamingContent("");
    setActiveToolName("");
    setStreamingUrl("");
    setProgressSteps([]);

    try {
      let assistantContent = "";

      for await (const event of streamChat(userMsg)) {
        switch (event.type) {
          case "thinking":
            break;

          case "tool_call":
            if (event.name === "tinyfish_web_automation") {
              setActiveToolName("tinyfish");
              const tfUrl = typeof event.args.url === "string" ? event.args.url : "";
              const tfGoal = typeof event.args.goal === "string" ? event.args.goal : "";
              setMessages((prev) => [
                ...prev,
                {
                  id: uid(),
                  role: "tool_call",
                  toolName: event.name,
                  url: tfUrl,
                  goal: tfGoal,
                },
              ]);
            } else if (event.name === "duckduckgo_search") {
              setActiveToolName("search");
              const query = typeof event.args.query === "string" ? event.args.query : "";
              setMessages((prev) => [
                ...prev,
                {
                  id: uid(),
                  role: "search_call",
                  toolName: event.name,
                  searchQuery: query,
                },
              ]);
            }
            break;

          case "streaming_url":
            setStreamingUrl(event.url);
            break;

          case "progress":
            if (event.message) {
              setProgressSteps((prev) => [...prev, event.message]);
            }
            break;

          case "tool_result":
            setActiveToolName("");
            setStreamingUrl("");
            setProgressSteps([]);
            if (event.name === "tinyfish_web_automation") {
              setMessages((prev) => [
                ...prev,
                {
                  id: uid(),
                  role: "tool_result",
                  toolName: event.name,
                  content:
                    typeof event.content === "string"
                      ? event.content
                      : JSON.stringify(event.content),
                },
              ]);
            } else if (event.name === "duckduckgo_search") {
              setMessages((prev) => [
                ...prev,
                {
                  id: uid(),
                  role: "search_result",
                  toolName: event.name,
                  content:
                    typeof event.content === "string"
                      ? event.content
                      : JSON.stringify(event.content),
                },
              ]);
            }
            break;

          case "token":
            assistantContent += event.content;
            setStreamingContent(assistantContent);
            break;

          case "done":
            setStreamingContent("");
            setMessages((prev) => [
              ...prev,
              { id: uid(), role: "assistant", content: event.content || assistantContent },
            ]);
            break;

          case "error":
            setMessages((prev) => [
              ...prev,
              { id: uid(), role: "assistant", content: `Error: ${event.message}` },
            ]);
            break;
        }
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: uid(),
          role: "assistant",
          content: `Error: ${err instanceof Error ? err.message : String(err)}`,
        },
      ]);
    } finally {
      setLoading(false);
      setStreamingContent("");
      setActiveToolName("");
      setStreamingUrl("");
      setProgressSteps([]);
      inputRef.current?.focus();
    }
  };

  return (
    <div className="flex h-screen flex-col bg-background text-foreground font-sans">
      {/* Header */}
      <header className="border-b border-border/50 px-6 py-3">
        <div className="mx-auto flex max-w-2xl items-center justify-between">
          <div className="flex items-center gap-2.5">
            <img src={tfIcon} alt="TinyFish" className="h-7 w-7 fish-idle" />
            <h1 className="text-[15px] font-bold tracking-tight">
              <span className="text-tf-orange">Tiny</span><span>Fish</span>
            </h1>
            <span className="text-xs text-muted-foreground/50 font-medium">Web Agent</span>
          </div>
          <LangChainBadge />
        </div>
      </header>

      {/* Messages */}
      <ChatContainerRoot className="flex-1">
        <ChatContainerContent className="mx-auto max-w-2xl px-6 py-8">
          {messages.length === 0 && !loading && (
            <div className="flex flex-col items-center justify-center py-20 text-center animate-[fadeSlideIn_0.5s_ease-out_both]">
              <img src={tfIcon} alt="TinyFish" className="h-14 w-14 mb-6 fish-hero" />
              <h2 className="text-xl font-bold mb-1.5 tracking-tight">
                What would you like to automate?
              </h2>
              <p className="text-sm text-muted-foreground mb-6 max-w-sm">
                Browse websites, extract data, search the web — powered by a multi-tool LangChain agent.
              </p>
              <div className="flex flex-wrap gap-2 justify-center">
                {[
                  "Search for the top AI startups in 2025 and extract details from the first result",
                  "Extract the first 5 products from scrapeme.live/shop",
                  "What's trending on Hacker News right now?",
                ].map((q) => (
                  <button
                    key={q}
                    onClick={() => setInput(q)}
                    className="rounded-full border border-border px-3.5 py-1.5 text-[13px] text-muted-foreground hover:border-tf-orange/40 hover:text-foreground transition-all duration-200"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <MessageBlock key={msg.id} message={msg} />
          ))}

          {/* Active tool indicator with streaming progress */}
          {activeToolName && (
            <FadeIn className="ml-9 pl-4 py-2 space-y-1.5">
              <div className="flex items-center gap-2.5 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin text-tf-orange" />
                <span>
                  {activeToolName === "tinyfish"
                    ? "Browsing website..."
                    : "Searching the web..."}
                </span>
              </div>
              {streamingUrl && (
                <FadeIn className="flex items-center gap-2 text-xs">
                  <Eye className="h-3 w-3 text-tf-orange/70" />
                  <a
                    href={streamingUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-tf-orange/70 hover:text-tf-orange underline underline-offset-2 transition-colors duration-200"
                  >
                    Watch browser live
                  </a>
                </FadeIn>
              )}
              {progressSteps.map((step, i) => (
                <FadeIn key={i} className="flex items-center gap-2 text-xs text-muted-foreground/70">
                  <ArrowRight className="h-3 w-3 text-tf-orange/40" />
                  <span>{step}</span>
                </FadeIn>
              ))}
            </FadeIn>
          )}

          {/* Streaming response */}
          {streamingContent && (
            <FadeIn className="mt-4">
              <div className="text-[14px] text-foreground/75 leading-[1.7] prose prose-sm prose-neutral max-w-none prose-p:my-1.5 prose-ol:my-2 prose-ul:my-2 prose-li:my-0.5 prose-strong:text-foreground/90 prose-strong:font-semibold prose-headings:text-foreground prose-code:text-tf-orange prose-code:bg-tf-orange/5 prose-code:rounded prose-code:px-1 prose-code:py-0.5 prose-code:text-xs prose-code:font-normal prose-code:before:content-none prose-code:after:content-none">
                <Markdown>{streamingContent}</Markdown>
                <span className="inline-block w-1.5 h-4 bg-tf-orange/60 animate-pulse ml-0.5 align-text-bottom" />
              </div>
            </FadeIn>
          )}

          {/* Thinking indicator */}
          {loading && !activeToolName && !streamingContent && (
            <FadeIn className="flex items-center gap-2.5 text-sm text-muted-foreground py-4">
              <img src={tfIcon} alt="" className="h-6 w-6 fish-active" />
              <span>Agent is thinking...</span>
            </FadeIn>
          )}

          <ChatContainerScrollAnchor />
        </ChatContainerContent>
      </ChatContainerRoot>

      {/* Input */}
      <div className="border-t border-border/50 px-6 py-3.5">
        <form onSubmit={handleSubmit} className="mx-auto flex max-w-2xl gap-2.5">
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask me to browse any website or search the web..."
            disabled={loading}
            className="flex-1 rounded-lg border border-border bg-transparent px-3.5 py-2 text-sm font-sans placeholder:text-muted-foreground/50 focus:outline-none focus:border-tf-orange/50 disabled:opacity-50 transition-colors duration-200"
          />
          <Button
            type="submit"
            disabled={loading || !input.trim()}
            size="icon"
            className="h-9 w-9 rounded-lg bg-tf-orange hover:bg-tf-orange/90 text-white shrink-0 transition-colors duration-200"
          >
            <Send className="h-3.5 w-3.5" />
          </Button>
        </form>
      </div>
    </div>
  );
}

/* ── Message Block ───────────────────────────────────────────────────────── */

function MessageBlock({ message }: { message: ChatMessage }) {
  if (message.role === "user") {
    return (
      <FadeIn className="pt-8 first:pt-0 flex justify-end">
        <div className="max-w-[80%] rounded-2xl rounded-br-md bg-tf-orange px-4 py-2.5 text-[14px] text-white font-medium shadow-sm shadow-tf-orange/15">
          {message.content}
        </div>
      </FadeIn>
    );
  }

  if (message.role === "assistant") {
    return (
      <FadeIn className="mt-4">
        <div className="text-[14px] text-foreground/75 leading-[1.7] prose prose-sm prose-neutral max-w-none prose-p:my-1.5 prose-ol:my-2 prose-ul:my-2 prose-li:my-0.5 prose-strong:text-foreground/90 prose-strong:font-semibold prose-headings:text-foreground prose-code:text-tf-orange prose-code:bg-tf-orange/5 prose-code:rounded prose-code:px-1 prose-code:py-0.5 prose-code:text-xs prose-code:font-normal prose-code:before:content-none prose-code:after:content-none">
          <Markdown>{message.content ?? ""}</Markdown>
        </div>
      </FadeIn>
    );
  }

  if (message.role === "tool_call") {
    return (
      <FadeIn className="mt-3 ml-9 pl-4 border-l-2 border-tf-orange/20">
        <ToolCallBlock url={message.url!} goal={message.goal!} />
      </FadeIn>
    );
  }

  if (message.role === "tool_result") {
    return (
      <FadeIn className="mt-2 ml-9 pl-4">
        <ResultBlock content={message.content!} />
      </FadeIn>
    );
  }

  if (message.role === "search_call") {
    return (
      <FadeIn className="mt-3 ml-9 pl-4 border-l-2 border-blue-500/20">
        <SearchCallBlock query={message.searchQuery!} />
      </FadeIn>
    );
  }

  if (message.role === "search_result") {
    return (
      <FadeIn className="mt-2 ml-9 pl-4">
        <SearchResultBlock content={message.content!} />
      </FadeIn>
    );
  }

  return null;
}

/* ── Tool Call Block ─────────────────────────────────────────────────────── */

function ToolCallBlock({ url, goal }: { url: string; goal: string }) {
  return (
    <div className="space-y-1">
      <div className="flex items-center gap-2">
        <Globe className="h-3.5 w-3.5 text-tf-orange" />
        <span className="text-[11px] font-bold uppercase tracking-widest text-tf-orange">
          Browsing
        </span>
        <LangChainBadge />
      </div>
      <p className="text-[13px] font-medium text-foreground/90 break-all">{url}</p>
      <p className="text-xs text-muted-foreground/70 italic">{goal}</p>
    </div>
  );
}

/* ── Search Call Block ───────────────────────────────────────────────────── */

function SearchCallBlock({ query }: { query: string }) {
  return (
    <div className="space-y-1">
      <div className="flex items-center gap-2">
        <Search className="h-3.5 w-3.5 text-blue-500" />
        <span className="text-[11px] font-bold uppercase tracking-widest text-blue-500">
          Searching
        </span>
        <LangChainBadge />
      </div>
      <p className="text-xs text-muted-foreground/70 italic">{query}</p>
    </div>
  );
}

/* ── Search Result Block ─────────────────────────────────────────────────── */

function SearchResultBlock({ content }: { content: string }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div>
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors duration-200"
      >
        <CheckCircle2 className="h-3 w-3 text-emerald-500" />
        <span className="font-medium">Search results</span>
        <ChevronRight
          className={`h-3 w-3 transition-transform duration-200 ${expanded ? "rotate-90" : ""}`}
        />
      </button>
      <div
        className="grid transition-[grid-template-rows] duration-300 ease-out"
        style={{ gridTemplateRows: expanded ? "1fr" : "0fr" }}
      >
        <div className="overflow-hidden">
          <pre className="mt-2 max-h-72 overflow-auto rounded-md bg-muted/30 p-3 text-xs text-muted-foreground/70 font-mono leading-relaxed whitespace-pre-wrap">
            {content}
          </pre>
        </div>
      </div>
    </div>
  );
}

/* ── Result Block ────────────────────────────────────────────────────────── */

function ResultBlock({ content }: { content: string }) {
  const [expanded, setExpanded] = useState(false);

  let parsed: unknown;
  try {
    parsed = JSON.parse(content);
  } catch {
    parsed = content;
  }

  return (
    <div>
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 text-xs text-muted-foreground/60 hover:text-muted-foreground transition-colors duration-200"
      >
        <CheckCircle2 className="h-3 w-3 text-emerald-500" />
        <span className="font-mono text-[10px] text-tf-orange/70 bg-tf-orange/5 rounded px-1 py-px">
          JSON
        </span>
        <span>Tool result</span>
        <ChevronRight
          className={`h-3 w-3 transition-transform duration-200 ${expanded ? "rotate-90" : ""}`}
        />
      </button>
      <div
        className="grid transition-[grid-template-rows] duration-300 ease-out"
        style={{ gridTemplateRows: expanded ? "1fr" : "0fr" }}
      >
        <div className="overflow-hidden">
          <pre className="mt-2 max-h-72 overflow-auto rounded-md bg-muted/30 p-3 text-xs text-muted-foreground/70 font-mono leading-relaxed">
            {typeof parsed === "string" ? parsed : JSON.stringify(parsed, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  );
}

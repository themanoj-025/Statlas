"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Bot, ChevronDown, ChevronUp, Send, ThumbsDown, ThumbsUp } from "lucide-react";
import { useAuth } from "./AuthProvider";
import { api, ApiError } from "@/lib/api";
import type { AssistantQuota, ChatMessage, ToolCall } from "@/lib/types";

type Feedback = "up" | "down" | null;

/**
 * Grounded AI assistant (Phase 4 — Part B). Embedded contextually (any page
 * can render it), function-calling only — the API never lets the model
 * free-generate a number. Every reply ships `tool_calls` which this widget
 * renders as an expandable "Data used" section (the show-your-work claim).
 * Quota state is shown with the reset date; hitting the cap states exactly
 * what Pro gives you.
 */
export function Assistant() {
  const { status } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [quota, setQuota] = useState<AssistantQuota | null>(null);
  const [expanded, setExpanded] = useState<Record<number, boolean>>({});
  const [feedback, setFeedback] = useState<Record<number, Feedback>>({});
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (status !== "signed-in") return;
    api
      .assistantQuota()
      .then(setQuota)
      .catch(() => setQuota(null));
  }, [status]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, busy]);

  const send = async () => {
    const text = input.trim();
    if (!text || busy) return;
    const history = [...messages, { role: "user" as const, content: text }];
    setMessages(history);
    setInput("");
    setBusy(true);
    setError(null);
    try {
      const res = await api.assistantChat(history.map((m) => ({ role: m.role, content: m.content })));
      setMessages([
        ...history,
        { role: "assistant", content: res.reply, tool_calls: res.tool_calls },
      ]);
      setQuota(res.quota);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The assistant could not answer — try again.");
    } finally {
      setBusy(false);
    }
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void send();
    }
  };

  const toggleTools = (index: number) =>
    setExpanded((cur) => ({ ...cur, [index]: !cur[index] }));

  const setThumb = (index: number, value: "up" | "down") =>
    setFeedback((cur) => ({ ...cur, [index]: cur[index] === value ? null : value }));

  if (status === "signed-out") {
    return (
      <section className="card" aria-label="Statlas assistant">
        <div className="state-block state-block--sunken" role="status">
          <p className="state-block__title">Statlas assistant</p>
          <p className="state-block__body">
            <Link href="/login">Sign in</Link> (or{" "}
            <Link href="/register">create a free account</Link>) to ask grounded questions about
            player stats, comparisons, leaderboards and trends. Every answer is traced to the data
            it used.
          </p>
        </div>
      </section>
    );
  }

  const nearLimit = quota && quota.remaining <= Math.max(2, Math.round(quota.limit * 0.2));

  return (
    <section className="card" aria-label="Statlas assistant" style={{ display: "grid", gap: "var(--space-3)" }}>
      <div className="section-head" style={{ marginTop: 0 }}>
        <h2 className="card__title" style={{ margin: 0 }}>
          <Bot size={16} aria-hidden="true" style={{ verticalAlign: "middle", marginRight: 6 }} />
          Statlas assistant
        </h2>
        {quota && (
          <span className="chip">
            {quota.remaining}/{quota.limit} queries this month · resets {quota.reset}
          </span>
        )}
      </div>

      {quota && quota.remaining <= 0 && (
        <div className="state-block state-block--sunken" role="status">
          <p className="state-block__title">Monthly query quota reached</p>
          <p className="state-block__body">
            Your quota resets on <strong>{quota.reset}</strong>. Pro raises the monthly quota to 200
            queries and includes unlimited comparisons, leaderboards and trend history.
          </p>
        </div>
      )}

      <div
        ref={scrollRef}
        className="assistant-thread"
        role="log"
        aria-live="polite"
        aria-label="Assistant conversation"
        style={{ maxHeight: 420, overflowY: "auto", display: "grid", gap: "var(--space-3)" }}
      >
        {messages.length === 0 && (
          <p className="field__hint" style={{ margin: 0 }}>
            Ask things like: “Compare Erling Haaland and Mohamed Salah”, “Who leads the Premier
            League in progressive passes?”, or “Find players similar to Jude Bellingham”. The
            assistant only answers from Statlas data — never from memory.
          </p>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`assistant-msg assistant-msg--${msg.role}`}>
            <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>{msg.content}</p>

            {msg.role === "assistant" && msg.tool_calls && msg.tool_calls.length > 0 && (
              <div style={{ marginTop: "var(--space-2)" }}>
                <button
                  type="button"
                  className="button button--sm button--ghost"
                  aria-expanded={expanded[i] ?? false}
                  onClick={() => toggleTools(i)}
                >
                  {expanded[i] ? <ChevronUp size={13} aria-hidden="true" /> : <ChevronDown size={13} aria-hidden="true" />}
                  Data used ({msg.tool_calls.length})
                </button>
                {expanded[i] && (
                  <div className="state-block state-block--sunken" style={{ marginTop: "var(--space-2)" }}>
                    <p className="field__hint" style={{ margin: "0 0 var(--space-2)" }}>
                      Every number above comes from these queries against Statlas data:
                    </p>
                    {msg.tool_calls.map((tool: ToolCall, ti) => (
                      <details key={ti} className="assistant-tool">
                        <summary className="field__hint" style={{ fontWeight: 600 }}>
                          {tool.name}({JSON.stringify(tool.input)})
                        </summary>
                        <pre
                          className="assistant-tool-result"
                          style={{ fontSize: "var(--text-xs)", whiteSpace: "pre-wrap", overflowX: "auto", margin: "var(--space-1) 0 0" }}
                        >
                          {typeof tool.result === "string" ? tool.result : JSON.stringify(tool.result, null, 2)}
                        </pre>
                      </details>
                    ))}
                  </div>
                )}
              </div>
            )}

            {msg.role === "assistant" && (
              <div className="assistant-feedback" role="group" aria-label="Rate this answer" style={{ marginTop: "var(--space-2)", display: "flex", gap: "var(--space-1)" }}>
                <button
                  type="button"
                  className="icon-button"
                  aria-label="This answer was accurate"
                  aria-pressed={feedback[i] === "up"}
                  onClick={() => setThumb(i, "up")}
                >
                  <ThumbsUp size={14} aria-hidden="true" />
                </button>
                <button
                  type="button"
                  className="icon-button"
                  aria-label="This answer was inaccurate"
                  aria-pressed={feedback[i] === "down"}
                  onClick={() => setThumb(i, "down")}
                >
                  <ThumbsDown size={14} aria-hidden="true" />
                </button>
              </div>
            )}
          </div>
        ))}

        {busy && (
          <p className="field__hint" role="status" style={{ margin: 0 }}>
            Querying Statlas data…
          </p>
        )}
      </div>

      {error && (
        <div className="state-block state-block--error" role="alert">
          <p className="state-block__body">{error}</p>
        </div>
      )}

      {quota && quota.remaining > 0 && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void send();
          }}
          style={{ display: "flex", gap: "var(--space-2)" }}
        >
          <label htmlFor="assistant-input" className="visually-hidden">
            Ask the assistant
          </label>
          <textarea
            id="assistant-input"
            className="input"
            rows={2}
            placeholder="Ask about a player, comparison, leaderboard or trend…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            disabled={busy}
            style={{ flex: 1, resize: "vertical" }}
          />
          <button type="submit" className="button" disabled={busy || !input.trim()} aria-label="Send question">
            <Send size={15} aria-hidden="true" />
          </button>
        </form>
      )}

      {nearLimit && quota && quota.remaining > 0 && (
        <p className="field__hint" style={{ margin: 0 }} role="status">
          You have {quota.remaining} queries left this month (resets {quota.reset}).{" "}
          <Link href="/pricing">Pro includes 200/month</Link>.
        </p>
      )}
    </section>
  );
}

/** Learn page — AI chat interface with quick actions. */
import { useState, useRef, useEffect, type FormEvent } from "react";
import { assistantApi, type ChatResponse } from "../services/api";
import { STRINGS } from "../constants/strings";
import { Send, Sparkles, HelpCircle, BookOpen, FileText, Loader2, GraduationCap } from "lucide-react";
import "./LearnPage.css";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  xpEarned?: number;
}

export function LearnPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [topic, setTopic] = useState("");
  const [difficulty, setDifficulty] = useState(1);
  const [loading, setLoading] = useState(false);
  const [started, setStarted] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function sendMessage(text: string) {
    if (!text.trim() || loading) return;
    const userMsg: Message = { id: Date.now().toString(), role: "user", content: text };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setLoading(true);
    setStarted(true);

    try {
      const res: ChatResponse = await assistantApi.chat(text, sessionId, topic || undefined);
      setSessionId(res.session_id);
      setDifficulty(res.difficulty_level);
      const aiMsg: Message = {
        id: (Date.now() + 1).toString(), role: "assistant",
        content: res.message, xpEarned: res.xp_earned,
      };
      setMessages(prev => [...prev, aiMsg]);
    } catch (err) {
      const errorMsg: Message = {
        id: (Date.now() + 1).toString(), role: "assistant",
        content: "Sorry, I encountered an error. Please try again.",
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    sendMessage(input);
  }

  function handleQuickAction(action: string) {
    sendMessage(action);
  }

  return (
    <div className="learn-page">
      <div className="animated-bg" aria-hidden="true" />

      {!started ? (
        <section className="learn-hero" aria-label="Start learning">
          <div className="learn-hero-icon" aria-hidden="true"><Sparkles size={48} /></div>
          <h1>{STRINGS.START_LEARNING}</h1>
          <p className="learn-hero-sub">Enter a topic or ask any question to begin your learning session</p>
          <div className="form-group" style={{ maxWidth: 500, margin: "1.5rem auto 0" }}>
            <label htmlFor="topic-input" className="form-label">What would you like to learn?</label>
            <input id="topic-input" type="text" className="form-input" value={topic}
              onChange={e => setTopic(e.target.value)} placeholder="e.g., Python programming, Quantum physics..."
              onKeyDown={e => { if (e.key === "Enter" && topic) sendMessage(`I want to learn about ${topic}`); }} />
          </div>
          <button className="btn btn-primary btn-lg" style={{ marginTop: "1rem" }}
            onClick={() => { if (topic) sendMessage(`I want to learn about ${topic}`); }}
            disabled={!topic}>
            <GraduationCap size={20} aria-hidden="true" /> Start Learning
          </button>
        </section>
      ) : (
        <>
          <header className="learn-header clay-card">
            <div className="learn-topic-info">
              <BookOpen size={20} aria-hidden="true" />
              <span className="learn-topic-name">{topic || "General Learning"}</span>
              <span className="badge badge-primary">Level {difficulty}</span>
            </div>
          </header>

          <div className="learn-chat" role="log" aria-live="polite" aria-label="Conversation history">
            {messages.map(msg => (
              <div key={msg.id} className={`chat-message chat-message-${msg.role}`}
                aria-label={`${msg.role}: ${msg.content.substring(0, 100)}`}>
                <div className="chat-content">{msg.content}</div>
                {msg.xpEarned && msg.xpEarned > 0 && (
                  <div className="xp-popup" aria-label={`${msg.xpEarned} XP earned`}>+{msg.xpEarned} XP</div>
                )}
              </div>
            ))}
            {loading && (
              <div className="chat-message chat-message-assistant" aria-label="Assistant is thinking">
                <Loader2 size={20} style={{ animation: "spin 1s linear infinite" }} aria-hidden="true" />
                <span style={{ marginLeft: "0.5rem" }}>{STRINGS.SENDING}</span>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          <div className="learn-quick-actions" role="toolbar" aria-label="Quick actions">
            <button className="btn btn-ghost btn-sm" onClick={() => handleQuickAction("Quiz me on this topic")}
              disabled={loading}><HelpCircle size={16} aria-hidden="true" /> {STRINGS.QUIZ_ME}</button>
            <button className="btn btn-ghost btn-sm" onClick={() => handleQuickAction("Explain that in simpler terms")}
              disabled={loading}><Sparkles size={16} aria-hidden="true" /> {STRINGS.EXPLAIN_SIMPLER}</button>
            <button className="btn btn-ghost btn-sm" onClick={() => handleQuickAction("Give me a practical example")}
              disabled={loading}><BookOpen size={16} aria-hidden="true" /> {STRINGS.GIVE_EXAMPLE}</button>
            <button className="btn btn-ghost btn-sm" onClick={() => handleQuickAction("Summarize what we've covered")}
              disabled={loading}><FileText size={16} aria-hidden="true" /> {STRINGS.SUMMARIZE}</button>
          </div>

          <form className="learn-input-bar clay-card" onSubmit={handleSubmit}>
            <label htmlFor="chat-input" className="sr-only">Type your message</label>
            <input ref={inputRef} id="chat-input" type="text" className="form-input learn-input"
              value={input} onChange={e => setInput(e.target.value)}
              placeholder={STRINGS.CHAT_PLACEHOLDER} disabled={loading} autoComplete="off" />
            <button type="submit" className="btn btn-indigo" disabled={loading || !input.trim()}
              aria-label="Send message" aria-busy={loading}>
              <Send size={20} aria-hidden="true" />
            </button>
          </form>
        </>
      )}
    </div>
  );
}

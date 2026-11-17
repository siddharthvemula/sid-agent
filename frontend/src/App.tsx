import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { api, Application, Profile, Task } from "./api";

interface Message {
  role: "user" | "agent";
  text: string;
}

const QUICK_ACTIONS = [
  "What courses am I taking?",
  "List tasks",
  "List applications",
  "Look up prereqs for CMSC351",
];

export default function App() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "agent",
      text: "I'm SidAgent. I do things: try \"remind me to submit the form by 2026-11-20\" or \"log application to Acme for SWE Intern\".",
    },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [provider, setProvider] = useState<string>("?");
  const [profile, setProfile] = useState<Profile | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [apps, setApps] = useState<Application[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  const refreshSidebar = useCallback(async () => {
    try {
      const [t, a] = await Promise.all([api.tasks(), api.applications()]);
      setTasks(t.open);
      setApps(a.applications);
    } catch {
      /* backend offline - sidebar just stays as-is */
    }
  }, []);

  useEffect(() => {
    api.health().then((h) => setProvider(h.provider)).catch(() => setProvider("offline"));
    api.profile().then(setProfile).catch(() => undefined);
    refreshSidebar();
  }, [refreshSidebar]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send(text: string) {
    const trimmed = text.trim();
    if (!trimmed || busy) return;
    setMessages((m) => [...m, { role: "user", text: trimmed }]);
    setInput("");
    setBusy(true);
    try {
      const reply = await api.chat(trimmed);
      setMessages((m) => [...m, { role: "agent", text: reply }]);
    } catch {
      setMessages((m) => [
        ...m,
        { role: "agent", text: "Backend unreachable - is the API running on port 8000?" },
      ]);
    } finally {
      setBusy(false);
      refreshSidebar();
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    send(input);
  }

  return (
    <div className="layout">
      <aside className="sidebar">
        <h1>SidAgent</h1>
        <p className="provider">provider: {provider}</p>
        {profile && (
          <section>
            <h2>{profile.name}</h2>
            <p>{profile.degree}</p>
            <p>
              {profile.school} - graduating {profile.graduation}
            </p>
          </section>
        )}
        <section>
          <h2>Open tasks ({tasks.length})</h2>
          {tasks.length === 0 ? (
            <p className="muted">None</p>
          ) : (
            <ul>
              {tasks.map((t) => (
                <li key={t.id}>
                  {t.title}
                  {t.due ? <span className="due"> - {t.due}</span> : null}
                </li>
              ))}
            </ul>
          )}
        </section>
        <section>
          <h2>Applications ({apps.length})</h2>
          {apps.length === 0 ? (
            <p className="muted">None logged yet</p>
          ) : (
            <ul>
              {apps.map((a) => (
                <li key={a.id}>
                  {a.company} - {a.role} <span className="due">[{a.status}]</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </aside>

      <main className="chat">
        <div className="messages">
          {messages.map((m, i) => (
            <div key={i} className={`msg ${m.role}`}>
              <span className="who">{m.role === "user" ? "You" : "SidAgent"}</span>
              <pre>{m.text}</pre>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
        <div className="quick">
          {QUICK_ACTIONS.map((q) => (
            <button key={q} onClick={() => send(q)} disabled={busy}>
              {q}
            </button>
          ))}
        </div>
        <form onSubmit={onSubmit} className="composer">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Tell SidAgent to do something..."
            disabled={busy}
          />
          <button type="submit" disabled={busy}>
            Send
          </button>
        </form>
      </main>
    </div>
  );
}

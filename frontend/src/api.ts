const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface Task {
  id: number;
  title: string;
  due: string | null;
  status: string;
}

export interface Application {
  id: number;
  company: string;
  role: string;
  status: string;
}

export interface Profile {
  name: string;
  school: string;
  degree: string;
  graduation: string;
  fall_2026_courses: string[];
  goals: string[];
  [key: string]: unknown;
}

async function getJson<T>(path: string): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`);
  if (!resp.ok) throw new Error(`GET ${path} failed: ${resp.status}`);
  return resp.json() as Promise<T>;
}

export const api = {
  health: () => getJson<{ status: string; provider: string }>("/health"),
  profile: () => getJson<Profile>("/profile"),
  tasks: () => getJson<{ open: Task[]; done: Task[] }>("/tasks"),
  applications: () =>
    getJson<{ applications: Application[] }>("/applications"),
  async chat(message: string): Promise<string> {
    const resp = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    if (!resp.ok) throw new Error(`POST /chat failed: ${resp.status}`);
    const data = (await resp.json()) as { reply: string };
    return data.reply;
  },
};

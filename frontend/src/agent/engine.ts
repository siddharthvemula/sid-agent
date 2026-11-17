// SidAgent web engine — a faithful TypeScript port of the Python agent
// (sid_agent/: providers.MockProvider + tools + agent.Agent formatting).
//
// Why it exists: Vercel serves this app as a static site, so the agent runs
// entirely in the browser. State lives in localStorage (per-visitor).
// Course lookup still hits the live umd.io API (it allows CORS); a small
// snapshot of core courses is the offline fallback. The fact-lock rule is
// identical to the Python version: replies are built ONLY from tool
// results, and unmatched requests get a plain refusal.
import profileData from "./profile.json";

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
  class_status: string;
  fall_2026_courses: string[];
  ap_credits: string[];
  projects: string[];
  experience: string[];
  skills: string[];
  goals: string[];
  internship_targets: string[];
  [key: string]: unknown;
}

export const PROFILE = profileData as Profile;

interface State {
  tasks: Task[];
  applications: Application[];
  memories: Record<string, string>;
  nextTaskId: number;
  nextAppId: number;
}

export interface StorageLike {
  getItem(k: string): string | null;
  setItem(k: string, v: string): void;
}

const STORAGE_KEY = "sidagent-state-v1";

function emptyState(): State {
  return { tasks: [], applications: [], memories: {}, nextTaskId: 1, nextAppId: 1 };
}

class Store {
  private state: State;
  private storage: StorageLike | null;

  constructor(storage?: StorageLike | null) {
    if (storage !== undefined) {
      this.storage = storage;
    } else {
      try {
        this.storage = window.localStorage;
      } catch {
        this.storage = null;
      }
    }
    this.state = this.load();
  }

  private load(): State {
    try {
      const raw = this.storage?.getItem(STORAGE_KEY);
      if (raw) return { ...emptyState(), ...JSON.parse(raw) };
    } catch {
      /* corrupted state -> start fresh */
    }
    return emptyState();
  }

  private save() {
    try {
      this.storage?.setItem(STORAGE_KEY, JSON.stringify(this.state));
    } catch {
      /* storage full/blocked -> keep running in-memory */
    }
  }

  createTask(title: string, due: string | null): Task {
    const task: Task = { id: this.state.nextTaskId++, title, due, status: "open" };
    this.state.tasks.push(task);
    this.save();
    return task;
  }

  listTasks(status = "open"): Task[] {
    return this.state.tasks
      .filter((t) => t.status === status)
      .sort((a, b) => (a.due ?? "9999").localeCompare(b.due ?? "9999") || a.id - b.id);
  }

  completeTask(id: number): { id: number; updated: boolean } {
    const t = this.state.tasks.find((x) => x.id === id);
    if (!t) return { id, updated: false };
    t.status = "done";
    this.save();
    return { id, updated: true };
  }

  logApplication(company: string, role: string): Application {
    const app: Application = { id: this.state.nextAppId++, company, role, status: "applied" };
    this.state.applications.push(app);
    this.save();
    return app;
  }

  listApplications(): Application[] {
    return [...this.state.applications];
  }

  updateApplication(company: string, status: string): { company: string; status: string; updated: number } {
    let updated = 0;
    for (const a of this.state.applications) {
      if (a.company.toLowerCase() === company.toLowerCase()) {
        a.status = status;
        updated++;
      }
    }
    if (updated) this.save();
    return { company, status, updated };
  }

  addMemory(key: string, value: string): { key: string; value: string } {
    this.state.memories[key] = value;
    this.save();
    return { key, value };
  }

  recallMemory(key: string): { key: string; value: string | null } {
    return { key, value: this.state.memories[key] ?? null };
  }

  snapshot(): { tasks: Task[]; applications: Application[] } {
    return { tasks: this.listTasks("open"), applications: this.listApplications() };
  }
}

// -- course lookup --------------------------------------------------------

const COURSE_CODE_RE = /\b[A-Z]{4}\d{3}[A-Z]?\b/g;

function parsePrereqs(text: string | null): string[] {
  if (!text) return [];
  const seen = new Set<string>();
  const out: string[] = [];
  for (const code of text.match(COURSE_CODE_RE) ?? []) {
    if (!seen.has(code)) {
      seen.add(code);
      out.push(code);
    }
  }
  return out;
}

interface CourseResult {
  course_id: string;
  found: boolean;
  name?: string;
  credits?: string;
  prereqs_text?: string | null;
  prereq_courses?: string[];
}

// Snapshot of core courses (fetched from umd.io) used only if the live
// API is unreachable from the browser.
const COURSE_FALLBACK: Record<string, CourseResult> = {
  CMSC132: { course_id: "CMSC132", found: true, name: "Object-Oriented Programming II", credits: "4", prereqs_text: "Minimum grade of C- in CMSC131 or CMSC133; or must have earned a score of 5 on the A Java AP exam; or must have earned a satisfactory score on the departmental placement exam; and minimum grade of C- in MATH140." },
  CMSC216: { course_id: "CMSC216", found: true, name: "Introduction to Computer Systems", credits: "4", prereqs_text: "Minimum grade of C- in CMSC132; and minimum grade of C- in MATH141." },
  CMSC250: { course_id: "CMSC250", found: true, name: "Discrete Structures", credits: "4", prereqs_text: "Minimum grade of C- in CMSC131; and minimum grade of C- in MATH141." },
  CMSC351: { course_id: "CMSC351", found: true, name: "Algorithms", credits: "3", prereqs_text: "Minimum grade of C- in CMSC250 and CMSC216." },
  MATH141: { course_id: "MATH141", found: true, name: "Calculus II", credits: "4", prereqs_text: "Minimum grade of C- in MATH140." },
  MATH240: { course_id: "MATH240", found: true, name: "Introduction to Linear Algebra", credits: "4", prereqs_text: "1 course with a minimum grade of C- from MATH141." },
};

async function courseLookup(courseIdRaw: string): Promise<CourseResult> {
  const courseId = courseIdRaw.toUpperCase();
  try {
    const resp = await fetch(`https://api.umd.io/v1/courses/${courseId}`);
    if (!resp.ok) throw new Error(`umd.io ${resp.status}`);
    const data = await resp.json();
    if (!Array.isArray(data) || data.length === 0) return { course_id: courseId, found: false };
    const c = data[0];
    const prereqText: string | null = c?.relationships?.prereqs ?? null;
    return {
      course_id: c.course_id,
      found: true,
      name: c.name,
      credits: c.credits,
      prereqs_text: prereqText,
      prereq_courses: parsePrereqs(prereqText),
    };
  } catch {
    const fb = COURSE_FALLBACK[courseId];
    if (fb) return { ...fb, prereq_courses: parsePrereqs(fb.prereqs_text ?? null) };
    throw new Error("live course lookup failed and no snapshot exists for this course");
  }
}

// -- planner (port of MockProvider) ---------------------------------------

interface ToolCall {
  name: string;
  args: Record<string, unknown>;
}

const PROFILE_TRIGGERS: [string[], string][] = [
  [["what courses", "my courses"], "fall_2026_courses"],
  [["my major", "what degree"], "degree"],
  [["when do i graduate", "graduation"], "graduation"],
  [["what school", "where do i go"], "school"],
  [["my goals", "what are my goals"], "goals"],
  [["my projects", "what projects"], "projects"],
  [["my skills", "what skills"], "skills"],
  [["my experience", "work experience"], "experience"],
  [["my name", "who am i"], "name"],
  [["internship targets", "targeting"], "internship_targets"],
  [["ap credits", "ap credit"], "ap_credits"],
];

function planSingle(userText: string): ToolCall[] {
  const text = userText.trim();
  const low = text.toLowerCase();
  let m: RegExpMatchArray | null;

  m = low.match(/^remind me to (.+?)(?:\s+by\s+(\d{4}-\d{2}-\d{2}))?$/);
  if (m) return [{ name: "create_task", args: { title: m[1], due: m[2] ?? null } }];

  m = text.match(/^log application to (.+?) for (.+)$/i);
  if (m) return [{ name: "log_application", args: { company: m[1], role: m[2] } }];

  m = low.match(/^(?:mark|complete) task (\d+)(?: as)? done$/);
  if (m) return [{ name: "complete_task", args: { task_id: parseInt(m[1], 10) } }];

  m = text.match(/^mark (.+?) as (.+)$/i);
  if (m) return [{ name: "update_application", args: { company: m[1], status: m[2] } }];

  for (const [triggers, field] of PROFILE_TRIGGERS) {
    if (triggers.some((t) => low.includes(t))) {
      return [{ name: "get_profile", args: { field } }];
    }
  }

  if (low.startsWith("remember that")) {
    const body = text.slice("remember that".length).trim();
    const idx = body.indexOf(" is ");
    if (idx >= 0) {
      return [{ name: "add_memory", args: { key: body.slice(0, idx).trim(), value: body.slice(idx + 4).trim() } }];
    }
  }
  m = low.match(/^what is my (.+?)\?$/);
  if (m) return [{ name: "recall_memory", args: { key: m[1] } }];

  if (low.includes("due") || low.includes("coming up")) return [{ name: "due_summary", args: {} }];
  if (low.includes("list") && low.includes("task")) return [{ name: "list_tasks", args: {} }];
  if (low.includes("list") && low.includes("application")) return [{ name: "list_applications", args: {} }];

  m = text.match(/\b([A-Z]{4}\d{3}[A-Z]?)\b/);
  if (m && (low.includes("prereq") || low.includes("look up") || low.includes("lookup"))) {
    return [{ name: "course_lookup", args: { course_id: m[1] } }];
  }
  return [];
}

function plan(userText: string): ToolCall[] {
  // Compound first (same rule as the Python provider): split on " and "
  // only when EVERY clause parses as an intent.
  if (userText.toLowerCase().includes(" and ")) {
    const clauses = userText.trim().split(/\s+and\s+/i);
    if (clauses.length > 1) {
      const calls: ToolCall[] = [];
      let ok = true;
      for (const clause of clauses) {
        const sub = planSingle(clause);
        if (sub.length === 0) {
          ok = false;
          break;
        }
        calls.push(...sub);
      }
      if (ok) return calls;
    }
  }
  return planSingle(userText);
}

// -- tools + formatting (port of tools.py / agent.py) ---------------------

function localToday(): Date {
  const n = new Date();
  return new Date(n.getFullYear(), n.getMonth(), n.getDate());
}

function parseDue(due: string): Date | null {
  const m = due.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!m) return null;
  return new Date(parseInt(m[1], 10), parseInt(m[2], 10) - 1, parseInt(m[3], 10));
}

function dueSummary(store: Store, withinDays = 7) {
  const today = localToday();
  const buckets: Record<string, Task[]> = { overdue: [], due_soon: [], later: [], no_date: [] };
  for (const task of store.listTasks("open")) {
    if (!task.due) {
      buckets.no_date.push(task);
      continue;
    }
    const d = parseDue(task.due);
    if (!d) {
      buckets.no_date.push(task);
      continue;
    }
    const delta = Math.round((d.getTime() - today.getTime()) / 86400000);
    if (delta < 0) buckets.overdue.push(task);
    else if (delta <= withinDays) buckets.due_soon.push(task);
    else buckets.later.push(task);
  }
  return { within_days: withinDays, ...buckets };
}

type Result = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

async function runTool(store: Store, call: ToolCall): Promise<Result> {
  switch (call.name) {
    case "create_task":
      return store.createTask(String(call.args.title), (call.args.due as string | null) ?? null);
    case "list_tasks":
      return { tasks: store.listTasks("open") };
    case "due_summary":
      return dueSummary(store);
    case "complete_task":
      return store.completeTask(Number(call.args.task_id));
    case "log_application":
      return store.logApplication(String(call.args.company), String(call.args.role));
    case "list_applications":
      return { applications: store.listApplications() };
    case "update_application":
      return store.updateApplication(String(call.args.company), String(call.args.status));
    case "course_lookup":
      return courseLookup(String(call.args.course_id));
    case "get_profile": {
      const field = String(call.args.field);
      return { field, value: (PROFILE as Record<string, unknown>)[field] };
    }
    case "add_memory":
      return store.addMemory(String(call.args.key), String(call.args.value));
    case "recall_memory":
      return store.recallMemory(String(call.args.key));
    default:
      return { error: `unknown tool: ${call.name}` };
  }
}

function formatResult(name: string, result: Result): string {
  if ("error" in result) return `Error: ${result.error}`;
  switch (name) {
    case "create_task": {
      const due = result.due ? ` (due ${result.due})` : "";
      return `Done - task #${result.id} created: '${result.title}'${due}.`;
    }
    case "list_tasks": {
      const tasks = result.tasks as Task[];
      if (!tasks.length) return "No open tasks.";
      const lines = ["Open tasks:"];
      for (const t of tasks) lines.push(`  #${t.id} ${t.title}${t.due ? ` - due ${t.due}` : ""}`);
      return lines.join("\n");
    }
    case "due_summary": {
      const labels: [string, string][] = [
        ["overdue", "Overdue"],
        ["due_soon", `Due in the next ${result.within_days} days`],
        ["later", "Later"],
        ["no_date", "No date"],
      ];
      const lines: string[] = [];
      for (const [key, label] of labels) {
        for (const t of result[key] as Task[]) {
          lines.push(`${label}: #${t.id} ${t.title}${t.due ? ` (due ${t.due})` : ""}`);
        }
      }
      return lines.length ? lines.join("\n") : "Nothing on your plate - no open tasks.";
    }
    case "complete_task":
      return result.updated ? `Task #${result.id} marked done.` : "No such task.";
    case "log_application":
      return `Logged application: ${result.company} - ${result.role} (status: ${result.status}).`;
    case "list_applications": {
      const apps = result.applications as Application[];
      if (!apps.length) return "No applications logged yet.";
      const lines = ["Applications:"];
      for (const a of apps) lines.push(`  ${a.company} - ${a.role} [${a.status}]`);
      return lines.join("\n");
    }
    case "update_application":
      return `Updated ${result.updated} application(s) for ${result.company} -> ${result.status}.`;
    case "course_lookup": {
      if (!result.found) return `No course found for ${result.course_id}.`;
      const prereqs = (result.prereq_courses as string[]).join(", ") || "none listed";
      return `${result.course_id} - ${result.name} (${result.credits} credits). Prerequisites: ${prereqs}. Full text: ${result.prereqs_text}`;
    }
    case "get_profile": {
      const value = result.value;
      if (Array.isArray(value)) return value.map((v) => `  - ${v}`).join("\n");
      return `${result.field}: ${value}`;
    }
    case "add_memory":
      return `Remembered: ${result.key} = ${result.value}.`;
    case "recall_memory":
      return result.value === null
        ? `I don't have anything stored for '${result.key}'.`
        : `${result.key}: ${result.value}`;
    default:
      return JSON.stringify(result);
  }
}

const REFUSAL =
  "I can't do that yet - no tool matches that request. " +
  "The web agent understands: 'remind me to ... by YYYY-MM-DD', " +
  "'log application to <Company> for <Role>', 'list tasks', " +
  "'list applications', 'what courses am I taking', " +
  "'remember that <key> is <value>', 'look up prereqs for <COURSE>', " +
  "'what's due this week?'.";

export interface Agent {
  handle(text: string): Promise<string>;
  getState(): { tasks: Task[]; applications: Application[] };
  profile: Profile;
}

export function createAgent(storage?: StorageLike | null): Agent {
  const store = new Store(storage);
  return {
    profile: PROFILE,
    getState: () => store.snapshot(),
    async handle(text: string): Promise<string> {
      const calls = plan(text);
      if (!calls.length) return REFUSAL;
      const parts: string[] = [];
      for (const call of calls) {
        let result: Result;
        try {
          result = await runTool(store, call);
        } catch (err) {
          result = { error: `${call.name} failed: ${err instanceof Error ? err.message : String(err)}` };
        }
        parts.push(formatResult(call.name, result));
      }
      return parts.join("\n");
    },
  };
}

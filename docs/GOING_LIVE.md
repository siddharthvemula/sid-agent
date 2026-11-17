# Going live — the two optional steps

SidAgent v1 works fully offline on the mock provider. Two steps remain, both
need Sid himself (his accounts, his keys). Each takes about 2 minutes.

## Step 1 — Push to GitHub

GitHub needs you to log in once; nobody else can do this for you.

1. Open a terminal in the project folder (`sid-agent`).
2. Log in to GitHub in the CLI:

   ```bash
   gh auth login
   ```

   Choose: **GitHub.com** → **HTTPS** → **Login with a web browser**.
   It shows a one-time code — enter it in the browser tab it opens.
3. Create the repo and push (private by default; add `--public` if you
   want it visible for resume links):

   ```bash
   ./scripts/push_to_github.sh            # private
   ./scripts/push_to_github.sh --public   # public
   ```

   That's it — the script creates `sid-agent` under your account and
   pushes. GitHub Actions will run the test suite, evals, and frontend
   build automatically on every push.

## Step 1b — Put it on the web with Vercel

The web app runs the agent entirely in the browser, so Vercel can host
it as a static site — free, no server, no keys.

- **With GitHub (after Step 1):** go to vercel.com → *Add New → Project →
  Import* → pick the `sid-agent` repo → Deploy. The `vercel.json` in the
  repo already has the right settings; don't change anything.
- **Without GitHub:** in a terminal in the project folder:

  ```bash
  npm i -g vercel
  vercel
  ```

  It asks you to log in (browser), then accept the defaults. You get a
  live `*.vercel.app` URL at the end.

Either way: visitors get their own copy of the agent (their tasks and
applications save in their own browser). The live-LLM upgrade in Step 2
applies to the local Python version; wiring a model into the hosted
site is a later step (serverless route + hosted database).

## Step 2 — Plug in a live LLM (optional)

The mock provider understands fixed patterns. A real model understands
anything you type.

1. Get an API key from the provider you prefer
   (Anthropic console → API Keys, or OpenAI platform → API Keys).
   SidAgent usage for personal testing costs a few dollars at most.
2. Copy `.env.example` to `.env` and fill in:

   ```bash
   SID_AGENT_PROVIDER=claude
   ANTHROPIC_API_KEY=sk-ant-...
   ```

   (or `openai` + `OPENAI_API_KEY`).
3. Restart the API/CLI. The agent loop, tools, and store don't change —
   only the planner gets smarter. The system prompt keeps the fact-lock
   rule: the model may only state what tools returned.

**Key safety:** keys live in `.env`, which is gitignored. Never paste a
key into chat, a commit, or an issue.

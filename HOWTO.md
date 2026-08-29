# How to use this in a real repo

## 0. Install once (existing app)

From the app’s root (the folder you open in the editor):

```bash
git clone --depth 1 --branch cursor/atlas-agent-harness-0002 --filter=blob:none --sparse \
  https://github.com/viswanathvs1981/agent-harness.git /tmp/agent-harness
git -C /tmp/agent-harness sparse-checkout set .agents
mkdir -p .agents
cp -R /tmp/agent-harness/.agents/. .agents/
cp .agents/AGENTS.md.example AGENTS.md   # merge if you already have AGENTS.md
rm -rf /tmp/agent-harness
```

Do not copy `.harness/`. If `.agents/bots/forge` already exists, diff — do not overwrite blind.

**Auto-align:** `AGENTS.md` at the app root must tell agents to follow `.agents/README.md`. Copy `.agents/AGENTS.md.example` to `AGENTS.md` (or merge). Then coding agents, incident guests, and the editor’s agent share the same gates.

Skills in `.agents/skills/` are Agent Skills: the editor can load them. Bots in `.agents/bots/` are the roster. Optional CLI from this repo: `pip install -e /path/to/agent-harness` then `bots run` inside the app.

---

## 1. You have a coding task

Stay in **that** repo. Do not paste the whole codebase into a new chat as the product.

| You want | What you do | What should happen |
| --- | --- | --- |
| Understand | “How does checkout fail today?” | **Read-only.** No file changes. Atlas or Forge explains. |
| Change code | “**Implement** X behind tests” (or `@Forge implement …`) | **Write on.** Still **no commit.** You review the diff. |
| Throw away a file | “**Delete** `path/to/file`” | Delete gate only for named paths. |
| Record git | “**Commit** these changes” | Commit gate. Never implied by implement. |

Typical loop:

1. Ask read-only until the spec is clear (or `@Shaper`).
2. `@Forge implement …` — one slice, tests if you have them.
3. You look at `git diff`.
4. `@Reviewer` or `@Sentinel` if it is risky (still read-only unless you ask for a fix).
5. You say **commit** only when you want a commit.

If the message is vague (“fix it”), it should **ask** and stay read-only.

---

## 2. You already have an incident agent (or any other agent)

Do **not** replace it. Drop it in as a **guest bot**. Atlas can `@` it. Forge stays the coder.

1. Create `.agents/bots/incident/BOT.md` (name = folder name).
2. Put its instructions in the body. **Read-only tools** until you know what it was allowed to do.
3. Point `skills:` at any of its procedures you copied into `.agents/skills/`.
4. `never:` include `prod_db`, `deploy`, `network` unless you truly want those.
5. Leave Forge as default for “implement”. Incident owns paging, runbooks, status — not random refactors.

Minimal guest:

```markdown
---
name: incident
title: Incident management
description: Triage, runbooks, comms. Use during an incident. Does not change application code unless the human says implement.
tools_read: [files_read]
tools_write: []
tools_delete: []
tools_commit: []
never: [prod_db, deploy, network, files_write, git_commit]
skills: [read-only-default]
---

# Incident

Page, diagnose, propose. Do not mute alerts or edit prod. If code must change, @Forge after the human says implement.
```

Same pattern for a security bot, a docs bot, a vendor GPT export: new folder, tight `never`, read-only first.

If you already have `AGENTS.md` / `.cursorrules` / `.claude/skills`: copy skills into `.agents/skills/`; turn long rule files into a guest `BOT.md` or a skill — your pick. Do not delete the old files until you are happy.

---

## 3. How they work together

One human thread. **One specialist doing work.** Others only if `@`d.

```
You: sev-2 payments 5xx, don’t change code yet
Atlas: @incident (read-only)
Incident: likely checkout timeout; runbook step 3
You: @Forge implement a retry on that client, tests only
Forge: write gate on, commit off
You: looks good, commit
```

Rules:

- Atlas routes; it does not implement.
- Incident and Forge do not share tools. Shared disk, separate allowlists.
- Idle bots cost nothing. Do not `@` all fourteen.
- Eval retries the **same** bot (max 3), then stops.

---

## 4. How you know it is efficient (and safe)

After a turn, check:

| Signal | Healthy | Unhealthy |
| --- | --- | --- |
| `write` / `delete` / `commit` flags | Match what you said | Write on for a question; commit on for “implement” only |
| `tools` list | Read tools on a question; `files_write` only after implement | `git_commit` or `network` appeared without you asking |
| Bots invoked | 1, maybe 2 | Whole roster woke up |
| Files actually changed | None on a question; only named slice on implement | Surprise edits, `.env`, files outside the repo |
| Time / steps | Done or blocked under 10 min / 24 steps | Retrying forever |
| Eval | Isolation 1.0, no surprise commit | `no_commit_unless_asked` = 0 |

CLI prints those flags:

```bash
bots run "How does checkout work?"
bots run "implement retry on checkout client" --bot forge
```

If a question run shows `"write": true` or a write tool, that is a bug — stop and tighten gates.

Efficiency is: **smallest bot, smallest tool set, smallest diff, then stop.** Not more agents.

# Agent contract (read this first)

If you are an agent in this repository: **follow this file.** Do not improvise a parallel process.

Drop-in layout:

```
.agents/bots/<name>/BOT.md     ← who
.agents/skills/<name>/SKILL.md ← how (load name+description first; body only if you activate it)
```

---

## Align automatically

1. List `.agents/bots/` and `.agents/skills/`. Use **one** bot per turn unless the human `@`s another.
2. Default **read-only**: no file updates, deletes, or git commits unless this message clearly asks.
3. Stay inside the project root. Never read/write `.env`, keys, `*.pem`, or paths outside the repo. No prod DB, no deploy, no extra network unless granted.
4. Do not wake the whole roster. Idle bots cost tokens; leave them idle.

**Write** only if they said implement / apply / write / fix / refactor / go ahead.  
**Delete** only if they said delete/remove **and** named paths.  
**Commit/push** only if they said commit or push — never implied by implement.

If unclear → ask, stay read-only.

---

## Coding tasks (Forge)

- Questions (“how does X work?”) → read, explain, propose a diff **in chat**. Zero tree changes.
- “Implement X” → Forge (or the human’s named coder). Tests first when tests exist. Smallest diff.
- After a write: stop for the human to review `git diff`. Do not commit unless asked.
- Do not “improve” unrelated files. Do not touch production config or secrets.

---

## Complex tasks (Atlas slices)

Do not one-shot a large epic in a single unbounded loop.

1. **Shaper** (read-only): outcome, in/out of scope, success checks, first slice.
2. Human confirms the slice (or they already named it).
3. **Forge** (or specialist) does **only that slice**, bounded (see below).
4. Eval / Reviewer if risky. Then the next slice in a **new turn**.

Complex = a **sequence of short runs**, not one 2-hour agent. Pass state as: the spec, the last diff, the failing test — not the entire repo in every prompt.

---

## Long-running work

Interactive turns are **not** overnight jobs.

| Limit | Cap | On hit |
| --- | --- | --- |
| Inner steps | 24 | Stop, report leftover |
| Eval retries | 3 | Stop, ask the human |
| Wall clock | 10 minutes | Stop |

“Keep going” from the human starts a **new** bounded turn (checkpoint: spec + current diff + last error). Do not silently loop.

Work that must continue while they are away is a **routine they opted into**, still with a per-run cap and no prod mutations without approval. There is no unbounded `while true`.

Incident / other guest bots (e.g. `.agents/bots/incident/`): they own their job. They do not implement app code unless the human said implement and `@Forge` (or they explicitly assigned that guest write).

---

## Token savings (yes, if you follow this)

This pack **saves tokens** by shrinking context and tool use. It does not magically compress a pasted monorepo.

Do:

- Load skill **names + descriptions** (~tens of tokens each). Open a skill **body** only when it matches the task.
- Run **one** bot. `@` a second only when needed. Never fourteen.
- Read-only questions: no write tools, fewer steps.
- Search/read the files you need; do not dump the whole tree into context.
- After a slice: keep a short summary, not the full trace, for the next turn.
- Prefer tests/allowlists over a long model-as-judge.

Don’t:

- Paste every skill body into the system prompt.
- `@` Atlas+Forge+Reviewer+Sentinel+Gauge “just in case.”
- Re-read the entire repo each retry.
- Retry evals without a bound.

If you ignore this file and load everything, you **will not** save tokens.

---

## Efficiency checklist (every turn)

- Tools on this turn match the words they used (write/delete/commit).
- At most 1–2 bots did work.
- Question → no file changes. Implement → no commit unless asked.
- Stopped by 24 steps / 3 retries / 10 minutes, or a clear blocker.

Guest agents: add `.agents/bots/<name>/BOT.md`, start read-only, keep Forge as default implementer.

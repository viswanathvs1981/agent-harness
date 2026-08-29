# Plan

Grok-style named bots for AI engineering. No workflow builder. You message teammates.

## Product

Sidebar of bots. 1:1 chat is default. `@Bot` pulls a specialist into a thread. `/skill` attaches a procedure. Share a pack link; the other person gets a **copy of the bot**, not your computer or memory.

```
You:  @Forge implement auth behind tests
Atlas: handing to Forge; Gauge will score
Forge: red test landed, writing the module
```

## Four objects

| | What it is | Share? |
| --- | --- | --- |
| **Bot** | Who. Name, job, description, tool fence, own chat | Profile + skill list + routines. Never memory, logins, transcripts |
| **Skill** | How. Portable `SKILL.md` (`/` menu) | Yes. Also works in Cursor / Claude / Codex |
| **Routine** | When this bot runs that skill | Yes, no secrets |
| **Harness** | Invisible loop, evals, checkpoints, learning | One runtime. Not forked per bot |

Do not pick skills *or* bots. Skills are know-how. Bots are teammates. The harness is generic.

**Forge** is the coding bot — separate chat, separate tools. It cannot deploy or touch production databases.

## Roster (Andrew Ng skills map as jobs)

Ship these five first: **Atlas, Shaper, Forge, Gauge, Sentinel**.

| Bot | Job | Must not |
| --- | --- | --- |
| Atlas | Chief of staff. Routes. `@`s specialists | Implement or deploy |
| Shaper | Spec / what to build / what “done” means | Write the code |
| **Forge** | Implement, refactor, tests | Prod DB, deploy, prod credentials |
| Reviewer | Diff critique | Merge unattended |
| Architect | Name the tradeoffs | Silently restack prod |
| Stack | UI + API slice | Same fence as Forge |
| Steward | Data models and lifecycle | Migrate without approval |
| Ground | Prompt vs tools vs vector vs graph | Overwrite the source of truth |
| Gauge | Evals and error analysis | Ship on vibes |
| Sentinel | Security, allowlists, injection | — (can halt a run) |
| Bridge | Ops: traces, cost, drift, CI | Change prod without approval |
| Lexer | LLM/context/model mix | Rotate prod keys |
| Signal | ML: when not to generate | Keep training data in bot memory |
| Coach | Turn traces into skill drafts | Auto-merge into the shared library |

## Persistence

Yes. Chat logs are not enough.

| Layer | Shared on pack link? |
| --- | --- |
| Thread checkpoint (resume / approval wait) | No |
| Per-bot memory (how you like this job) | No |
| Skill files | Yes |
| Routines (no secrets) | Yes |
| Traces + eval scores | No |
| Workspace files | No |

Learning = Grok “save that as a skill,” plus an eval gate so a lucky run is not published.

## Graph and loop (not the UI)

You never draw a graph.

Inside a turn: think → tool or `/skill` or `@bot` → eval. Fail retries the same bot, bounded. Pass may draft a skill.

Atlas `@`s Shaper → Forge → Gauge → Sentinel. You only see the thread.

## Isolation (where we do not copy Grok)

Grok shares one computer across all bots. We share a workspace for handoffs, but **each bot has a hard tool allowlist**. Forge cannot call deploy even if Bridge’s files are on disk.

## Share pack

```
forge.botpack
  bot.json       # name, title, description, tools, approval
  skills/        # SKILL.md folders
  routines.json  # no secrets
```

Recipient reconnects their own logins.

## v1 will not include

Visual graph editor. Per-bot cloud VMs. Auto-commit of evolved skills. Required embeddings. All 14 bots on day one.

## Build after this plan is accepted

1. Chat with Forge (1:1)
2. `@` via Atlas and `/` skills
3. Pack import/export
4. Eval gate on Forge
5. Memory + skill drafts (Coach)
6. Routines last

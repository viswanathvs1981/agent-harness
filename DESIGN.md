# Design: Grok-style bots on a generic AI-engineering harness

**Status:** plan and design. The Python in `agent_harness/` is a runtime sketch, not the product. Do not grow it until this document is the contract.

**Product metaphor:** [Grok Bot](https://docs.x.ai/grok-bot/overview) — a sidebar of named teammates you message. Not a DAG editor. Not a skill-file dump. Not one omniscient agent.

**Domain:** Andrew Ng / DeepLearning.AI [AI Engineering Skills Map](https://www.deeplearning.ai/the-batch/the-ai-engineering-skills-map) (Aug 2026).

---

## 1. What “like Grok bots” means

From xAI’s own model, a **Bot is one persistent named teammate**: name, title, description, avatar, its own conversation, working context that compounds. You do not draw a workflow. You create a bot, message it, grant access as needed.

| Grok Bot behavior | What we copy | What we change |
| --- | --- | --- |
| Sidebar of named bots; `@` to pull one into a thread | **The whole UX** | — |
| Create → message → grant access. No builder required | Same | Graphs exist *under* the bot, never as the UI |
| Skills = how; Routines = when; Bot = who | Same three objects | Evals gate skill promotion (Ng) |
| Share link copies **profile + skills + routines** | Same | Never share computer, logins, memory, or transcripts |
| Duplicate copies profile/skills/routines, **not** history | Same | Same |
| Bots DM each other and sit in group chats | Same | Conductor is a bot, not a hidden router you babysit |
| One shared computer (files, browser, terminal, logins) | Shared **workspace** for handoffs | **Tool policy is per-bot.** Coding must not be able to drop prod tables even if it can see the same disk |
| Teach-by-doing → skill draft → later a routine | Same evolution loop | Deterministic eval before a skill is shareable |
| Description = durable rules; messages = this task | Same | Approval boundaries live in the description |

xAI’s internal pattern we should copy literally: *one bot to manage the others, plus a specialist per lane, so you are not the middleman.*

---

## 2. The product (what a person sees)

```
┌─────────────┬──────────────────────────────────────────────┐
│ ROSTER      │  THREAD                                      │
│             │                                              │
│ Atlas ★     │  You:  @Forge implement auth behind tests    │
│ Forge       │  Atlas: handing to Forge; Gauge will score.  │
│ Shaper      │  Forge: red test landed, writing the module. │
│ Gauge       │  Gauge: eval task=0.91, isolation pass.      │
│ Sentinel    │  Sentinel: no prod tools in the trace.       │
│ …           │                                              │
│ + New bot   │  [ /verifier-first-coding ]  [@Forge]        │
└─────────────┴──────────────────────────────────────────────┘
```

- **1:1 chat** with a bot is the default. That bot owns the job and the memory of how you like it done.
- **Group chat** is for visible handoffs (Website Launch: Shaper + Forge + Reviewer + Gauge).
- **`@Bot`** adds a teammate mid-thread. **`/skill`** attaches a procedure. You are not wiring nodes.
- **Share** is a public pack link. Recipient **Add to roster** gets a copy of identity + enabled skills + routines. They do not get your VM, cookies, or private memory.

No workflow canvas in v1. If someone needs a canvas, the design has already failed.

---

## 3. Object model

```
Account
├── Computer / workspace          # files, terminal, optional browser, connectors
│                                 # shared for handoff, NOT a security boundary
├── Skill library                 # SKILL.md, Agent Skills standard, `/` menu
├── Bot roster                    # ≤ 50 bots + groups (same cap idea as Grok)
│     └── Bot
│           profile               # name, title, description, avatar
│           conversation          # 1:1 thread
│           memory                # preferences, stable facts, summaries
│           enabled_skills[]
│           routines[]            # schedule or event → run a skill
│           approval_boundary     # what may never happen unattended
│           tool_policy           # allowlist — our hard fork from Grok
│           eval_hooks[]          # verifiers this bot must close
└── Group chats
      members: Bot[]
      thread
```

### What is a bot vs a skill vs a routine vs the harness

| Object | Question it answers | Shareable? | Example |
| --- | --- | --- | --- |
| **Bot** | Who owns this job, with what voice, tools, and stop-the-line rules? | Pack: profile + skill ids + routines. **Not** memory/computer | `Forge` — isolated coder |
| **Skill** | How do we do this procedure, any bot that is allowed to? | Yes — `SKILL.md`, works in Cursor/Claude/Codex too | `verifier-first-coding` |
| **Routine** | When should *this* bot run that skill? | Yes, as config, without secrets | Weekdays 8:00, run eval regression |
| **Harness** | How do bots loop, checkpoint, eval, learn, and talk? | One runtime. Do not fork per bot | Graph+loop, stores, pack import |
| **Computer** | Where does the work actually happen? | Never via share link | Project workspace |

**Decision (the question from the last turn):** do not choose skill files *or* full-blown agents. Grok already split them correctly. **Bots are the droppable product. Skills are the portable know-how. The harness is generic and invisible.**

Build skill files for procedures. Build bots (not anonymous graph nodes) for roles. Ship packs so anyone can add a bot the way they Add to Grok Bot.

---

## 4. Persistence (yes, layered — same reasons as Grok)

Grok: named bots keep memory, files, sessions, preferences; context compounds; share copies identity not history.

We need the same layers, named so we do not smash them into one sqlite blob:

| Store | Lives with | Shared on pack link? | Purpose |
| --- | --- | --- | --- |
| Thread / checkpoint | conversation | No | Resume after crash or approval wait |
| Bot memory | one bot | No | How you like *this* job done |
| Skill files | git / library | Yes | Procedures that survived evals |
| Routines | bot config | Yes (no secrets) | Schedule / event triggers |
| Episode traces | harness | No | Ng error analysis |
| Eval scores | harness | No (summaries may be) | Gate promotion |
| Workspace disk | account computer | No | Files, repos, browser profile |

Skip persistence and you get a chat toy: no resume, no learning, no shareable skill that is more than a pasted prompt.

Embeddings are optional later. Default retrieve is the **memory graph** (episode → lesson → skill) plus keyword/neighbor walk. That matches Ng’s grounding menu (vector *or* graph *or* semantic layer) without forcing a vector vendor into a droppable pack.

---

## 5. Graph and loop engineering (invisible)

Ng: workflows (you chain steps) vs harness (the model picks the next step). Production is hybrid.

**User-visible:** message, `@`, `/`, approval card.

**Inside one bot turn:**

```
message in
  → assemble: profile + enabled skill metadata + recalled memory
  → INNER LOOP (harness): think | /skill | tool | @other-bot | ask-you | finish
  → EVAL gate (deterministic first)
  → fail: loop the same bot with the trace (bounded)
  → pass: persist memory + maybe draft a skill
```

**Inside a group / @-handoff:**

```
Atlas (chief of staff)
  → @Shaper if the spec is missing
  → @Forge for implementation   (own context, own tool_policy)
  → @Gauge for scoring
  → @Sentinel if tools or data are dangerous
  → back to you only for approval
```

That outer path *is* a graph. We may store it as JSON for the runtime. We do not show it as a builder. Loops are bounded (`max_iters` / give_up). Eval failure retries the owning bot, then still learns from the miss.

**Coding bot is a separate teammate**, not a skill called “write code.” Grok’s rule: split a bot when the job has a distinct goal, tool set, working style, approval boundary, or schedule. Coding hits all five. Ng’s warning (do not let a coding agent mess up production) is the approval/tool boundary on `Forge`.

---

## 6. How the harness actually runs (once we build)

1. You open **Forge** (or `@Forge` in a group).
2. Harness loads Forge’s profile, enabled skill *names*, last memory summaries, not the whole library.
3. Inner loop runs on Forge’s tool allowlist only (`files`, `git`, tests — never `prod_db`, never deploy).
4. Forge activates `/verifier-first-coding` when the task matches (progressive disclosure).
5. Eval bot **Gauge** (or a silent eval hook) scores isolation, tests, “no prod mutation.”
6. Fail → Forge again with the error bucket. Three misses → stop and ask you.
7. Success → episode stored. If the same job class succeeded twice and evals passed, **draft** a skill. You (or Gauge) promote it into the library. Only then may a routine schedule it.
8. Share Forge → recipient gets profile + skill ids + routines. Their Forge is amnesiac until they work with it. Correct: that is Grok’s duplicate/share semantics.

Self-evolution is Grok’s “save that as a skill / teach a task / then routine,” plus Ng’s eval gate so we do not publish a lucky trace.

---

## 7. Starter roster (Ng map → Grok-style jobs)

Keep the roster small. Grok: add a bot only when the work has a stable specialist role. Names are **jobs**, not framework modules.

| Bot | Title | Owns | Approval line |
| --- | --- | --- | --- |
| **Atlas** | Chief of staff | Routing, group handoffs, “workflow vs loop” | Never implements prod code or deploys |
| **Shaper** | Spec / PM | What goes in the spec, MVP vs careful, success evidence | Never writes the implementation |
| **Forge** | Coding teammate | Implement, refactor, tests in a sandbox | Never production DB, never deploy, never prod credentials |
| **Reviewer** | Diff critic | Correctness, blast radius, spec drift | Can block; cannot merge unattended |
| **Architect** | Systems | Tradeoffs: cost, latency, consistency, granularity | Advises; does not silently restack prod |
| **Stack** | Full-stack | Vertical UI+API+persistence slice | Same fence as Forge for prod |
| **Steward** | Data | Models, lifecycle, agent-readable stores | Migrations need your OK |
| **Ground** | Grounding | Prompt vs tool vs vector vs graph vs semantic layer | No silent corpus overwrite |
| **Gauge** | Eval lead | Metrics, judges, error analysis, eval-the-eval | Cannot ship on vibes |
| **Sentinel** | Security | Injection, allowlists, exfil, supply chain | Can halt a run |
| **Bridge** | Ops / SRE | Traces, drift, cost, latency, CI | Prod changes need approval |
| **Lexer** | LLM engineer | Context, caching, model mix, tool schemas | Cannot rotate prod keys |
| **Signal** | ML engineer | Bias/variance, when not to generate | Training data stays in source systems |
| **Coach** | Evolution | Distill traces → skill drafts | Cannot auto-merge to the shared library |

**Forge is the separate coding agent.** Atlas may `@Forge`; Forge does not inherit Bridge’s deploy tools.

Starter skills (portable `SKILL.md`, `/` menu): eval-driven-development, verifier-first-coding, tdd-for-agents, context-management, error-analysis, rag-vs-tools, workflow-vs-harness, graph-loop-engineering, production-observability, guardrails, shaping-the-build, data-lifecycle, skill-authoring, close-the-loop.

---

## 8. Share contract (droppable with anyone)

Pack on the wire (public, like a Grok share link):

```
forge.botpack
  bot.json          # name, title, description, avatar, tool_policy, approval
  skills/           # SKILL.md folders (Agent Skills standard)
  routines.json     # schedules/events with no secrets
  README            # what this bot will not do
```

**Included:** identity, description, enabled skills, routine *shape*.  
**Excluded:** memory, transcripts, workspace, cookies, API keys, customer data.

If a routine needs a connector, the pack lists the connector *name*. The recipient reconnects on their computer.

Skills stay valid outside this harness: copy `skills/verifier-first-coding` into `.agents/skills/` for Cursor / Claude Code / Codex.

---

## 9. Isolation: where we refuse to copy Grok

Grok is explicit: the computer is **account-scoped**, not per-bot. Logins and files are available to every bot. That is convenient for handoffs and unacceptable as the only fence for a coding teammate next to an ops teammate.

**UX like Grok. Permissions unlike Grok.**

- Shared workspace so Atlas can hand Forge a repo path.
- **Per-bot tool allowlist** as a hard gate (hooks, not prompt text).
- Forge cannot invoke deploy / prod_db / kubectl even if the files are on disk.
- Human node before send, purchase, delete, publish, or production mutate — same as Grok’s “design routines for trust,” made mandatory for Bridge and Forge.

---

## 10. What we will not build in v1

- A visual graph editor
- Per-bot cloud VMs (Grok’s full computer) — start with one workspace + allowlists
- Auto-commit of evolved skills
- Embedding service as a required dependency
- 50 novelty personas. Fourteen jobs covering the skills map is already fat; ship Atlas, Shaper, Forge, Gauge, Sentinel first if we cut

---

## 11. Build order (after this design is accepted)

1. **Bot profile schema** (`bot.json` / `BOT.md`) and roster loader — no new graph features.
2. **Chat surface:** 1:1 with Forge; `@` dispatch via Atlas; `/` skills.
3. **Pack import/export** matching the share contract.
4. **Eval gate + bounded retry** on Forge.
5. **Memory + skill drafts** (Coach), promotion manual.
6. Routines last (Grok: one-time task → skill → then automate).

The existing `agent_harness` package is allowed to become the invisible runtime for steps 3–5. It must not define the UX.

---

## 12. One-line summary

Talk to **named bots** like Grok teammates. Put **know-how in skills** anyone can `/` or copy. Keep a **generic harness** for loop, graph, evals, and learning. **Persist** threads, bot memory, traces, and evals; **share** only profile + skills + routines. Give **Forge** its own chat and a tool fence so coding cannot become ops.

# Research: skills vs agents, persistence, and a generic self-evolving harness

**Product contract:** [DESIGN.md](DESIGN.md) (Grok-style named bots). This file is background research. If the two conflict, DESIGN wins.

This note is the design rationale for this repo. It is based on:

- Andrew Ng / DeepLearning.AI, **The AI Engineering Skills Map** (14 Aug 2026) and the two follow-ups: *Building and Deploying AI Applications* (21 Aug 2026) and *Software Engineering Fundamentals* (28 Aug 2026).
- The **Agent Skills** open standard (`SKILL.md`, progressive disclosure), now loaded by Claude Code, Cursor, Codex, Copilot, OpenCode, and others.
- Production agent practice: Claude Code / Cursor harness layers (rules, skills, hooks, sub-agents, MCP); LangGraph-style graph orchestration with checkpoints; self-evolving memory work (Metis, ReMe, Mem2Evolve).

## 1. What the skills map actually says (and why a harness cares)

Ng's top level is four skills, not a job title:

1. **Building and deploying AI applications** — because outputs are unpredictable. Sub-skills: LLM foundations, grounding with data, building agentic systems, **evaluation-driven development**, operating in production, ML foundations.
2. **Software engineering fundamentals** — so you can *name the tradeoffs* a coding agent will otherwise make badly: full-stack, data, architecture, security/reliability, scale/ops.
3. **Using coding agents** — mental model of agents, context, plan vs execute, **closing loops with verifiers**, multi-agent orchestration, not letting an agent trash prod.
4. **Shaping the build** — as specs get easier to implement, the scarce work is deciding what belongs in the spec, what success evidence is, when to spike vs slow down.

Two sentences from Ng should drive architecture:

- Agentic systems range from **workflows** (a predefined sequence of LLM calls) to an **agent harness** (the model repeatedly chooses the next step). You choose what to chain, what to parallelize, when to use code vs an LLM, plus tools, memory, long-session context, and when to go multi-agent.
- The trait that distinguishes people who are great at this is a **disciplined evals / error-analysis loop**. Without it, RAG, agents, and prod ops are unsteerable.

This repo treats those as *runtime invariants*, not as a reading list.

## 2. Should we build skill files or full-blown agents?

**Both. They are different layers. Do not pick one.**

| | Skill (`SKILL.md`) | Agent (`AGENT.md`) | Harness |
| --- | --- | --- | --- |
| Job | *How* to do a procedure | *Who* runs, with which tools and isolation | *When* things run, how they loop, what is remembered |
| Context | Progressive disclosure (name/description always; body on activation; scripts on demand) | Own system prompt, tool allowlist, skill list, isolation | Graph + inner loop + stores |
| Share with anyone | Yes — this is the portable unit. One folder works in Cursor, Claude Code, Codex, Copilot if you author to the open spec | Yes, but as a **pack** (agent + its skills + optional graph). Isolation and tools are part of the contract | Share the runtime once; do not fork it per specialist |
| Lifetime | Procedural memory (SOPs) | Role / identity | Product |
| Fail mode if overused | 40 skills dumped into one prompt = context death | 15 “god agents” that all have shell+prod DB | A new framework per task |

### What should be a skill

Repeatable procedures that **any** agent might need: verifier-first coding, error analysis, eval design, RAG vs tools, guardrails, skill authoring. If you find the same instructions copied into three agent prompts, it is a skill.

Author to the [Agent Skills spec](https://agentskills.io/specification): `name` + `description` (what **and** when), directory name matches, body under ~500 lines, details in `references/` / `scripts/`. Put them in `.agents/skills/` if you want other products to discover them without this harness.

### What should be an agent

A **bounded execution identity**:

- Different tool permissions (coding must not equal ops).
- Different isolation (clean context, sandbox, no inherited prod skills).
- Different stop conditions and evals.
- You would not want its transcript mixed into another role's reasoning.

The **coding agent is a separate agent**, not a skill named “write code”. Ng's “using coding agents” skill is *for humans and orchestrators*: how to steer that agent. The agent itself needs its own context, verifiers, and a hard fence around production.

Anthropic's own split is the same: skills teach expertise any agent can apply; sub-agents exist for independent execution, permissions, and context isolation.

### What should stay generic (the harness)

Do **not** bake orchestration, persistence, or evolution into every specialist. That is how packs stop being droppable. The harness owns:

- Graph execution (workflow)
- Inner ReAct loop (harness in Ng's sense)
- Skill discovery / progressive disclosure
- Checkpoints, eval store, memory graph
- Promotion of new skills behind eval gates
- Pack import/export

Hooks (deterministic gates) belong in the harness too: path sandbox, tool allowlists, blocked shell. Prompts are not control.

### Packs: the unit you actually email someone

```
coding-pack/
  pack.json
  AGENT.md
  skills/verifier-first-coding/SKILL.md
  graph.json          # optional
```

Skills inside the pack remain valid standalone Agent Skills. Someone without this harness can still drop the skill folders into Cursor. Someone with the harness also gets isolation and the coding graph.

**Do not share raw memory databases.** Lessons are environment-specific and can contain secrets. Share skills that survived evals; keep the graph memory local (or behind an org store).

## 3. Do we need persistence?

**Yes, if you want any of: resume, evals, multi-step coding, learning.** A chat log is not persistence.

Use **layers**, not one blob:

| Layer | Lifetime | Backend here | If you skip it |
| --- | --- | --- | --- |
| Working context | one inner-loop window | messages in `RunState` | Agent forgets the current tool result |
| **Checkpoint** | one thread, crash/HITL | SQLite `checkpoints` | Long coding loops restart from zero (the LangGraph lesson) |
| Episode traces | weeks, for error analysis | SQLite `episodes` | You cannot do Ng's eval loop |
| Eval scores | as long as you ship | SQLite `evals` | Evolution will promote junk |
| **Graph memory** | across threads | SQLite `memory.db` nodes/edges | No learning, no grounding beyond the prompt |
| Procedural memory | across teams | `SKILL.md` files (git) | Knowledge dies in one transcript |
| Promoted skills | after eval gate | `.harness/state/evolved-skills/` | Self-evolution is theater |

LangGraph production practice matches this: checkpoint after every node (Sqlite in dev, Postgres in prod), `thread_id` to resume, TTL so checkpoints do not grow forever, fat blobs in object storage not in the checkpoint. This repo starts on SQLite so it is droppable; swap the `Store` / `MemoryGraph` backends without touching agents.

You do **not** need embeddings on day one. Ng's grounding menu is vector **or** knowledge graph **or** semantic layer. A typed graph (episode → lesson → skill, agent → skill) plus keyword retrieval is the right default for a shareable harness. Plug in vectors later as a retrieve strategy, not as the schema.

## 4. How the whole harness works

```
                    ┌─────────────────────────────────────────┐
  goal + thread_id  │                 HARNESS                  │
                    │  catalog (agents, skills, graphs)        │
                    │  tools (allowlisted per agent)           │
                    └───────────────┬─────────────────────────┘
                                    ▼
                         ┌──────────────────┐
                         │  OUTER GRAPH     │  workflow (deterministic)
                         │  router → spec   │
                         │  → conductor     │
                         │  → LOOP node     │
                         │  ⇄ EVAL gate     │  fail: retry; give_up: evolve
                         │  → reviewer      │
                         │  → evolve → end  │
                         └────────┬─────────┘
                                  ▼
                         ┌──────────────────┐
                         │  INNER LOOP      │  harness (model chooses)
                         │  think / tool /  │
                         │  activate_skill /│
                         │  spawn / finish  │
                         └────────┬─────────┘
                                  ▼
                         ┌──────────────────┐
                         │  SPECIALISTS     │  droppable AGENT.md
                         │  coding (isolated│
                         │   context+tools) │
                         │  spec, eval, ops │
                         │  security, ...   │
                         └────────┬─────────┘
                                  ▼
                         ┌──────────────────┐
                         │  EVOLUTION       │  observe → distill →
                         │  memory graph    │  promote skill iff
                         │  eval gate       │  repeated success
                         └──────────────────┘
```

**Graph engineering (outer):** typed nodes (`router`, `agent`, `loop`, `eval`, `evolve`, `human`, `parallel`, `end`). Conditional edges. Loops are explicit and bounded. This is the “workflow” side of Ng's spectrum and the same idea as LangGraph / Google ADK Sequential/Loop/Router agents: code owns structure; the model owns the messy middle.

**Loop engineering (inner):** one specialist, budgeted steps, skills loaded on demand, tools denied if not on the agent. The coding graph is a *separate* graph so implementation cannot accidentally pick up ops nodes.

**Eval loop:** the eval node is a gate, not a report. Fail routes back into the specialist with traces. Three failures → `give_up` → still evolve (learn from the miss). Mix deterministic checks (isolation, no prod DB, has output) with later judges/humans.

**Self-evolution:** after every run, distill lessons (success patterns *and* failure triggers), bump usefulness, prune junk (ReMe: refine, do not hoard). If the same class of goal succeeds twice and evals passed, promote a real `SKILL.md` (Metis/Mem2Evolve: text memory first, then assets). Never rewrite the generic harness from one lucky trace.

**Multi-agent:** spawn is a child `RunState` with its own context; the parent does not keep the child's full transcript. Coding isolation strips inherited skills that the coding agent is not allowed to hold.

## 5. Best-practice rules we encoded

1. **Hybrid control flow** — graph outside, loop inside. Pure ReAct is hard to eval; pure DAGs cannot recover from surprise.
2. **Evals steer development** — if you cannot measure it, do not add another agent.
3. **Coding agent is fenced** — own context, own tools, no prod. Verifier-first. Humans approve irreversible actions, not every compile.
4. **Progressive disclosure** — skill metadata at boot; body on activation. Do not put SOPs in a giant always-on rules file.
5. **Skills portable, agents packaged, harness generic.**
6. **Persistence is layered**; memory is a graph; promotion is gated.
7. **Grounding is a menu** — prompt vs tool vs vector vs graph vs semantic layer.
8. **Hooks over vibes** for safety (allowlists, path sandbox, blocked commands).
9. **Share packs, not brains** — git the skills that survived; keep local lessons local.
10. **Keep learning operational** — evolved skills are files you can read, diff, and delete.

## 6. What we did *not* do (on purpose)

- Did not take a hard dependency on LangGraph/LangChain. The graph/loop ideas are the standard; the runtime should stay copy-pasteable. You can rehost these graphs on LangGraph later if you need Postgres checkpointers at scale.
- Did not put embeddings in the critical path.
- Did not merge “coding” into the conductor. That recreates the prod-db failure mode.
- Did not auto-merge evolved skills into the shared catalog. Promotion writes a draft skill; humans (or a later CI eval) still own the git commit.

## 7. If you only remember one thing

Build a **generic harness**. Put **know-how in skill files** that anyone's agent can load. Put **roles in droppable agents** with isolation and tool contracts — especially a separate coding agent. Persist **checkpoints, traces, evals, and a memory graph**, and only let the system learn when an eval says the lesson worked.

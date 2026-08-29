# Agent Harness — Grok-style bots for AI engineering

**Read [DESIGN.md](DESIGN.md) first.** That is the product contract.

This repo is a **roster of named bots** you message like Grok teammates (Atlas, Forge, Gauge, …), mapped to [Andrew Ng’s AI Engineering Skills Map](https://www.deeplearning.ai/the-batch/the-ai-engineering-skills-map). The generic harness (graph, loop, evals, memory) stays **invisible**. There is no workflow builder.

## The product

- **Bots** — durable teammates with a job, description, tool fence, and own chat. `@` them into a thread.
- **Skills** — portable `SKILL.md` procedures (`/` menu). Shareable across Cursor, Claude Code, Codex.
- **Routines** — when a *specific* bot should run a skill (after the skill is reliable).
- **Packs** — share **profile + skills + routines**. Never memory, computer, logins, or transcripts.
- **Forge** — the separate coding bot. It cannot deploy or touch production databases.

Starter roster and share contract: [`design/bots/`](design/bots/README.md). Example pack: [`design/packs/forge.botpack.json`](design/packs/forge.botpack.json).

Research notes (skills vs agents, persistence layers): [RESEARCH.md](RESEARCH.md). If RESEARCH and DESIGN disagree, **DESIGN wins**.

## Build status

Design is the milestone. `agent_harness/` is a runtime sketch (catalog, graph/loop, sqlite stores). Do not treat the CLI as the UX.

```bash
python3 -m unittest discover -s tests -v
```

## Next (from DESIGN §11)

1. Bot profile loader for `design/bots/*/BOT.md`
2. Chat surface: 1:1 Forge, `@` via Atlas, `/` skills
3. Pack import/export matching the share contract
4. Eval gate on Forge
5. Memory + skill drafts (Coach)
6. Routines last

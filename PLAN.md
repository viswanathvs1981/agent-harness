# Plan

Grok-style named bots. You message teammates. No workflow builder.

A task does **not** run forever. Interactive work has a budget. Only a routine (scheduled job you opted into) may keep going after you close the chat.

Drop bots and skills as folders in the repo. Cursor and VS Code already load Agent Skills from `.agents/skills/`.

---

## Product

Sidebar of bots. 1:1 chat is default. `@Bot` pulls a specialist in. `/skill` attaches a procedure. Share a pack = copy of the bot, not your memory or computer.

```
You:  @Forge implement auth behind tests
Atlas: handing to Forge; Gauge will score
Forge: red test landed, writing the module
```

## Four objects

| | What | Share? |
| --- | --- | --- |
| **Bot** | Who — name, job, tool fence, own chat | Profile + skills + routines. Not memory, logins, transcripts |
| **Skill** | How — `SKILL.md` | Yes. Cursor / VS Code / Claude / Codex |
| **Routine** | When this bot runs that skill | Yes, no secrets |
| **Harness** | Invisible loop, evals, checkpoints | One runtime |

**Forge** is the separate coding bot. No prod DB, no deploy.

## A task will not take forever

Interactive (you sent a message):

| Limit | Default | What happens when hit |
| --- | --- | --- |
| Steps in the inner loop | 24 | Stop, return what exists, say what is left |
| Eval retries | 3 | Stop, ask you; do not keep “just one more try” |
| Wall clock | 10 minutes | Same |
| Parallel bots | 3 | Queue the rest |
| Tokens / cost | per-bot cap | Stop |

The bot must **close the loop** (test, eval, or a clear blocker) before those limits, or stop. Humans are for approval, not for babysitting a 40-minute retry.

Routines (opt-in, scheduled) are the only path that runs while you are away. They still have a per-run budget and an approval line for prod.

## Where files live (this repo / this project)

On first use, create this in the **project root** (the folder you opened in Cursor or VS Code):

```
.agents/
  README.md                 # drop rules
  bots/
    atlas/BOT.md            # drop a bot = drop a folder
    forge/BOT.md
    gauge/BOT.md
    ...
  skills/
    verifier-first-coding/SKILL.md    # drop a skill = drop a folder
    eval-driven-development/SKILL.md
    ...
.harness/                   # created locally, not shared, not committed
  state/                    # checkpoints, bot memory, traces
  evolved-skills/           # drafts only; promote into .agents/skills/ by hand
```

How you drop things:

- New skill: copy `my-skill/SKILL.md` into `.agents/skills/my-skill/`
- New bot: copy `my-bot/BOT.md` into `.agents/bots/my-bot/`
- Share with a teammate: zip that folder, or send the pack. They paste it into **their** `.agents/`

Cursor / VS Code:

- Skills in `.agents/skills/*/SKILL.md` follow the Agent Skills standard. Cursor, VS Code Copilot, Claude Code, Codex already look here (or also under `.cursor/skills/`, `.github/skills/`). We use **one** vendor-neutral path: `.agents/skills/`.
- Bots are our extra: `.agents/bots/`. Cursor will not auto-run `BOT.md` until a harness exists; you can still edit them in the IDE like any markdown. Optional mirror: `.cursor/agents/` later if we add a Cursor adapter.
- Do **not** put secrets in `.agents/`. Local memory stays in `.harness/` and is gitignored.

Workspace code (the app you are building) stays in the rest of the repo. Bots edit that tree; they do not store their identity inside `src/`.

## Roster (ship first: Atlas, Shaper, Forge, Gauge, Sentinel)

| Bot | Job | Must not |
| --- | --- | --- |
| Atlas | Chief of staff, `@` specialists | Implement or deploy |
| Shaper | Spec / what “done” means | Write the code |
| **Forge** | Implement, tests | Prod DB, deploy |
| Reviewer | Diff critique | Merge unattended |
| Architect | Tradeoffs | Silently restack prod |
| Stack | UI + API slice | Same fence as Forge |
| Steward | Data lifecycle | Migrate without approval |
| Ground | Prompt vs tools vs vector vs graph | Overwrite source of truth |
| Gauge | Evals | Ship on vibes |
| Sentinel | Security | — (can halt) |
| Bridge | Ops | Change prod without approval |
| Lexer | LLM / context | Rotate prod keys |
| Signal | ML | Keep training data in memory |
| Coach | Skill drafts from traces | Auto-merge to `.agents/skills/` |

## Persistence

| Layer | On disk | In git / pack? |
| --- | --- | --- |
| Bots + skills | `.agents/` | Yes |
| Checkpoints, memory, traces | `.harness/state/` | No |
| Skill drafts | `.harness/evolved-skills/` | No until you promote |

## Graph / loop (invisible)

think → tool or `/skill` or `@bot` → eval. Fail retries the **same** bot, max 3. Then stop.

## Isolation

Shared project files. **Per-bot tool allowlist.** Forge cannot deploy.

## Pack

```
forge.botpack
  BOT.md
  skills/     # SKILL.md folders this bot enables
  routines.json
```

Recipient drops it into `.agents/bots/forge/` and `.agents/skills/`.

## What is special (vs a generic coding agent)

These are not fourteen chat personas. Each bot is a **job from Ng’s map** with a stop-the-line rule, a tool fence, and an eval. The scarce things Ng named are the product:

1. **Shaping the build** is a bot (Shaper), not a preamble in Forge’s prompt.
2. **Using coding agents** is a *separate* bot (Forge) with verifiers, not Atlas writing code.
3. **Evaluation-driven development** is a bot + a gate (Gauge), not a checklist at the end.
4. **Software fundamentals** show up as Architect / Steward / Sentinel / Bridge, so Forge is steered in engineering language instead of vibe-coding.

Also special operationally: progressive disclosure (load skill *names*, not every SOP), bounded runs, share-as-copy, and Coach that only promotes a skill after evals pass.

## Alignment with Andrew Ng’s skills map

Ng’s four top skills (Aug 2026), then the published sub-skills. Every roster seat maps; nothing is a mascot.

| Ng skill | Sub-skill (where published) | Bot |
| --- | --- | --- |
| Shaping the build | Spec, MVP vs careful, success evidence | **Shaper**, **Atlas** |
| Using coding agents | Context, plan vs execute, close loops with verifiers, multi-agent, don’t trash prod | **Forge**, **Reviewer**, **Atlas** |
| Building & deploying AI apps | LLM foundations | **Lexer** |
| | Grounding with data | **Ground** |
| | Building agentic systems (workflow vs harness, tools, memory, multi-agent) | **Atlas** + harness |
| | Evaluation-driven development (the one Ng calls most important) | **Gauge**, **Coach** |
| | Operating in production | **Bridge** |
| | ML foundations | **Signal** |
| Software engineering fundamentals | Full-stack | **Stack** |
| | Managing data | **Steward** |
| | System architecture | **Architect** |
| | Secure and reliable | **Sentinel**, **Reviewer** |
| | Scale / operate in production | **Bridge** |
| Continuous learning (under the whole map) | Keep evolving workflows | **Coach** |

Coverage is the map, not a parallel universe. If Ng later publishes “using coding agents” sub-skills, they attach to Forge’s skills, not a new brand.

## Fresh repo vs existing repo

**Fresh repo.** First open creates `.agents/` (starter five bots + core skills) and gitignored `.harness/`. There is almost no app code. Forge will not invent a product; Shaper has to write a spec or you give one. Atlas is the default chat.

**Existing repo.** Same folders, **additive**. Nothing in `src/` is rewritten on install. The harness reads the tree (layouts, tests, existing agents) and **does not replace** `.cursor/rules`, `AGENTS.md`, `CLAUDE.md`, or Copilot instructions. Those are inbound candidates (see fold-in below).

Operate the same in both: you message a bot; it only uses tools on its allowlist; it writes in the repo; Gauge scores; stop on budget. Difference is context: existing repo has code, tests, and maybe rival agent files. Fresh repo has none — Forge must be given a slice or it should refuse to “build the whole product.”

If `.agents/` already exists, drop-in **merges by folder name**: same slug = you choose keep / replace / diff. Never silent overwrite.

## How they operate (one task)

1. You talk to Atlas (or `@Forge` directly).
2. Atlas loads **metadata** of enabled skills (~name + when to use), not full text.
3. If the spec is missing, `@Shaper`. If it is code, `@Forge` with a **fresh context** and Forge’s tools only.
4. Forge activates one skill (e.g. verifier-first), edits files, runs a check, `record_eval`.
5. Fail → Forge again, max 3. Pass → Reviewer/Sentinel only if the change is risky.
6. Coach may **draft** a skill in `.harness/evolved-skills/`. You copy it into `.agents/skills/` to keep it.

You never assign all 14. Idle bots cost zero.

## Efficiency

Cheap by default:

- One bot in the loop unless Atlas `@`s another.
- Skills: metadata first, body on activation, scripts only if needed.
- Deterministic evals (tests, allowlists) before LLM-as-judge.
- Caps: 24 steps, 3 retries, 10 minutes, 3 parallel bots.
- No embeddings required; memory is a small graph + keywords.

Expensive on purpose: Gauge judging prose, Sentinel on untrusted input, Architect on a greenfield design. Not expensive: “every message wakes the whole roster.”

## Fold in and improve existing agents (“fine-tune”)

**Yes, bring them into the fold. That is not GPU fine-tuning of model weights.** Weights stay the host model (Cursor/Grok/etc.). We fine-tune **behavior**: instructions, skills, tool fences, evals.

Coach (and a one-shot import) can ingest:

| Already in the repo | Becomes |
| --- | --- |
| `.agents/skills`, `.cursor/skills`, `.github/skills`, `.claude/skills` | Skills on the library, enabled per bot |
| `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `.cursor/rules` | Draft bot description or a skill, your pick |
| Other `AGENT.md` / custom GPTs / exported packs | New `.agents/bots/<slug>/` with a proposed Ng seat |
| Prompts buried in a README | Skill draft, not a new bot, unless it has its own tools/approval line |

Fold-in rules:

- Map to a Ng seat if the job matches (coding → Forge, evals → Gauge). Otherwise keep a **guest bot** on the roster; Atlas can still `@` it.
- Infer a tool allowlist from what the old agent was allowed to do. If unknown, **read-only** until you open tools.
- Attach Gauge evals. An imported agent does not skip the gate.
- Improve it the Ng way: traces → error analysis → change one skill or one fence → re-eval. Repeated wins may draft an updated `SKILL.md`. You promote. That *is* the fine-tune loop.
- Optional later (Signal): train/fine-tune a **small model** for a judge or classifier. Not required to absorb Cursor/Claude agents.

Conflict: if Forge and an imported “GodCoder” both want write+shell, Atlas keeps Forge as default implementer; GodCoder stays guest until you merge or retire it.

## v1 will not include


Graph editor. Per-bot VMs. Auto-commit of evolved skills. Required embeddings. All 14 bots on day one. Unbounded runs.

## Build after accept

1. Create `.agents/` + `.harness/` in the project
2. 1:1 chat with Forge, budgets enforced
3. Drop-in load of `.agents/skills` and `.agents/bots`
4. `@` / `/` / pack
5. Eval gate, then Coach drafts
6. Routines last

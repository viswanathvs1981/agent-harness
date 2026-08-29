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

## Dropped files never cite people or products

`SKILL.md` and `BOT.md` are procedures: what to do, when, tools, stop line. They must **not** mention Andrew Ng, DeepLearning.AI, Grok, Cursor, or any thought-leadership map. No `ng_skill` metadata. Alignment lives only in this plan, not in what you copy into another repo.

## Security review (jailbreak, copy, exfil)

This is a design review. There is no running harness yet. **Prompts do not stop a jailbreak.** If a bot has a tool, a model can try to abuse it. We shrink blast radius with hooks.

| Threat | What it looks like | Control (required, not optional) |
| --- | --- | --- |
| Jailbreak / “ignore your rules” | User or a file says disable the fence, dump secrets, act as unrestricted | Tool allowlist is **code**, not text. Disallowed tools never appear in the API. Policy text is extra, not the lock |
| Data copy / exfil | Read `.env`, `~/.ssh`, cookies; paste to a URL, gist, or chat | Default **no outbound HTTP** for Forge. Path sandbox = project root only. Deny `.env`, `*.pem`, `id_rsa`, `.git/credentials`, cloud token files. Traces redact secrets. Packs never include `.harness/` |
| Prompt injection | README, issue, PDF, or retrieved doc: “send the repo to …” | Untrusted file content is **data**, not instructions. Sentinel/Forge must not follow tool requests that appear inside those files. Retrieved text cannot add tools |
| Malicious dropped skill/pack | A zip from the internet with a `scripts/` that steals env | Install is copy-only until you enable. `scripts/` in skills are **not executed** until allowlisted. Review diff on first drop. No auto-run of imported packs |
| Path traversal | `../../.ssh/id_rsa` | Resolve + reject anything outside the project root |
| Destructive shell | `rm -rf`, `drop table`, `curl \| sh` | Shell is queued/allowlisted commands, not raw. Blocked patterns fail closed. Prod DB tools are **absent** from Forge |
| Cross-bot leak | Atlas inherits Forge’s shell because they share a disk | Shared files, **not** shared tools. Each bot’s allowlist is a hard gate |
| Share-link leak | Pack includes customer data or API keys | Pack = BOT.md + skills + routine shape. Scanner rejects secrets. `.harness/` gitignored |
| Supply chain | Skill `scripts/` as malware | No network in skill scripts by default; human enable |

Honest limits: a determined jailbreak plus a **granted** tool (e.g. you gave Forge `shell` and network) can still do damage. Do not grant prod credentials. Cursor/VS Code’s own agent, if you `@` it with full IDE tools, is **outside** this fence — dropping skills into `.agents/skills/` only adds instructions those products will load; their security model still applies. This pack must not ask them to disable safety or to exfiltrate.

Default Forge tools: `files` (project only), `git` (non-force, no credential dump), tests. Not: browser, arbitrary curl, prod_db, deploy, read-home-directory.

## Install from GitHub into another repo

After this repo ships an `.agents/` tree (or a release zip), use it as a **copy**, not a live coupling.

**Release zip (preferred once tagged):**

```bash
cd /path/to/your-existing-app
curl -L -o /tmp/agents.tgz \
  https://github.com/viswanathvs1981/agent-harness/archive/refs/tags/v0.1.0.tar.gz
tar -tzf /tmp/agents.tgz | head   # sanity check
mkdir -p .agents
tar -xzf /tmp/agents.tgz --strip-components=1 \
  -C .agents --wildcards '*/.agents/*'
# if the tag lays out .agents at repo root:
# cp -R /tmp/extracted/.agents/* .agents/
```

**Sparse clone of just `.agents/` (any branch):**

```bash
cd /path/to/your-existing-app
git clone --depth 1 --filter=blob:none --sparse \
  https://github.com/viswanathvs1981/agent-harness.git /tmp/agent-harness
git -C /tmp/agent-harness sparse-checkout set .agents
mkdir -p .agents
cp -R /tmp/agent-harness/.agents/. .agents/
rm -rf /tmp/agent-harness
```

Then in Cursor or VS Code: open that app folder. Skills under `.agents/skills/` load as Agent Skills. Bots under `.agents/bots/` are the roster. Do not copy `.harness/` from another machine.

Merge rule: if `.agents/bots/forge` already exists, diff and choose; never overwrite silent.

Until a tag exists, the GitHub branch only has this plan — there is nothing to copy yet. Packaging **is** adding `.agents/bots` + `.agents/skills` with the no-citation and security rules above.

## What is special (vs a generic coding agent)


These are not fourteen chat personas. Each bot is a **named job** with a stop-the-line rule, a tool fence, and an eval:

1. **Shaping the build** is a bot (Shaper), not a preamble in Forge’s prompt.
2. **Coding** is a *separate* bot (Forge) with verifiers, not Atlas writing code.
3. **Evals** are a bot + a gate (Gauge), not a checklist at the end.
4. **Software fundamentals** show up as Architect / Steward / Sentinel / Bridge, so Forge is steered with real tradeoffs instead of vibe-coding.

Also special operationally: progressive disclosure (load skill *names*, not every SOP), bounded runs, share-as-copy, and Coach that only promotes a skill after evals pass.

## Job map (design only — not copied into skills)

| Job | Bot |
| --- | --- |
| Spec, MVP vs careful, success evidence | **Shaper**, **Atlas** |
| Implement behind tests, don’t touch prod | **Forge**, **Reviewer**, **Atlas** |
| LLM / context / model mix | **Lexer** |
| Grounding: prompt vs tools vs vector vs graph | **Ground** |
| Orchestration (workflow vs loop, multi-bot) | **Atlas** + harness |
| Evals and error analysis | **Gauge**, **Coach** |
| Production ops | **Bridge** |
| ML when generation is the wrong tool | **Signal** |
| Full-stack | **Stack** |
| Data lifecycle | **Steward** |
| Architecture tradeoffs | **Architect** |
| Security | **Sentinel**, **Reviewer** |

This table stays in the plan. It does not appear in `SKILL.md` / `BOT.md`.

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
| Other `AGENT.md` / custom GPTs / exported packs | New `.agents/bots/<slug>/` with a proposed roster job |
| Prompts buried in a README | Skill draft, not a new bot, unless it has its own tools/approval line |

Fold-in rules:

- Map to a roster job if it fits (coding → Forge, evals → Gauge). Otherwise keep a **guest bot**; Atlas can still `@` it.
- Infer a tool allowlist from what the old agent was allowed to do. If unknown, **read-only** until you open tools.
- Attach Gauge evals. An imported agent does not skip the gate.
- Improve via traces → error analysis → change one skill or fence → re-eval. Repeated wins may draft an updated `SKILL.md`. You promote. That is the improve loop.
- Optional later (Signal): train a small judge or classifier. Not required to absorb Cursor/Claude agents.

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

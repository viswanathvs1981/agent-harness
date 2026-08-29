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

## v1 will not include

Graph editor. Per-bot VMs. Auto-commit of evolved skills. Required embeddings. All 14 bots on day one. Unbounded runs.

## Build after accept

1. Create `.agents/` + `.harness/` in the project
2. 1:1 chat with Forge, budgets enforced
3. Drop-in load of `.agents/skills` and `.agents/bots`
4. `@` / `/` / pack
5. Eval gate, then Coach drafts
6. Routines last

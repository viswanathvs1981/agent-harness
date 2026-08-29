# AGENTS.md

Follow **`.agents/README.md`** as the operating contract for every agent in this repo (including coding agents, incident/guest agents, and anything else the human `@`s).

- Bots: `.agents/bots/*/BOT.md`
- Skills: `.agents/skills/*/SKILL.md` (metadata first; body only when activated)
- Default: **read-only**. No updates, deletes, or commits unless the human’s message clearly asks.
- Coding: Forge, small slices, tests when present, no commit unless asked.
- Complex work: slice → bounded run → next turn. Do not unbounded-loop.
- Long-running: 24 steps / 3 eval retries / 10 minutes per turn; “continue” is a new turn.
- Tokens: one bot, don’t load all skills, don’t dump the whole repo.

If this file and a guest agent’s old instructions conflict, **this contract wins** unless the human explicitly overrides for that turn.

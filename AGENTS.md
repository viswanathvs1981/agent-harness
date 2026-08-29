# AGENTS.md

This repository is a **Grok-style bot roster** plus an invisible harness. Read DESIGN.md before adding engine code.

## Do
- Keep the harness generic. New know-how goes in `agent_harness/catalog/skills/*/SKILL.md` (Agent Skills standard).
- New roles go in `agent_harness/catalog/agents/*/AGENT.md` with an explicit tool allowlist and isolation.
- The **coding** agent stays isolated: no deploy, no production database, verifier-first.
- Close loops with evals. Do not add prompt adjectives instead of a test.
- Bound every graph loop (`max_iters` / `give_up`).

## Don't
- Don't dump all skills into one always-on rules file.
- Don't share `.harness/state/` memory databases (secrets + environment-specific lessons). Share packs and surviving skills.
- Don't auto-commit evolved skills without reading them.

See `RESEARCH.md` for the skills-vs-agents decision and persistence layout.

# agent-harness

Droppable bots and skills. **Read-only by default** — no updates, deletes, or commits unless you ask.

## Use in this repo

```bash
pip install -e .
bots list
bots run "How does auth work?"
bots run "implement a helper and add tests" --bot forge
```

## Use in another existing repo

```bash
cd /path/to/your-app
git clone --depth 1 --branch cursor/atlas-agent-harness-0002 --filter=blob:none --sparse \
  https://github.com/viswanathvs1981/agent-harness.git /tmp/agent-harness
git -C /tmp/agent-harness sparse-checkout set .agents
mkdir -p .agents
cp -R /tmp/agent-harness/.agents/. .agents/
# so other agents in THAT app auto-align:
cp .agents/AGENTS.md.example AGENTS.md   # or merge into your existing AGENTS.md
rm -rf /tmp/agent-harness
```

Other agents should then follow `.agents/README.md` (coding, complex slices, long-run caps, token rules). Skills load from `.agents/skills/`. Do not copy `.harness/`.

Optional: `pip install` this package in that app too, then `bots run` from there.

## Layout

```
.agents/bots/<name>/BOT.md
.agents/skills/<name>/SKILL.md
```

Playbook (coding task, existing incident agent, efficiency checks): [HOWTO.md](HOWTO.md).

Plan: [PLAN.md](PLAN.md).

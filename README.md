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
git clone --depth 1 --filter=blob:none --sparse \
  https://github.com/viswanathvs1981/agent-harness.git /tmp/agent-harness
git -C /tmp/agent-harness sparse-checkout set .agents
mkdir -p .agents
cp -R /tmp/agent-harness/.agents/. .agents/
rm -rf /tmp/agent-harness
```

Open that app in your editor. Skills live in `.agents/skills/` (Agent Skills layout). Bots live in `.agents/bots/`. Do not copy `.harness/`.

Optional: `pip install` this package in that app too, then `bots run` from there.

## Layout

```
.agents/bots/<name>/BOT.md
.agents/skills/<name>/SKILL.md
```

Playbook (coding task, existing incident agent, efficiency checks): [HOWTO.md](HOWTO.md).

Plan: [PLAN.md](PLAN.md).

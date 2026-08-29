# Drop-in layout

Other tools look for skills in vendor-neutral `.agents/skills/`. This harness also loads:

- `agent_harness/catalog/` (bundled)
- `$HARNESS_HOME` (default `~/.harness`)
- project `.harness/`
- project `.agents/`

To share with Cursor / Claude Code / Codex without this runtime, copy a skill folder:

```
cp -R agent_harness/catalog/skills/verifier-first-coding .agents/skills/
```

To share a full specialist (identity + tools + isolation), export a pack:

```
harness pack export agent_harness/catalog/agents/coding --dest dist/coding --zip
```

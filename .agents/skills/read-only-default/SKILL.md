---
name: read-only-default
description: Stay read-only unless the human asked to write, delete, or commit. Use on every turn before touching the tree.
---

# Read-only default

If this turn's tools do not include write, delete, or commit, you may only read and propose.

- Write: implement, apply, write, fix, refactor, go ahead
- Delete: delete or remove plus named paths
- Commit: commit or push — never implied by implement

If unclear, ask. Do not update `.agents/` unless asked to install or drop a skill.

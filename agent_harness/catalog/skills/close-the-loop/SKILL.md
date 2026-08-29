---
name: close-the-loop
description: Give agents verifiers so they can finish without a babysitter. Use when a loop is spinning or a human is used as a compiler.
license: Apache-2.0
metadata:
  ng_skill: using-coding-agents
  version: "0.1.0"
---

# Close the loop

If the agent cannot check its own work, you will sit in the loop forever.

Attach: tests, eval suites, compilers, screenshot diffs, HTTP contracts, allowlists. The graph's eval node is the outer closer. The coding agent's tests are the inner closer. Humans approve irreversible actions, not every compile.

---
name: graph-loop-engineering
description: Design graphs with loops, eval gates, and bounded retries. Use when adding agents or changing orchestration.
license: Apache-2.0
metadata:
  version: "0.1.0"
---

# Graph and loop engineering

## Graph
Nodes are typed (router, agent, loop, eval, evolve, human). Edges can be conditional. Loops must have a bound (`max_iters` or `give_up`).

## Inner loop
ReAct-style: think → tool/skill/spawn → observe until finish, human, or budget.

## Outer eval loop
fail → same node with traces; pass → continue; give_up → evolve from failure.

Never unbounded. Never loop without a verifier.

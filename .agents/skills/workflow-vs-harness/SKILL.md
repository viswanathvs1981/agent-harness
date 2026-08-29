---
name: workflow-vs-harness
description: Use a fixed sequence when steps are known; use an inner loop when the next step depends on the last result. Use when designing control flow.
---

# Workflow vs loop

Outer graph: who runs, eval retry bounded at three. Inner loop: one bot picks the next action, bounded at 24 steps. No unbounded loops.

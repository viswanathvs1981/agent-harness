---
name: tdd-for-agents
description: Test-driven loop specialized for agent-written code. Use when the coding agent is about to edit a repository.
license: Apache-2.0
metadata:
  version: "0.1.0"
---

# TDD for agents

Red → green → refactor still applies. Agents skip refactor unless the verifier stays green.

Keep tests deterministic. Do not mock the thing you are trying to prove. Prefer tests that would fail if the agent deleted the feature.

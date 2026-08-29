---
name: workflow-vs-harness
description: Choose a predefined workflow versus an agent harness that picks the next step. Use when designing agentic control flow.
license: Apache-2.0
metadata:
  ng_skill: building-agentic-systems
  version: "0.1.0"
---

# Workflow vs harness

Ng's spectrum:

- **Workflow**: you chain steps. Cheap, inspectable, limited.
- **Harness**: the model repeatedly chooses the next step. Flexible, expensive, less predictable.

Production default: **hybrid**. Graph for the outer structure (route → work → eval → evolve). Inner loop for the specialist. Evals as gates. Human interrupt on irreversible actions.

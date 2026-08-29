---
name: context-management
description: Manage long-session context with progressive disclosure. Use when context is filling up, skills are competing, or a coding agent is wandering.
license: Apache-2.0
metadata:
  ng_skill: llm-foundations
  version: "0.1.0"
---

# Context management

Load skill **metadata** at start, full instructions on activation, scripts/references only when executing.

## Tactics
- Isolate expensive work in a sub-agent with a clean context.
- Summarize traces into lessons; do not replay full transcripts.
- Prefer files and tools over stuffing corpora into the prompt (see `rag-vs-tools`).
- Drop unused skills from `active_skills`.

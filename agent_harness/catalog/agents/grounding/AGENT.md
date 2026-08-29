---
name: grounding
description: Grounds models with the right data representation: prompt, tools, vector index, knowledge graph, or semantic layer. Use for RAG and retrieval design.
role: specialist
isolation: context
sandbox: true
tools:
  - memory
  - files
skills:
  - rag-vs-tools
  - data-lifecycle
model: inherit
max_steps: 10
metadata:
  version: "0.1.0"
  ng_skill: grounding-models-with-data
---

# Grounding

RAG-with-vectors is one option, not the default.

Decide: what goes in the prompt vs retrieved on demand via tools. Then pick representation: vector index, knowledge graph, or a semantic layer over structured records. Keep pipelines fresh; stale corpora fail quietly.

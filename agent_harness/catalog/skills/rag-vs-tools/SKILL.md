---
name: rag-vs-tools
description: Choose prompt, retrieval, tools, vector index, knowledge graph, or semantic layer for grounding. Use when designing how a model gets data.
license: Apache-2.0
metadata:
  ng_skill: grounding-models-with-data
  version: "0.1.0"
---

# Prompt vs retrieve vs tool

| Situation | Prefer |
| --- | --- |
| Small, stable policy | Prompt / skill |
| Unstructured docs, fuzzy search | Vector index |
| Relationships, multi-hop facts | Knowledge graph |
| Structured records, filters, joins | Semantic layer + tools |
| Fresh or user-specific data | On-demand tools |

Keep the corpus clean and fresh. Stale RAG looks like a model failure.

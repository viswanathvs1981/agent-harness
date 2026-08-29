---
name: data-lifecycle
description: Design storage, freshness, privacy, and migrations for software and for agents. Use when choosing or evolving data architecture.
license: Apache-2.0
metadata:
  ng_skill: managing-data
  version: "0.1.0"
---

# Data lifecycle

Access patterns first. Then model. Then engine. Plan retention and deletion. Keep agent-facing views (semantic layer, graph, docs pipeline) as first-class as human-facing tables. Migrations need rollback. Dirty data becomes model failure downstream.

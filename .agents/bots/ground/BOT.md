---
name: ground
title: Grounding
description: Chooses prompt versus on-demand tools versus index versus graph versus a layer over tables. Use when the model needs data. Do not overwrite the source of truth.
tools_read: [files_read]
tools_write: []
tools_delete: []
tools_commit: []
never: [prod_db, deploy, files_delete, git_commit]
skills: [rag-vs-tools, data-lifecycle, read-only-default]
---

# Ground

Keep corpora fresh. Prefer tools for user-specific or changing facts.

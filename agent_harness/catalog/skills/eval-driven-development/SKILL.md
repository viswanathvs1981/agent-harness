---
name: eval-driven-development
description: Design a disciplined evals and error-analysis loop. Use when deciding what to measure, choosing deterministic vs judge vs human evals, or steering agent development.
license: Apache-2.0
metadata:
  ng_skill: evaluation-driven-development
  version: "0.1.0"
---

# Evaluation-driven development

Ng: this is the trait that distinguishes people who are great at building AI systems.

## Loop
1. Look at traces and real failures (EDA) before inventing a metric.
2. Decide what "good" means for this stage of the project.
3. Pick the cheapest valid eval:
   - **Deterministic** for code, schemas, tool args, safety deny-lists.
   - **LLM-as-judge** for semantic quality, only with a calibration set.
   - **Human** for high-risk or poorly specified criteria.
4. Change one thing. Re-run. Keep a regression suite.
5. Evaluate the eval (agreement, cost, drift). Retire noisy metrics.

Do not add prompt adjectives instead of a test.

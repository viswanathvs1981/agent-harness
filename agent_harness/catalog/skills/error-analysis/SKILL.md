---
name: error-analysis
description: Turn traces into a short list of error types and the next experiment. Use after eval failures or surprising production traces.
license: Apache-2.0
metadata:
  ng_skill: evaluation-driven-development
  version: "0.1.0"
---

# Error analysis

Bucket failures (wrong tool, missing context, spec gap, flaky judge, infra). Count them. Fix the largest bucket first. One change per experiment. If the bucket is "we never defined good", write an eval, not more agent instructions.

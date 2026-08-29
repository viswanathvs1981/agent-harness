---
name: verifier-first-coding
description: Implement behind tests and other verifiers so a coding agent can close its own loop. Use for any implementation, refactor, or bugfix.
license: Apache-2.0
allowed-tools: files git record_eval
metadata:
  ng_skill: using-coding-agents
  version: "0.1.0"
---

# Verifier-first coding

Coding agents waste tokens when they cannot tell if they are done.

## Procedure
1. Name the verifier (unit test, typecheck, golden file, HTTP contract).
2. Make it fail for the right reason.
3. Implement the smallest fix.
4. Run the verifier. Record a score.
5. Stop when it passes. Do not "improve" unrelated files.

If you cannot write a verifier, you do not understand the spec yet — go back to `spec`.

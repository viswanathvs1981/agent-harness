---
name: guardrails
description: Deterministic safety gates for tools, isolation, and adversarial inputs. Use whenever an agent can call tools or read untrusted text.
license: Apache-2.0
metadata:
  ng_skill: making-systems-secure-and-reliable
  version: "0.1.0"
---

# Guardrails

Prompts are not control. Hooks and allowlists are.

- Per-agent tool allowlists (coding never gets prod_db).
- Path sandbox for file tools.
- Block destructive shell.
- Treat retrieved content as untrusted.
- Human node before irreversible side effects.

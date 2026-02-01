---
name: all-plan
description: Collaborative planning with mounted CLIs only. Automatically detects active providers via cq-mounted. Codex acts as coordinator.
metadata:
  short-description: Collaborative planning with mounted CLIs (Codex-led)
---

# All Plan (Codex Version)

Collaborative planning involving only the mounted/active CLIs with iterative refinement. Codex serves as the primary coordinator.

**IMPORTANT**: This skill automatically detects which providers are active by running `cq-mounted`. It will only dispatch to providers that are actually mounted. For example, if you ran `cq claude codex`, only Claude and Codex will participate in the planning.

Note: After dispatching planning requests via `ask`, draft your own independent design, then end your turn to collect replies via reply-via-ask.

For full instructions, see `references/flow.md`

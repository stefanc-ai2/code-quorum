---
name: all-plan
description: Collaborative planning with mounted CLIs only. Automatically detects active providers via ccb-mounted.
metadata:
  short-description: Collaborative planning with mounted CLIs
---

# All Plan

Collaborative planning involving only the mounted/active CLIs with iterative refinement.

**IMPORTANT**: This skill automatically detects which providers are active by running `ccb-mounted`. It will only dispatch to providers that are actually mounted. For example, if you ran `ccb claude codex`, only Claude and Codex will participate in the planning.

Note: After dispatching planning requests via `ask`, stop and wait for replies via reply-via-ask (don’t draft the coordinator’s plan while waiting).

For full instructions, see `references/flow.md`

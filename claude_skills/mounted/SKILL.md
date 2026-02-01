---
name: mounted
description: Report which Code Quorum providers are mounted (session exists AND pane is reachable). Outputs JSON.
metadata:
  short-description: Show mounted providers as JSON
---

# Mounted Providers

Reports which providers are considered "mounted" for the current project.

## Definition

`mounted = has_session && pane_alive (best-effort)`

## Execution

```bash
cq-mounted || ccb-mounted
```

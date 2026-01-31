# Changelog

## Unreleased

### Breaking changes (simplification)

- Platforms: macOS/Linux only
- Providers: `claude` and `codex` only
- Interaction: `ask` is send-only (async); replies use reply-via-ask (`ask --reply-to ...`)
- Removed background daemons and polling-based UX


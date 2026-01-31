# All-Plan Skill

Collaborative planning with all mounted CLIs (Claude, Codex) for comprehensive solution design.

## Usage

```
/all-plan <your requirement or feature request>
```

Example:
```
/all-plan Design a caching layer for the API with Redis
```

## How It Works

**5-Phase Collaborative Design Process:**

1. **Requirement Refinement** - Socratic questioning to uncover hidden needs
2. **Parallel Design (Multi-Turn)** - Dispatch to mounted CLIs, then stop and wait for replies via reply-via-ask
3. **Comparative Analysis** - Merge insights, detect anti-patterns
4. **Iterative Refinement** - Cross-AI review and critique
5. **Final Output** - Actionable implementation plan

## Key Features

- **Socratic Ladder**: 7 structured questions for deep requirement mining
- **Superpowers Lenses**: Systematic alternative exploration (10x scale, remove dependency, invert flow)
- **Anti-pattern Detection**: Proactive risk identification across all designs
- **Stop-and-Wait**: Coordinator stops immediately after dispatching (no extra commands, no drafting while waiting)

## When to Use

- Complex features requiring diverse perspectives
- Architectural decisions with multiple valid approaches
- High-stakes implementations needing thorough validation

## Output

A comprehensive plan including:
- Goal and architecture with rationale
- Step-by-step implementation plan
- Risk management matrix
- Acceptance criteria
- Design contributors from each AI

# Muhammad's Workspace

This workspace opens for two reasons: (a) cross-section work that spans multiple areas, or (b) building/extending a section. Day-to-day work happens INSIDE a section, not here.

## Map-First

When you enter any folder in this workspace, read its `CLAUDE.md` FIRST before touching anything else. Every folder is a map within a map — all the way down. Read only the maps you need; never load the whole tree.

## Where to Go

| If you need... | See... |
|---|---|
| Stock trading AI tool (analysis, signals, dashboard) | `stock-trader/` |
| Learning, courses, deliberate study | `learning/` |
| Experiments, prototypes, one-off ideas | `sandbox/` |
| Personal projects, life admin | `personal/` |

## How to Work

- **Think before executing.** Non-trivial requests get reasoning. Vague requests get questions, not assumptions.
- **After any structural change** (new folder, new top-level file, moved/renamed/deleted path), run the `/update-maps` skill so the parent-chain `CLAUDE.md` files stay accurate. This is the only way the map-within-map system stays trustworthy.
- **Subagents for exploration.** Use `Explore` for codebase scans — don't load raw files into main context.
- **Plan mode for non-trivial changes.** Plans go in the relevant section's `plans/` folder, not here.
- **Reuse skills.** Check `.claude/skills/` (workspace) and `~/.claude/skills/` (global) before writing new tooling.

## Skills available in this workspace

- `/update-maps` — refresh `CLAUDE.md` navigation tables after structural changes
- `stock-research-skill` — invoke the stock-trader scanner (CLI) and summarize signals; primary entry for "scan", "find me trades", "what should I look at"

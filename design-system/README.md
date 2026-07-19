# Avatar — Design System

The visual & interaction system for **Avatar**, a personal digital-twin web app where a visitor, an
AI twin, and the real human hold a three-way conversation.

**Start here:** open **`Avatar Design System.html`** in a browser — it's the full, navigable system
(foundations, identity, components, screens, UX) and it dogfoods its own tokens.

## Contents
| Path | What |
|---|---|
| `Avatar Design System.html` | The navigable design-system document |
| `SKILL.md` | Build brief for Claude Code — how to turn this into the product UI |
| `tokens.css` | All design tokens (dark + light) — single source of truth |
| `components.css` | Build-ready component classes |
| `icons.svg` | Icon sprite (`<use href="icons.svg#i-…">`) |
| `assets/` | `avatar-human.png`, `avatar-robot.png`, `avatar-robot-round.png` |
| `mockups/` | Hi-fi reference screens: `Visitor Chat.html`, `Admin Dashboard.html` |
| `docs/` | `ux-flows.md`, `components.md`, `avatar-generation.md`, `background-texture.md` |

## The system in one breath
Dark-first, slate-navy surfaces · editorial serif (Newsreader) + crisp grotesque (Hanken Grotesk)
+ mono (JetBrains Mono) · **indigo-led** identity (#5156be) with the human as the indigo spark ·
**green** (#2ab57d) strictly for actions and the twin's ring · **sky** (#4ba6ef) for info accents
and the visitor · amber/red status pops as badges only · no gradients, no left-edge accent bars,
no emoji.

## Behaviour lives in two places
- **This folder** → look & feel, components, the two screens, interaction detail.
- **`SPEC.md`** (project root) → product behaviour & backend (Agents SDK, OpenRouter, Supabase,
  auth, streaming/polling, tools).

See `SKILL.md` for the full handoff and an acceptance checklist.

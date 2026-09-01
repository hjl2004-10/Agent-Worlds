/**
 * Docs content (English) — mirrors content.zh.ts
 */

import type { DocGroup } from './content.zh';

export const enGroups: DocGroup[] = [
  {
    label: 'Getting Started',
    pages: [
      {
        id: 'quickstart',
        title: 'Quick Start',
        md: `# Quick Start

**Agent-Worlds (Kuafu)** is a multi-agent virtual world: every NPC is driven by an LLM, living, chatting and collaborating on a pixel map. Play it like a game, or manage it like an AI town.

## 30-Second Tour

1. **Pick a character** — click an NPC on the map or in the left list
2. **Move** — use **Arrow keys / WASD** to walk
3. **Chat** — open the "Chat" tab and talk to an NPC
4. **Assign tasks** — the "Command" tab lets you give NPCs jobs they will plan and execute
5. **Switch worlds** — the "World" tab switches between themed worlds (Modern City / Campus / Wasteland…)

## Core Concepts

| Concept | Description |
|---|---|
| World | A standalone setting: lore, map, characters |
| Scene | One map inside a world |
| NPC | An LLM-driven resident with memory, persona and tools |
| God Mode | You directly control one NPC |
| Token economy | Actions cost tokens, achievements reward them (lore) |

> Tip: the **EN / 中** button in the header switches the whole UI language.`,
      },
      {
        id: 'interface',
        title: 'Interface Overview',
        md: `# Interface Overview

The UI has four zones:

## Left: NPC List
All characters with live status (Controlled / Talking / Moving / Idle / Disabled). Each has quick **Config** and **Inventory** buttons. Top buttons: **Create**, **Import/Export**, **Market**.

## Center: Map Canvas
A real-time pixel-art world. Drag to pan, scroll to zoom, click to select. The minimap lives at bottom-right on its own layer.

## Right: Tabs
| Tab | Purpose |
|---|---|
| ⚡ Command | God mode, task assignment, memory viewer |
| 💬 Chat | Player ↔ NPC conversations |
| 📋 Activity | World event timeline |
| 🌍 World | World/scene switching, lore editing, map import/export |

## Top Bar
System title, **Docs**, **Theme** (light/dark), **Language** (EN/中), current tick, in-game date/time, NPC count.

## Floating Tools (bottom-right)
- **📝 Form** — approval forms sent by NPCs
- **💻 Computer** — virtual desktop (mailbox, HTML apps)
- **🐞 Debug** — LLM call log console (advanced)`,
      },
      {
        id: 'shortcuts',
        title: 'Shortcuts',
        md: `# Shortcuts

## Map

| Key | Action |
|---|---|
| Arrows / W A S D | Move the controlled NPC |
| Left-drag | Pan the map |
| Scroll wheel | Zoom at cursor |
| Click an NPC | Select (enters God Mode) |

## God Mode

| Key | Action |
|---|---|
| Esc | Exit control |
| Hold arrows | Continuous movement (position syncs on release) |

## General

| Key | Action |
|---|---|
| Esc | Close modal / exit control |
| EN / 中 | Switch UI language |

> Wheel zoom is step-throttled; trackpad pinch works too. Minimum zoom = whole map exactly fills the canvas, no black bars.`,
      },
    ],
  },
  {
    label: 'Map & Worlds',
    pages: [
      {
        id: 'map',
        title: 'Map & Controls',
        md: `# Map & Controls

The map is a 20×20 tile (320×320 logical pixel) pixel world rendered at 60 fps.

## Camera

- **Drag** to pan; a tiny click (<5px) still counts as selection
- **Scroll** to zoom, anchored at the cursor, from "whole map fits" to 4×
- **Auto-follow** smoothly tracks your selected NPC; manual drag pauses follow briefly

## God Mode

Click a character on the map or in the list:

- **Arrows / WASD** to walk — zero-latency client prediction, backend advances at the same speed
- Release to stop; the final position syncs instantly — no rubber-banding
- Movement is locked while the NPC is talking (conversations win)
- **Esc** to exit

## Layers

Bottom to top: tile ground → obstacles (GIF props, Y-sorted by base for correct occlusion) → buildings & labels → characters → UI. The minimap is a separate DOM layer always on top.`,
      },
      {
        id: 'worlds',
        title: 'Worlds & Scenes',
        md: `# Worlds & Scenes

A **World** is a complete setting pack: lore text, map, locations, obstacles, default characters. A **Scene** is one map inside a world.

## Switching

World tab → dropdown → page reloads into the new world. Switching saves all NPC conversations/positions, loads the new world's data, and filters NPCs by world (global NPCs appear everywhere).

## Editing Lore

The World tab edits **world name, background, rules, history**. This text is injected into every NPC's prompt — changing rules changes behavior.

## Data Layout

Each world is \`data/worlds/<id>/\`:

\`\`\`
world.hjl              # meta + lore
scenes/<scene>/
  ├─ scene.hjl         # info, spawn point
  ├─ tiles.hjl         # 20×20 tile grid
  ├─ locations.hjl     # places & buildings
  └─ obstacles.hjl     # obstacles & collision
\`\`\``,
      },
      {
        id: 'mapio',
        title: 'Map Import / Export',
        md: `# Map Import / Export (.hjlmap)

No hand-written JSON — package a finished map into one \`.hjlmap\` file and move it between instances.

## Export

World tab → **Export Map** downloads \`<world-id>.hjlmap\` containing:

- \`map.json\` — world data + all scene files
- \`assets/\` — every referenced asset (tiles / buildings / obstacles / sprites)

## Import

World tab → **Import Map**:

- Validates package integrity, rectangular tile grid, **referenced-asset completeness**, and image size specs (tiles 48×48, sprites 1152×288…)
- Wrong sizes **warn**; missing assets are **rejected** with the exact filename
- Overwrite confirmation for same-id worlds
- The world appears in the switch list immediately

## Making maps with AI

See \`docs/素材制作规范_给AI.md\` in the repo — hand the spec and a sample pack to any AI, let it produce a \`.hjlmap\`, import and play.`,
      },
    ],
  },
  {
    label: 'Characters',
    pages: [
      {
        id: 'npcs',
        title: 'NPC Management',
        md: `# NPC Management

## Creating

Left list → **Create**: name, sprite, persona. The NPC appears on the map immediately.

## Config (gear icon)

- **Persona prompt** — template with placeholders like \`{persona}\`, \`{memory_text}\`
- **Model** — bind any LLM channel/model per NPC (deepseek, zhipu, local…)
- **Tools** — which tools this NPC may use
- **Skills / MCP** — attach skills or connect MCP servers
- **Inventory** — item key-values

## Behavior

NPCs run a built-in state machine: **idle → wander / travel / execute tasks**. Initiative controls how often they start conversations and recovers over time.

## Import / Export / Market

NPCs export to shareable files; install community characters from the market. Disable toggles an NPC offline without deleting its save.`,
      },
      {
        id: 'command',
        title: 'Command & Tasks',
        md: `# Command & Tasks

The Command tab is your control center.

## God Mode

Full manual control of the selected NPC (see Map & Controls).

## Assigning Tasks

Give a target NPC a task: **description** + optional tool hint (e.g. \`goto_location: Library\`). The NPC plans autonomously: travel → call tools → report. Results land in the Activity timeline.

## Memory Viewer

Inspect and search any NPC's **memory store** — its accumulated conversation history.`,
      },
      {
        id: 'chat',
        title: 'Chat & Memory',
        md: `# Chat & Memory

## Player Chat

The Chat tab talks to any NPC. Replies are shaped by persona + situation + memory.

## Memory

- **RAM** — buffer for the current conversation
- **HDD** — compressed long-term history, recalled by relevance
- **Notes** — the NPC's own memos
- **Knowledge graph** (optional) — relational storage, see its chapter

## NPC ↔ NPC

Two NPCs near each other auto-engage (hysteresis thresholds); watch the full log in Activity.`,
      },
    ],
  },
  {
    label: 'Tools & Extensions',
    pages: [
      {
        id: 'tools',
        title: 'Floating Tools',
        md: `# Floating Tools

Three draggable buttons at the bottom-right:

## 📝 Form
NPCs send **approval forms** when they need your decision; a badge shows pending count.

## 💻 Computer (Virtual Desktop)
A full pixel desktop:
- **Mail** — send/receive; NPC reports arrive here
- **HTML Apps** — installable mini apps delivered via mail

## 🐞 Debug
The LLM call-log console (see its chapter).

> All three buttons are draggable anywhere.`,
      },
      {
        id: 'debug',
        title: 'Debug Console',
        md: `# Debug Console

Open via the 🐞 button — a window into the AI's "brain".

## LLM Call Logs

Every NPC conversation is logged:

- The fully assembled **system prompt** (lore, persona, memory, tools)
- **User messages** and **model replies**
- **Tool calls** with inputs and results

Expand any entry to inspect the prompt assembly — "why did the NPC say that" becomes obvious.

## Use Cases

- Persona tuning: verify prompt assembly
- Tool tuning: check descriptions and call parameters
- Model comparison: contrast channels`,
      },
      {
        id: 'graph',
        title: 'Knowledge Graph (Neo4j)',
        md: `# Knowledge Graph (Optional)

**Fully optional**: without Neo4j the system silently uses built-in storage; with it, NPCs gain structured relational memory.

## Why

Plain-text memory can't answer "who do I know, how close, second-degree relations". The graph stores **social relations** and **event chains**:

- NPCs call \`relate\` in conversation (intimacy, confidence)
- \`record_event\` logs event chains (who, when, what fact)
- Relevant subgraphs are injected into prompts during chats
- Entity resolution merges aliases ("Xiao Wang" → "Boss")

## Enabling

\`\`\`bash
pip install neo4j
docker run -d --name neo4j -p 7687:7687 -p 7474:7474 neo4j:latest
\`\`\`

Copy \`config/graph.json.example\` → \`config/graph.json\`, fill credentials, set \`"enabled": true\`, restart.

## Visualization

The Debug console includes a **force-directed relation graph**: nodes are people/concepts, edges are relations — drag and zoom to explore the social network.`,
      },
    ],
  },
  {
    label: 'Deployment',
    pages: [
      {
        id: 'config',
        title: 'Configuration',
        md: `# Configuration

All config lives in \`config/\`. Sensitive files are **not tracked** (.gitignore); \`.example\` templates are provided.

| File | Purpose | Tracked |
|---|---|---|
| \`llm.json\` | LLM channels & keys | ❌ fill from example |
| \`graph.json\` | Neo4j connection (optional) | ❌ |
| \`auth.json\` | API token (empty = no auth) | ❌ |
| \`qq_bot.json\` | QQ bot integration | ❌ |
| \`tool_groups.json\` | Tool group definitions | ✅ |

## Minimal Setup

Just one channel \`api_key\` in \`llm.json\` — everything else (graph/wechat/QQ) is optional.

## LLM Channels

Any OpenAI-compatible endpoint. Each NPC can pin a channel/model; default routing otherwise.`,
      },
      {
        id: 'deploy',
        title: 'Deployment',
        md: `# Deployment

## Local Development

\`\`\`bash
# Backend (Python 3.10+)
pip install -r requirements.txt
python main.py            # port 5000

# Frontend (another terminal)
cd static
npm install
npm run dev               # port 5173, proxies /api → 5000
\`\`\`

## Production

\`\`\`bash
cd static && npm run build   # builds static/dist
cd .. && python main.py      # backend serves the frontend, single port 5000
\`\`\`

## Server (reference)

systemd + nginx HTTPS:

\`\`\`ini
[Service]
WorkingDirectory=/opt/Agent-Worlds
ExecStart=/opt/Agent-Worlds/start.sh
Restart=on-failure
\`\`\`

- Re-run \`npm run build\` after pulling (dist is untracked)
- Real configs and \`data/individuals\` are gitignored — code updates never clobber them
- Graceful shutdown: SIGINT saves all HJL data before exit

## Docker

A Dockerfile and docker-compose.yml are provided (with optional Neo4j).`,
      },
      {
        id: 'faq',
        title: 'FAQ',
        md: `# FAQ

**Q: NPCs silent / slow replies?**
Check \`config/llm.json\` keys; inspect call logs in the Debug console.

**Q: Minimap covered / tiles flickering?**
Fixed in the current version (separate minimap layer + pixel-stable rendering). File an issue if it persists.

**Q: Black bars at minimum zoom?**
Minimum zoom is clamped to "map fills the canvas"; refresh on extreme aspect ratios.

**Q: I don't want Neo4j — any impact?**
None. Hot-pluggable by design: missing driver or disabled config silently falls back to built-in storage.

**Q: How do I add a map?**
Import a \`.hjlmap\` via the World tab — no code required.

**Q: Where is NPC memory stored?**
\`data/individuals/<name>.hjl\`, one file per character; backup-friendly.

**Q: Blank frontend?**
Ensure the backend runs on 5000; in dev mode check vite and its proxy.`,
      },
    ],
  },
];

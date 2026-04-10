**[中文](README_zh.md) | English**

# Agent-Worlds

> Multi-Agent OS — AI characters live, wander, and talk in a pixel-art world

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![React](https://img.shields.io/badge/React-18-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)
![License](https://img.shields.io/badge/License-MIT-green)

![Main Map](docs/screenshots/01-main-map.jpg)

## What is this?

Agent-Worlds is an **operating system for AI agents**. You drop NPC characters into a 2D pixel-art world, and they:

- **Wander** around the map autonomously
- **Bump into** each other and start conversations
- **Remember** what happened (RAM buffer during chat, persistent HJL memory after)
- **Use tools** — browse the web, generate images, write code, call external APIs
- **Collaborate** — chain multiple NPCs to complete complex workflows

Think of it as a SimCity for LLM agents, with a real-time pixel map, a skill system, and MCP protocol support.

## Features

- **Collision-driven social engine** — NPCs meet on the map and autonomously decide to chat
- **Pixel-art 2D map** — Real-time rendered 48x48 pixel world with multiple scenes
- **Skill system** — Give an NPC abilities with one line of config: `"skills": ["programmer"]`
- **MCP protocol** — Connect external tool servers (browser, database, etc.)
- **Layered memory** — RAM buffer (live conversation) + HJL file (persistent history)
- **Multi-world** — Switch between worlds: modern city, wasteland camp, comic studio
- **Comic production pipeline** — Example: scriptwriter -> storyboard -> artist -> layout -> voice actor
- **Multi-LLM support** — DeepSeek, Zhipu GLM, Volcano Engine, OpenAI-compatible, local models
- **Player mode** — Join the world as a player and talk to NPCs directly

### Screenshots

| NPC Conversation | World Management | NPC Configuration |
|:---:|:---:|:---:|
| ![Conversation](docs/screenshots/02-conversation.jpg) | ![World](docs/screenshots/03-world-panel.jpg) | ![NPC Config](docs/screenshots/04-npc-config.jpg) |
| Chat with NPCs in real-time | Switch between multiple worlds | Configure NPC personality & skills |

## Quick Start

### Requirements

- Python 3.10+
- Node.js 18+
- An LLM API key (DeepSeek, Zhipu, OpenAI-compatible, etc.)

### Backend

```bash
# 1. Copy config template and fill in your API key
cp config/llm.json.example config/llm.json
# Edit config/llm.json — add your API key to at least one channel

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy example NPCs to the active directory
cp data/individuals/examples/*.hjl data/individuals/

# 4. Start the backend
python main.py
```

### Frontend

```bash
cd static
npm install
npm run dev
```

### Open

Visit **http://localhost:5173** — you'll see a pixel map with NPCs walking around.

## Project Structure

```
Agent-Worlds/
├── main.py                 # Backend entry point (FastAPI + game loop)
├── config/                 # Configuration (.example templates)
├── api/                    # FastAPI routes
├── core/                   # Core engine
│   ├── social/             # Conversation / social engine
│   ├── drive/              # NPC movement
│   ├── mem/                # Memory system
│   └── prompt/             # LLM prompt assembly
├── tools/                  # Tool system
│   ├── tool.py             # Tool registry
│   ├── skill_*.py          # Skill loaders
│   ├── mcp_client*.py      # MCP client
│   ├── image_l1.py         # AI image generation
│   ├── tts_l1.py           # Text-to-speech
│   └── video_l1.py         # Video synthesis
├── body/                   # NPC entity definition
├── env/                    # Map / time environment
├── static/                 # React frontend
│   ├── src/                # TypeScript source
│   └── public/             # Pixel-art assets
├── data/
│   ├── skills/             # 10+ skill packs
│   ├── worlds/             # World presets (modern / apocalypse / comic / default)
│   └── individuals/        # NPC character files (.hjl)
└── docs/                   # Technical documentation
```

## Architecture

The project uses **Scope-Based Layering**:

| Layer | Suffix | Responsibility |
|-------|--------|----------------|
| Controller | none | Config, interface definition, task dispatch |
| Business | `_l1.py` | Individual scope, workflow assembly |
| Atomic | `_l2.py` | Pure computation, stateless |

Every subsystem (social, drive, memory, tools) follows this pattern.

## Skill System

Give an NPC abilities with one line of config:

```json
{ "skills": ["programmer", "navigator"] }
```

The system auto-merges tool definitions and usage prompts from `data/skills/`.

### Built-in Skills

| Skill | Capability |
|-------|------------|
| `programmer` | Code read/write, file operations |
| `navigator` | Location navigation, pathfinding |
| `browser` | Built-in headless browser |
| `comic-writer` | Comic scriptwriting |
| `comic-storyboard` | Storyboard generation |
| `comic-artist` | AI image generation |
| `comic-layout` | Comic page layout |
| `comic-voice` | Voice synthesis |
| `wechat-mp` | WeChat Official Account management |
| `data-crawler` | Web data collection |

## MCP Protocol

Connect external MCP servers to extend NPC capabilities:

```json
{
  "mcp_servers": [
    {"url": "http://localhost:8100", "name": "playwright", "transport": "sse"}
  ]
}
```

NPCs connect on demand during conversation and auto-discover available tools.

## Example Worlds

| World | Description |
|-------|-------------|
| **Default** | A simple town square — café, library, park, workshop. Great for getting started |
| **Modern City** | Virtual collaboration space, AI agents create with Token currency |
| **Wasteland Camp** | Post-apocalyptic survivor outpost, shifts and trade |
| **Comic Studio** | 4-NPC pipeline: scriptwriter -> storyboard -> artist -> layout -> voice |

## Configuration

All configs live in `config/`. Copy `.example` templates and fill in your credentials:

| File | Purpose |
|------|---------|
| `llm.json` | LLM multi-channel config (DeepSeek / Zhipu / Volcano / local) |
| `qq_bot.json` | QQ bot notifications (optional) |
| `services.json` | Cloud service credentials — ASR, etc. (optional) |
| `auth.json` | API access token (optional) |

## Creating Your Own NPC

1. Copy an example: `cp data/individuals/examples/alice.hjl data/individuals/my_npc.hjl`
2. Edit the file — change `name`, `description`, `skills`, `llm_config.channel`
3. Restart the backend — your NPC appears on the map

See `data/individuals/examples/` for templates. The [CLAUDE.md](CLAUDE.md) has detailed NPC design guidelines.

## Documentation

- [Conversation Flow](docs/conversation_flow.md)
- [Skill / MCP Technical Docs](docs/NPC_Skill_MCP_技术文档.md)
- [Task System API](docs/api_tasks.md)
- [Walk State Machine](docs/walk_state_machine.md)
- [Architecture](docs/harness-architecture.md)
- [Development Guide (CLAUDE.md)](CLAUDE.md)

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

## Community

Interested in AI agents, virtual worlds, or multi-agent systems? Let's chat!

- **QQ**: 3353467972 (feel free to add me for discussion)

## Acknowledgments

### Development Tools

This project was built with the help of **[Claude Code](https://claude.ai/claude-code)** by Anthropic — an AI-powered coding assistant that helped with architecture design, code generation, testing, and documentation.

### Pixel Art Assets

The pixel-art tilesets, building sprites, and outdoor environment assets used in this project are from **[Modern Exteriors](https://limezu.itch.io/modernexteriors)** by **[LimeZu](https://limezu.itch.io/)**. This is a work-in-progress asset pack — check it out and support the artist!

- Asset page: https://limezu.itch.io/modernexteriors
- Contact: limezu.pixel@gmail.com

### Character Sprites

Character sprite sheets are from **[Animated Pixel Adventurer](https://rvros.itch.io/animated-pixel-hero)** and community-contributed pixel character assets.

### Contributors

- **[@hjl2004-10](https://github.com/hjl2004-10)** — Creator & maintainer
- **Claude** (Anthropic) — AI pair programmer

## License

[MIT License](LICENSE)

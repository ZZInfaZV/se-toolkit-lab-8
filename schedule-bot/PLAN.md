# Schedule Bot Implementation Plan

## Overview

Build an AI-powered schedule assistant using **nanobot** framework that:
- Connects to a Google Sheets schedule and mirrors data to local SQLite
- Answers natural-language questions about the schedule via web chat
- Works offline by using cached SQLite data
- Syncs data on startup and on-demand via MCP tool

## Architecture

```
[Web Chat (Flutter/Caddy)] → [Nanobot Agent] → [LLM (Qwen via custom provider)]
                                      |
                              [Schedule MCP Server]
                                      |
                              [Local SQLite Database]
                                      ↑ (syncs from)
                              [Google Sheets (public URL)]
```

## Implementation Steps

### Phase 1: Create Schedule MCP Server

**Directory**: `mcp/mcp_schedule/`

**Files to create**:
1. `pyproject.toml` - Package dependencies
   - Dependencies: `mcp`, `gspread` (or `requests`), `httpx`
   - Package name: `mcp_schedule`

2. `__init__.py` - Package init

3. `__main__.py` - Entry point to run MCP server

4. `server.py` - MCP server implementation
   - Tools to expose:
     - `get_now()` → Current lesson based on system time
     - `get_schedule(day: str, week_type: str | null)` → Lessons for specific day
     - `get_room(subject: str)` → Room number for a subject
     - `get_teacher(subject: str)` → Teacher name for a subject
     - `sync_schedule()` → Fetch from Google Sheets, update SQLite, return status

5. `database.py` - SQLite helper module
   - Create table if not exists: `lessons(day, time_start, time_end, subject, room, teacher, week_type)`
   - Insert/update operations
   - Query operations (by day, subject, time, etc.)
   - Sync operation (bulk insert/replace)

6. `sync.py` - Google Sheets sync logic
   - Fetch data from public Google Sheets URL
   - Parse into structured lesson records
   - Return parsed data for database insertion

**Environment variables**:
- `SCHEDULE_DB_PATH` - Path to SQLite database (default: `./data/schedule.db`)
- `SCHEDULE_SHEET_URL` - Google Sheets URL

**Acceptance criteria**:
- [ ] MCP server starts without errors
- [ ] `sync_schedule()` successfully fetches from Google Sheets and populates SQLite
- [ ] `get_now()` returns current lesson or "nothing right now"
- [ ] `get_schedule(day="Monday")` returns lessons for that day
- [ ] `get_room(subject="Math")` returns correct room
- [ ] `get_teacher(subject="Math")` returns correct teacher
- [ ] Server works with only SQLite (no Google Sheets at query time)

---

### Phase 2: Set Up Nanobot Agent

**Directory**: `schedule-bot/` (this directory)

**Files to create/modify**:
1. `pyproject.toml` - Already exists, needs dependencies
   - Add: `nanobot-ai`
   - Add: `mcp_schedule` (editable install from `../mcp/mcp_schedule`)

2. `config.json` - Nanobot configuration
   - Provider: custom (Qwen at `http://localhost:42005/v1`)
   - Model: `coder-model`
   - MCP server registration for `schedule`
   - Webchat channel enabled

3. `workspace/` - Agent workspace directory
   - Created by `nanobot onboard` or manually

**Configuration example**:
```json
{
  "agents": {
    "defaults": {
      "workspace": "./workspace",
      "model": "coder-model",
      "provider": "custom",
      "maxTokens": 8192,
      "contextWindowTokens": 65536,
      "temperature": 0.1,
      "maxToolIterations": 40
    }
  },
  "providers": {
    "custom": {
      "apiKey": "<QWEN_CODE_API_KEY>",
      "apiBase": "http://localhost:42005/v1"
    }
  },
  "channels": {
    "webchat": {
      "enabled": true,
      "allow_from": ["*"]
    }
  },
  "tools": {
    "mcpServers": {
      "schedule": {
        "command": "python",
        "args": ["-m", "mcp_schedule"],
        "env": {
          "SCHEDULE_DB_PATH": "./data/schedule.db",
          "SCHEDULE_SHEET_URL": "https://docs.google.com/spreadsheets/d/1GlRGsy6-UvdIqj_E-iT9UBz9gvBNba5qHTjfm-npyjI/"
        }
      }
    }
  }
}
```

**Acceptance criteria**:
- [ ] `uv add nanobot-ai` completes successfully
- [ ] `uv add -e ../mcp/mcp_schedule` completes successfully
- [ ] `config.json` is properly configured
- [ ] `uv run nanobot agent -c ./config.json -m "What is 2+2?"` works
- [ ] Agent can discover and use schedule MCP tools
- [ ] `uv run nanobot agent -c ./config.json -m "What classes do I have today?"` returns real schedule data

---

### Phase 3: Write Schedule Skill Prompt

**File**: `workspace/skills/schedule/SKILL.md`

**Purpose**: Teach the agent how to use schedule tools effectively

**Content should include**:
- Available tools and when to use each one
- How to interpret user questions about time/day
- How to handle "today", "tomorrow", day-of-week parsing
- Response formatting (concise, in Russian by default)
- What to do when `get_now()` returns nothing
- When to suggest `sync_schedule` (if data seems stale)
- How to handle week types (even/odd weeks)

**Example structure**:
```markdown
# Schedule Assistant Skill

You are a schedule assistant. You have access to the following tools:

## Tools

### get_now()
Use when: User asks "what do I have now?", "what's happening?", "current class"
Returns: Current lesson based on system time, or "nothing right now"

### get_schedule(day: str, week_type: str | null)
Use when: User asks about a specific day's schedule
Parameters:
  - day: "Monday", "Tuesday", etc. (parse from user input)
  - week_type: "even", "odd", or null for both

### get_room(subject: str)
Use when: User asks "where is [subject]?", "room for [subject]"

### get_teacher(subject: str)
Use when: User asks "who teaches [subject]?", "teacher for [subject]"

### sync_schedule()
Use when: User asks to refresh/update schedule data, or if data seems outdated

## Response Guidelines
- Always respond in Russian unless user asks in English
- Format time as HH:MM (e.g., "10:30")
- Be concise and direct
- If no classes found, say so clearly
- Suggest sync if user reports outdated information

## Examples
- "What do I have today?" → get_schedule("Monday") (if today is Monday)
- "Where is Math?" → get_room("Math")
- "What's my next class?" → get_now()
```

**Acceptance criteria**:
- [ ] Skill prompt exists at `workspace/skills/schedule/SKILL.md`
- [ ] Agent follows correct tool selection for common questions
- [ ] Responses are formatted consistently and concisely
- [ ] Agent handles ambiguous questions correctly (e.g., "show me scores" without specifying lab)

---

### Phase 4: Web Chat + Deployment (Optional)

**Components**:
1. **Webchat Channel** - Already enabled in config.json
2. **Caddy Reverse Proxy** - WebSocket endpoint at `/ws/chat`
3. **Docker Compose** - Containerize the agent
4. **Flutter Web Client** (Optional) - UI for chat

**Files to create** (if implementing):
- `Dockerfile` - Container image for nanobot agent
- `entrypoint.py` - Docker entrypoint script
- `docker-compose.yml` - Full deployment configuration
- Caddy configuration for reverse proxy

**Acceptance criteria**:
- [ ] Web chat interface accessible via browser
- [ ] WebSocket connection at `/ws/chat` works
- [ ] Agent responds to messages via web chat
- [ ] (Optional) Flutter web client deployed

---

### Phase 5: Testing & Verification

**Test scenarios**:
1. **Tool Testing**:
   - [ ] Each MCP tool works independently
   - [ ] Tools handle edge cases (no data, invalid input)

2. **Natural Language Testing**:
   - [ ] "What do I have today?" → Returns today's schedule
   - [ ] "Where is Math?" → Returns room number
   - [ ] "Who teaches Physics?" → Returns teacher name
   - [ ] "What's happening now?" → Returns current class or "nothing"
   - [ ] "Show me Monday's schedule" → Returns Monday lessons

3. **Offline Mode Testing**:
   - [ ] Block Google Sheets access (e.g., modify hosts file)
   - [ ] Verify bot still works with cached SQLite data
   - [ ] `sync_schedule()` fails gracefully with error message

4. **Sync Testing**:
   - [ ] Update the Google Sheet
   - [ ] Call `sync_schedule()`
   - [ ] Verify changes appear in agent responses

5. **Week Type Handling**:
   - [ ] Agent correctly handles even/odd week schedules
   - [ ] Agent asks for week type if ambiguous

---

## Key Design Decisions

### Why SQLite?
- **Offline resilience**: Works even when Google Sheets is unreachable
- **Performance**: Local queries are fast
- **Simplicity**: No external database dependency
- **Single source of truth at query time**: MCP server always reads from SQLite

### Why not query Google Sheets directly?
- Google Sheets has rate limits
- Network latency would make responses slow
- Offline operation is a requirement
- Sync-once, query-many pattern is more efficient

### Why skill prompt?
- LLM needs guidance on *which* tool to call *when*
- Tool descriptions alone aren't enough for complex routing
- Skill prompt teaches strategy, not just capability
- Improves response quality and consistency

---

## Dependencies

### MCP Server (`mcp/mcp_schedule/`)
- `mcp` - MCP protocol implementation
- `gspread` or `requests` - Google Sheets access
- `httpx` - HTTP client (optional, if using requests)

### Nanobot Agent (`schedule-bot/`)
- `nanobot-ai` - Agent framework
- `mcp_schedule` (editable) - Schedule MCP server

### System Requirements
- Python 3.11+
- `uv` package manager
- Access to Qwen Code API at `http://localhost:42005/v1`
- Google Sheets URL: `https://docs.google.com/spreadsheets/d/1GlRGsy6-UvdIqj_E-iT9UBz9gvBNba5qHTjfm-npyjI/`

---

## Timeline & Order of Implementation

1. ✅ **Phase 1**: Schedule MCP Server (blocking - everything else depends on this)
2. ✅ **Phase 2**: Nanobot Agent Setup (needs Phase 1 complete)
3. ✅ **Phase 3**: Schedule Skill Prompt (needs Phase 2 complete)
4. ⚠️ **Phase 4**: Web Chat + Deployment (optional, can be done anytime after Phase 2)
5. ✅ **Phase 5**: Testing & Verification (after all phases complete)

---

## Google Sheet Structure

**URL**: `https://docs.google.com/spreadsheets/d/1GlRGsy6-UvdIqj_E-iT9UBz9gvBNba5qHTjfm-npyjI/`

**Expected columns** (to be verified by fetching the sheet):
- Day of week (Monday-Friday)
- Time start (HH:MM)
- Time end (HH:MM)
- Subject name
- Room number
- Teacher name
- Week type (even/odd/both)

**Parsing strategy**:
- Fetch as CSV or JSON
- Map columns to database schema
- Handle week type alternation
- Insert/replace in SQLite on sync

---

## Troubleshooting

### Common issues:
1. **MCP server doesn't start**: Check Python path, dependencies, environment variables
2. **Agent can't find tools**: Verify config.json MCP server registration
3. **Sync fails**: Check Google Sheets URL is accessible, parse logic is correct
4. **Agent calls wrong tool**: Improve skill prompt, check tool descriptions
5. **Offline mode doesn't work**: Verify SQLite database exists and has data
6. **Web chat not working**: Check webchat channel enabled in config, WebSocket endpoint accessible

### Debug commands:
- `uv run nanobot agent -c ./config.json -m "test"` - Test agent connectivity
- `python -m mcp_schedule` - Test MCP server directly
- Check `data/schedule.db` with SQLite browser to verify data
- Review nanobot logs for tool call decisions

---

## Next Steps

1. Start with **Phase 1**: Create the Schedule MCP Server
2. Test MCP server independently
3. Move to **Phase 2**: Set up Nanobot agent
4. Test agent with MCP tools
5. Write **Phase 3**: Schedule skill prompt
6. Test agent behavior with skill prompt
7. (Optional) **Phase 4**: Deploy with web chat
8. **Phase 5**: Comprehensive testing

Each phase should be completed and tested before moving to the next. Don't skip ahead!

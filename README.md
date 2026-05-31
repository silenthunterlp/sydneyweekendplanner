# 🌊 Sydney Weekend Planner

An AI-powered agent that plans personalised Sydney weekends for users — factoring in live weather, local events, and transport costs — delivered via a web chat UI, WhatsApp, or Telegram.

---

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Project Structure](#project-structure)
4. [Prerequisites](#prerequisites)
5. [Quick Start](#quick-start)
6. [Configuration](#configuration)
7. [Running the Agent](#running-the-agent)
8. [Channels](#channels)
9. [User Preferences & Memory](#user-preferences--memory)
10. [Agent Design](#agent-design)
11. [Services](#services)
12. [Testing](#testing)
13. [Deployment Notes](#deployment-notes)

---

## Overview

Sydney Weekend Planner is a multi-channel AI agent built on the **Anthropic Claude API** (`claude-sonnet-4-6`). Given a user's preferences, it fetches a live Sydney weather forecast, searches for local events, retrieves public transport options and Opal fares, and delivers a personalised Saturday + Sunday itinerary.

### Channels

```mermaid
graph LR
    U1(👤 Web user) -->|WebSocket| WEB[Web Chat<br/>localhost:8000]
    U2(📱 WhatsApp user) -->|Twilio webhook| WA[WhatsApp<br/>POST /webhook/whatsapp]
    U3(🤖 Telegram user) -->|Bot polling| TG[Telegram Bot<br/>python-telegram-bot]
    WEB --> AGENT((PlannerAgent))
    WA  --> AGENT
    TG  --> AGENT
    AGENT --> DB[(SQLite<br/>Memory)]
```

All three channels share the same agent core and persistent memory store. User IDs are prefixed by channel (`web:`, `whatsapp:`, `telegram:`) so preferences are never accidentally merged across channels.

---

## Architecture

### System Overview

```mermaid
flowchart TD
    subgraph Channels
        WEB[Web — WebSocket]
        WA[WhatsApp — Twilio]
        TG[Telegram — Bot]
    end

    subgraph Agent Core
        PA[PlannerAgent.chat]
        LOOP[Agentic Tool-Use Loop]
        SP[System Prompt Builder]
    end

    subgraph Tools
        TH[ToolHandlers.dispatch]
        T1[get_weather]
        T2[search_events]
        T3[get_transport_options]
        T4[get_user_preferences]
        T5[save_user_preferences]
    end

    subgraph External APIs
        OM[Open-Meteo]
        EB[Eventbrite / RSS]
        TF[TfNSW Trip Planner]
        NM[Nominatim / OSM]
        CL[Claude API<br/>claude-sonnet-4-6]
    end

    subgraph Memory
        DB[(SQLite)]
        UPR[UserPreferences]
        CH[ConversationHistory]
    end

    WEB & WA & TG -->|chat(user_id, msg, channel)| PA
    PA --> SP
    PA --> DB
    PA --> LOOP
    LOOP <-->|tools=TOOLS| CL
    LOOP --> TH
    TH --> T1 & T2 & T3 & T4 & T5
    T1 --> OM
    T2 --> EB
    T3 --> TF
    T3 --> NM
    T4 & T5 --> DB
    DB --- UPR & CH
```

### Key Design Decisions

| Decision | Rationale |
|---|---|
| Hand-rolled tool-use loop | ~30 lines following Anthropic's own pattern. No LangChain overhead; transparent and debuggable. |
| Single FastAPI app for all channels | Web UI, WhatsApp webhook, and health endpoint share one port. Telegram runs as a background task. |
| Prompt caching on system prompt | `cache_control: ephemeral` reduces latency and API cost on repeat calls (5 min TTL). |
| Channel-scoped `user_id` prefix | Prevents accidental cross-channel memory merging. |
| SQLite for persistence | Zero infrastructure. Swap `DATABASE_URL` for PostgreSQL — SQLAlchemy 2.x is database-agnostic. |
| Eventbrite → RSS fallback | Gracefully degrades if no API key is configured; always returns something useful. |

---

## Project Structure

```
SydneyPlanner/
├── .env                          # Your secrets (never committed)
├── .env.example                  # Template — copy to .env
├── .gitignore
├── requirements.txt              # Runtime dependencies
├── requirements-dev.txt          # Test-only dependencies
├── pytest.ini                    # asyncio_mode = auto
│
├── sydney_planner/
│   ├── config.py                 # Settings dataclass (pydantic-settings)
│   │
│   ├── agent/
│   │   ├── core.py               # PlannerAgent — main agentic loop
│   │   ├── tools.py              # TOOLS list — Claude tool JSON schemas
│   │   ├── tool_handlers.py      # ToolHandlers.dispatch() — routes to services
│   │   ├── prompts.py            # build_system_prompt(prefs, weekend_dates)
│   │   └── conversation.py       # history helpers
│   │
│   ├── channels/
│   │   ├── base.py               # ChannelAdapter ABC + normalize_user_id()
│   │   ├── web.py                # FastAPI app + WebSocket /ws/{session_id}
│   │   ├── whatsapp.py           # POST /webhook/whatsapp → TwiML response
│   │   └── telegram.py           # build_telegram_app() + message handler
│   │
│   ├── services/
│   │   ├── weather.py            # WeatherService → Open-Meteo
│   │   ├── events.py             # EventsService → Eventbrite / RSS fallback
│   │   ├── transport.py          # TransportService → TfNSW Trip Planner
│   │   └── geocoding.py          # GeocodingService → Nominatim/OSM
│   │
│   ├── memory/
│   │   ├── models.py             # SQLAlchemy ORM: UserPreferences, ConversationHistory
│   │   ├── repository.py         # UserPreferencesRepository (async CRUD)
│   │   └── session.py            # create_engine_and_tables()
│   │
│   └── utils/
│       ├── date_helpers.py       # get_upcoming_weekend() → (sat_iso, sun_iso)
│       └── formatting.py         # Markdown → WhatsApp / Telegram safe text
│
├── static/                       # Web UI (served by FastAPI)
│   ├── index.html
│   ├── chat.js                   # WebSocket client; session_id in sessionStorage
│   └── style.css
│
├── tests/
│   ├── conftest.py               # In-memory SQLite, sample data fixtures
│   ├── test_date_helpers.py
│   ├── test_memory_repository.py
│   ├── test_tool_handlers.py
│   └── test_weather_service.py
│
└── scripts/
    ├── run_dev.py                # Dev entry point — wires all components
    ├── seed_db.py                # Create tables + insert a sample user
    └── package_skills.py         # Package dev skills into .skill files
```

---

## Prerequisites

```mermaid
graph LR
    REQ[Python 3.12+] --> CORE
    KEY[Anthropic API Key<br/>console.anthropic.com] --> CORE

    subgraph CORE[Required]
        C1[anthropic SDK]
        C2[FastAPI + uvicorn]
        C3[SQLAlchemy async]
    end

    subgraph OPT[Optional — enables extra channels/features]
        O1[Twilio account<br/>WhatsApp channel]
        O2[Telegram Bot Token<br/>@BotFather]
        O3[Eventbrite API key<br/>richer event data]
        O4[TfNSW API key<br/>opendata.transport.nsw.gov.au]
    end

    CORE --> OPT
```

---

## Quick Start

```bash
# 1. Enter project
cd SydneyPlanner

# 2. Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env — at minimum set ANTHROPIC_API_KEY

# 5. (Optional) Seed a test user to skip onboarding
python scripts/seed_db.py

# 6. Start the server
python scripts/run_dev.py
```

Open **http://localhost:8000** and start chatting.

---

## Configuration

All configuration is loaded from `.env` via `pydantic-settings`.

```mermaid
graph TD
    ENV[.env file] --> PS[pydantic-settings<br/>Settings dataclass]
    PS --> CORE_CFG[Core<br/>ANTHROPIC_API_KEY<br/>CLAUDE_MODEL<br/>DATABASE_URL<br/>WEB_PORT]
    PS --> WA_CFG[WhatsApp<br/>TWILIO_ACCOUNT_SID<br/>TWILIO_AUTH_TOKEN<br/>TWILIO_WHATSAPP_FROM]
    PS --> TG_CFG[Telegram<br/>TELEGRAM_BOT_TOKEN]
    PS --> EXT_CFG[External Services<br/>EVENTBRITE_API_KEY<br/>TFNSW_API_KEY]

    CORE_CFG -->|required| AGENT((Agent))
    WA_CFG -->|optional| WA_CH[WhatsApp channel]
    TG_CFG -->|optional| TG_CH[Telegram channel]
    EXT_CFG -->|optional — fallback used if absent| SVCS[Services]
```

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | ✅ Yes | Your Anthropic API key |
| `CLAUDE_MODEL` | No | Defaults to `claude-sonnet-4-6` |
| `TWILIO_ACCOUNT_SID` | WhatsApp only | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | WhatsApp only | Twilio auth token (used to verify webhook signatures) |
| `TWILIO_WHATSAPP_FROM` | WhatsApp only | e.g. `whatsapp:+14155238886` |
| `TELEGRAM_BOT_TOKEN` | Telegram only | From @BotFather |
| `EVENTBRITE_API_KEY` | No | Falls back to RSS without it |
| `TFNSW_API_KEY` | No | Falls back to Google Maps hint without it |
| `DATABASE_URL` | No | Defaults to `sqlite+aiosqlite:///./sydney_planner.db` |
| `WEB_PORT` | No | Defaults to `8000` |

---

## Running the Agent

### Development (all channels on one process)

```bash
python scripts/run_dev.py
```

```mermaid
graph LR
    RUN[run_dev.py] --> UV[uvicorn<br/>port 8000]
    RUN --> TG_POLL[Telegram polling<br/>background task]
    UV --> WEB_UI[Web UI<br/>GET /]
    UV --> WS[WebSocket<br/>ws://…/ws/{id}]
    UV --> WA_WH[WhatsApp webhook<br/>POST /webhook/whatsapp]
    UV --> HEALTH[Health check<br/>GET /health]
```

### Web UI only

```bash
uvicorn sydney_planner.channels.web:build_web_app --factory --port 8000 --reload
```

---

## Channels

### Channel Setup Overview

```mermaid
sequenceDiagram
    participant U as User
    participant CH as Channel Adapter
    participant AG as PlannerAgent
    participant CL as Claude API
    participant DB as SQLite

    U->>CH: sends message
    CH->>AG: chat(user_id, message, channel)
    AG->>DB: load history (last 20 turns)
    AG->>DB: load user preferences
    AG->>CL: messages + tools + system prompt
    CL-->>AG: stop_reason = tool_use
    AG->>AG: execute tools (weather / events / transport)
    AG->>CL: tool results
    CL-->>AG: stop_reason = end_turn
    AG->>DB: save user message + reply
    AG-->>CH: reply text
    CH-->>U: formatted response
```

### Web Chat

Navigate to `http://localhost:8000`. The vanilla-JS client connects via WebSocket to `/ws/{session_id}`, where `session_id` is generated on first load and stored in `sessionStorage` — so your conversation persists through page refreshes.

### WhatsApp Setup

```mermaid
sequenceDiagram
    participant DEV as Your Machine
    participant NG as ngrok
    participant TW as Twilio
    participant WA as WhatsApp User

    DEV->>NG: ngrok http 8000
    NG-->>DEV: https://xxxx.ngrok.io
    DEV->>TW: set webhook → https://xxxx.ngrok.io/webhook/whatsapp
    WA->>TW: sends message
    TW->>DEV: POST /webhook/whatsapp (signed)
    DEV->>TW: TwiML response
    TW-->>WA: reply message
```

1. Create a [Twilio](https://www.twilio.com) account and join the WhatsApp Sandbox.
2. Expose your local server: `ngrok http 8000`
3. Set the sandbox webhook URL to: `https://<your-ngrok-id>.ngrok.io/webhook/whatsapp`
4. Send a message from the sandbox number.

### Telegram

1. Message [@BotFather](https://t.me/botfather) → `/newbot` → copy the token.
2. Add `TELEGRAM_BOT_TOKEN=<token>` to `.env`.
3. Start the server — polling begins automatically.

---

## User Preferences & Memory

### Data Model

```mermaid
erDiagram
    UserPreferences {
        int     id PK
        string  user_id UK
        string  channel
        string  home_suburb
        int     budget_per_day_aud
        json    interests
        string  preferred_transport
        bool    accessibility_needs
        string  group_type
        json    children_ages
        bool    avoids_rain
        int     max_travel_time_minutes
        bool    prefers_early_start
        bool    onboarding_complete
        datetime created_at
        datetime updated_at
    }

    ConversationHistory {
        int     id PK
        string  user_id FK
        string  role
        string  content
        datetime timestamp
        string  weekend_reference
    }

    UserPreferences ||--o{ ConversationHistory : "user_id"
```

### Onboarding Flow

```mermaid
flowchart TD
    START([New message received]) --> CHK{onboarding_complete?}
    CHK -->|Yes| PLAN[Build weekend plan directly]
    CHK -->|No| Q1[Ask: home suburb?]
    Q1 --> S1[save home_suburb]
    S1 --> Q2[Ask: interests?]
    Q2 --> S2[save interests]
    S2 --> Q3[Ask: budget per day?]
    Q3 --> S3[save budget_per_day_aud]
    S3 --> Q4[Ask: group type?]
    Q4 --> S4[save group_type +<br/>set onboarding_complete=True]
    S4 --> PLAN
    PLAN --> WEATHER[get_weather]
    PLAN --> EVENTS[search_events]
    WEATHER & EVENTS --> ITINERARY[Return Saturday + Sunday itinerary]
```

Preferences update naturally during conversation — saying *"I moved to Glebe"* causes the agent to call `save_user_preferences({home_suburb: "Glebe"})` without any special command.

---

## Agent Design

### Tool-Use Loop

```mermaid
flowchart TD
    CHAT["chat(user_id, message, channel)"]
    LOAD[Load history + prefs from SQLite]
    PROMPT[Build system prompt]
    CALL[POST to Claude API<br/>with tools=TOOLS]
    CHECK{stop_reason?}
    EXEC[Execute all tool_use blocks<br/>via ToolHandlers.dispatch]
    APPEND[Append tool_results to messages]
    SAVE[Save to ConversationHistory]
    RETURN[Return text to channel]
    ERROR[Return error message]

    CHAT --> LOAD --> PROMPT --> CALL --> CHECK
    CHECK -->|tool_use| EXEC --> APPEND --> CALL
    CHECK -->|end_turn| SAVE --> RETURN
    CHECK -->|other| ERROR
```

### Available Tools

```mermaid
graph LR
    AG((Agent)) --> T1["get_weather<br/>(start_date, end_date)"]
    AG --> T2["search_events<br/>(date, category, suburb, max_price)"]
    AG --> T3["get_transport_options<br/>(origin, destination, departure)"]
    AG --> T4["get_user_preferences<br/>(user_id)"]
    AG --> T5["save_user_preferences<br/>(user_id, preferences)"]

    T1 --> OM[Open-Meteo API]
    T2 --> EB[Eventbrite API]
    T2 --> RSS[RSS fallback]
    T3 --> TFNSW[TfNSW Trip Planner]
    T3 --> GEO[Nominatim geocoding]
    T4 --> DB[(SQLite)]
    T5 --> DB
```

### Prompt Caching

The system prompt uses `"cache_control": {"type": "ephemeral"}`. Claude caches the prompt for 5 minutes — subsequent calls within that window skip re-processing, reducing both latency and API cost.

---

## Services

### Service Dependency Map

```mermaid
graph TD
    subgraph Free - no key needed
        OM[Open-Meteo<br/>weather forecast]
        NM[Nominatim / OSM<br/>suburb geocoding]
    end

    subgraph Optional - falls back gracefully
        EB[Eventbrite API<br/>structured event data]
        RSS[sydney.com RSS<br/>fallback events]
        TF[TfNSW Trip Planner<br/>journey + Opal fare]
        GM[Google Maps hint<br/>fallback transport]
    end

    WS[WeatherService] --> OM
    ES[EventsService] --> EB
    EB -->|quota exceeded / no key| RSS
    TS[TransportService] --> TF
    TS --> NM
    TF -->|no API key| GM
    GS[GeocodingService] --> NM
```

### Service Details

| Service | API | Key needed | Fallback |
|---|---|---|---|
| **WeatherService** | [Open-Meteo](https://open-meteo.com/) | No | — |
| **EventsService** | [Eventbrite](https://www.eventbrite.com/platform/api) | Optional | sydney.com RSS |
| **TransportService** | [TfNSW Trip Planner](https://opendata.transport.nsw.gov.au) | Optional | Google Maps hint |
| **GeocodingService** | [Nominatim/OSM](https://nominatim.openstreetmap.org/) | No | Sydney CBD coords |

---

## Testing

```mermaid
graph LR
    subgraph Test Suite
        DH[test_date_helpers<br/>2 tests]
        MR[test_memory_repository<br/>5 tests]
        TH[test_tool_handlers<br/>3 tests]
        WS[test_weather_service<br/>2 tests]
    end

    subgraph Fixtures
        DB[(in-memory SQLite)]
        RX[respx mock<br/>HTTP calls]
    end

    DH & MR & TH & WS --> DB
    WS --> RX
    TH --> RX
```

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=sydney_planner --cov-report=term-missing
```

All external HTTP calls are mocked via [`respx`](https://lundberg.github.io/respx/) — **tests run fully offline**.

| Test file | What it covers |
|---|---|
| `test_date_helpers.py` | `get_upcoming_weekend()` returns correct Saturday/Sunday |
| `test_memory_repository.py` | Create, update, history append/retrieve, channel isolation |
| `test_tool_handlers.py` | Dispatch routing, unknown tool error, save_preferences |
| `test_weather_service.py` | Response parsing, HTTP error handling |

---

## Deployment Notes

### Production Architecture

```mermaid
graph TD
    subgraph Internet
        WA_USER[WhatsApp users]
        TG_USER[Telegram users]
        WEB_USER[Web users]
    end

    subgraph Cloud Host e.g. Railway / Render
        LB[HTTPS Load Balancer]
        APP[Sydney Planner App<br/>uvicorn + FastAPI]
        PG[(PostgreSQL<br/>swap DATABASE_URL)]
    end

    subgraph Secrets Manager
        SK[ANTHROPIC_API_KEY<br/>TWILIO creds<br/>TELEGRAM_BOT_TOKEN]
    end

    WEB_USER -->|HTTPS WebSocket| LB
    WA_USER -->|Twilio webhook| LB
    TG_USER -->|Telegram webhook| APP
    LB --> APP
    APP <--> PG
    SK --> APP
```

### Switching to PostgreSQL

Change `DATABASE_URL` in `.env`:
```
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/sydney_planner
```
Add `asyncpg` to `requirements.txt`. No code changes required — SQLAlchemy 2.x is database-agnostic.

### WhatsApp in Production

- Host behind **HTTPS** (required by Twilio)
- Set `TWILIO_ACCOUNT_SID` + `TWILIO_AUTH_TOKEN` — webhook signatures are validated automatically
- Configure the webhook URL in [Twilio Console](https://console.twilio.com) → Messaging → Settings

### Telegram in Production

Switch from polling to webhook for better performance:
```python
app.run_webhook(
    listen="0.0.0.0",
    port=443,
    url_path=settings.telegram_bot_token,
    webhook_url=f"https://your-domain.com/{settings.telegram_bot_token}",
)
```

### Environment Variables
Never commit `.env`. Use your platform's secrets manager (Railway, Render, AWS Secrets Manager, etc.) and inject variables at runtime.

# Concept Map: APIs, Data Pipelines, and MCPs
*Session: 2026-04-19 | Project: TrainingPeaks + Whoop Data*

---

## The Big Picture

You want to take your personal training and health data (living inside Whoop and TrainingPeaks) and make it available to Claude so you can have intelligent, data-driven conversations about your training. Three building blocks make this possible:

```
[Whoop App]         [TrainingPeaks App]
     |                      |
     |  (API)               |  (API)
     v                      v
[Data Pipeline]  <----------+
     |
     | (stores/transforms data)
     v
[Your Database / Files]
     |
     | (MCP)
     v
[Claude] <---> [You]
```

---

## 1. APIs — The Doors Into Your Data

**What it is:** An API (Application Programming Interface) is how software applications talk to each other. Whoop and TrainingPeaks store your data on their servers. An API is the official "door" they provide so that your code can go knock and ask for that data.

**In your project:**
- The **Whoop API** lets you request things like: "give me my heart rate data for the last 7 days" or "what was my recovery score yesterday?"
- The **TrainingPeaks API** lets you request things like: "give me my planned workouts this week" or "what were my completed activities?"

**Key concept — Authentication:** Before any API gives you data, it wants to know *you* are who you say you are. This is done with something called an API key or OAuth token — basically a digital ID card your code carries when it knocks on the door.

---

## 2. Data Pipelines — Moving and Shaping the Data

**What it is:** A data pipeline is code that:
1. **Extracts** data from a source (the API)
2. **Transforms** it into a shape you want (cleaning it, combining fields, calculating things)
3. **Loads** it somewhere useful (a database, a file, a dashboard)

This is often called **ETL** — Extract, Transform, Load.

**In your project:**
- **Extract:** Your pipeline calls the Whoop and TrainingPeaks APIs and pulls raw data
- **Transform:** You combine them — e.g., "on days my recovery score was low, what kind of training did I do?"
- **Load:** Store the result in a simple local database (SQLite is a great beginner choice) or even JSON files to start

**Key concept — Scheduling:** Pipelines often run on a schedule (e.g., every morning at 6am, pull yesterday's data). Tools like cron jobs or simple Python scripts can handle this.

---

## 3. MCPs — Giving Claude a Window Into Your Data

**What it is:** MCP stands for **Model Context Protocol**. It's a standard that Anthropic created so that Claude can connect to external tools and data sources. Think of it as a bridge between Claude and your database.

Without MCP, Claude only knows what you paste into the chat. With MCP, Claude can actively *query* your training database in real time during a conversation.

**In your project:**
- You build a small MCP server — a lightweight program that sits next to your database
- When you ask Claude "how was my training load this week?", Claude uses the MCP to query your database directly and give you a data-informed answer
- Claude becomes your personal training analyst, not just a general chatbot

**Key concept — MCP vs. just pasting data:** Pasting data works for one-off questions. MCP is what makes it a *system* — Claude can always access fresh data without you doing anything.

---

## How the Pieces Connect in Your Project

| Layer | Tool/Concept | Your Use Case |
|---|---|---|
| Data Source | Whoop API | Recovery, HRV, sleep, strain |
| Data Source | TrainingPeaks API | Planned & completed workouts |
| Pipeline | Python script | Pull, combine, and store data daily |
| Storage | SQLite or JSON files | Local database on your machine |
| Bridge | MCP Server | Lets Claude query your database |
| Interface | Claude + You | Conversational training analysis |

---

## What to Build First

1. **Whoop API connection** — easier API, good docs, public access
2. **Simple data store** — save pulls to JSON files first, graduate to SQLite
3. **TrainingPeaks connection** — add second data source once first is working
4. **MCP server** — wire it all to Claude once the data is flowing reliably

---

## Key Terms Glossary

- **API** (Application Programming Interface) — A door into someone else's data/service, accessed by your code
- **API Key / OAuth Token** — Your digital ID card to authenticate with an API
- **ETL** — Extract, Transform, Load — the three steps of a data pipeline
- **SQLite** — A simple file-based database, great for personal projects
- **MCP** — Model Context Protocol — lets Claude connect to external tools/data
- **MCP Server** — A small program you write that exposes your data to Claude

# BudgetTrack API

A simple FastAPI backend for tracking expenses and budgets with SQLite.

## Features
- CRUD for Expenses (`/api/expenses`)
- Create/Update and List Budgets (`/api/budgets`)
- Summary Analytics (`/api/analytics/summary`)
- Serves a static UI at `/` from `static/index.html`

## Tech
- FastAPI, SQLAlchemy, Pydantic
- SQLite (local dev)
- Uvicorn

## Setup

```bash
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

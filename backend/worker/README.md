# Backend Worker

## Purpose
Runs background jobs:
- ingestion pulls
- agent workflow runs (LangGraph)
- monitoring + refresh scheduling

In production, this runs as a separate process/container from the API.

## Run (local)
For MVP we start with a simple CLI runner.

- `python -m worker.run`

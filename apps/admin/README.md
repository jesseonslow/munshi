# Munshi Admin (`munshi-admin`)

Streamlit-powered administrative cockpit and operational workbench for the **Mat Munshi** archival knowledge pipeline.

This dashboard provides an operator interface to manage and trigger backend stages—from raw PDF ingestion (`docproc`)[cite: 21] and entity ledger curation (`ledger`)[cite: 21] to graph reconciliation (`janitor`) and Open Knowledge Format encyclopedia synthesis (`synthesizer`)[cite: 21].

---

## Architecture & Layout

The dashboard uses Streamlit's native multi-page structure, communicating with the backend exclusively via `MunshiApiClient` over HTTP (FastAPI on Port 8000)[cite: 18]:

```
apps/admin/
├── pyproject.toml
├── README.md
└── src/
    └── munshi_admin/
        ├── __init__.py
        ├── app.py                     # Executive Overview & Pipeline Health Monitor
        ├── client.py                  # Typed HTTP bridge to munshi-api
        └── pages/
            ├── 1_📚_Wiki_Catalog.py   # Catalog, inspection, and metadata editor
            ├── 2_🧹_Janitor.py         # Author reattribution & source-path fixing
            ├── 3_📥_Docproc.py         # Drag-and-drop PDF ingest & queue monitoring
            ├── 4_🗄️_Ledger.py          # Entity occurrences, de-aliasing, & ignore list
            ├── 5_✍🏻_Summarizer.py     # Batch OKF publication summarization
            └── 6_⚡_Synthesizer.py     # Batch OKF topic generation & review desk

```
---

## Configuration

The dashboard connects to munshi-api via the following environment variable (defaults to localhost):

```
MUNSHI_API_URL="[http://127.0.0.1:8000/api](http://127.0.0.1:8000/api)"

```

### Running the Dashboard
 
### 1. Start the API Backend

Ensure the FastAPI control plane is running in a terminal:

```
uv run --package munshi-api uvicorn munshi_api.app:app --reload --port 8000

```

### 2. Launch the Streamlit Admin Cockpit

In another terminal, run:

```
uv run --package munshi-admin streamlit run apps/admin/src/munshi_admin/app.py

```

---

### Verification Workspace Sync

To sync and run the updated application:

1. **Sync dependencies:**

```
uv sync

```

2. **Launch the backend:**

```
uv run --package munshi-api uvicorn munshi_api.app:app --reload --port 8000

```

3. **Launch the cockpit:**

```
uv run --package munshi-admin streamlit run apps/admin/src/munshi_admin/app.py

```


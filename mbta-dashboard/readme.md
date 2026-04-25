# MBTA Bus Performance Dashboard

**CSE 5114 Data Manipulation and Management at Scale**  
**Washington University in St. Louis**  
**Group 1: Grace Lee, Mijung Jung, Duy Huynh**

---

## Overview

A historical performance dashboard for MBTA bus routes in Boston, MA.
Built to support transparency and accountability efforts at the MBTA — notably,
the MBTA's own public dashboard has no metrics for bus routes specifically.

---

## Pipeline Architecture

```
MBTA GTFS-RT API (every 60 seconds)
         ↓
    AWS Lambda
    (fetches protobuf .pb files)
         ↓
    AWS S3
    (raw protobuf snapshots, partitioned by date/hour)
         ↓
    Apache Spark
    (decodes protobuf → structured rows)
         ↓
    Snowflake — LEMMING_DB
    ├── FINAL_PROJECT_RAW    ← decoded snapshots
    ├── FINAL_PROJECT_STATIC ← GTFS schedule (dim tables)
    ├── FINAL_PROJECT_FACT   ← cleaned, joined events
    └── FINAL_PROJECT_MART   ← aggregated metrics for dashboard
         ↓
    Streamlit Dashboard
    (queries MART tables)
```

---

## Dashboard Features

The dashboard exposes a sidebar with a **date range** filter and a **route**
multi-select filter. When the date range is set to a single day, the time-series
charts switch from a daily view to an hourly view.

### Occupancy %
- Snapshot-weighted average occupancy across the selected routes and dates
- Daily trend line (or hourly line when a single day is selected)
- Hover tooltip with the full status breakdown (empty / many seats / few seats / standing room / crushed standing / full / no data)
- Top 10 most crowded routes table (ignores the route filter)

### Alerts by route
- Daily stacked bar chart of alert counts by severity (SEVERE / WARNING / INFO)
- Top 10 routes most affected by alerts, with a multiselect to choose which severities count toward the ranking

### Alerts by stop
- Geographic alert hotspot map (bubble size = alert count, color = severe count)
- Top 10 stops most affected by alerts, with the same severity multiselect

### On time performance
- Daily on-time % trend (or hourly when a single day is selected)
  - on time = arrival within 2.5 min early to 5 min late of schedule
- Hover tooltip with on time / early / late breakdown and event counts
- Top 10 routes with the lowest on-time performance

### Service delivered %
- Daily % of scheduled trips that were actually delivered in entirety
- Hover tooltip with delivered / canceled / no RT data / added trip breakdowns

---

## File Structure

```
mbta-dashboard/
├── dashboard.py              ← main Streamlit app (sidebar filters + tab routing)
├── data_access.py            ← Snowflake connection + cached query() helper
├── readme.md                 ← this file
├── tabs/
│   ├── occupancy_route_tab.py
│   ├── alerts_route_tab.py
│   ├── alerts_stop_tab.py
│   ├── on_time_performance_tab.py
│   └── service_delivered_tab.py
└── .streamlit/
    └── secrets.toml          ← credentials (not committed to git)
```

---

## Setup

### Prerequisites
Install the dashboard dependencies (pinned in the repo-root `requirements.txt`):
```bash
pip install -r ../requirements.txt
```

### Credentials
Copy the example secrets file and fill in your Snowflake values:
```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Minimal `secrets.toml` for local development:
```toml
SF_USER             = "your_snowflake_username"
SF_ACCOUNT          = "UNB02139"
SF_WAREHOUSE        = "LEMMING_WH"
SF_DATABASE         = "LEMMING_DB"
SF_PRIVATE_KEY_PATH = "/path/to/rsa_key.p8"
```

For Streamlit Community Cloud (no persistent filesystem), use `SF_PRIVATE_KEY`
instead and paste the full PEM contents of the `.p8` file as a triple-quoted
string. See `.streamlit/secrets.toml.example` for the exact format.

### Run locally
```bash
cd mbta-dashboard
streamlit run dashboard.py
```

Open `http://localhost:8501` in your browser.

### Deploy to Streamlit Community Cloud
1. Push this repo to GitHub.
2. Create a new app at <https://share.streamlit.io> with main file path
   `mbta-dashboard/dashboard.py`.
3. Paste the contents of `.streamlit/secrets.toml.example` into the app's
   **Settings → Secrets** panel and replace the placeholder values.
4. Save — the app redeploys automatically. Streamlit Cloud picks up
   `requirements.txt` from the repo root.

---

## Data Sources

- **Live data:** [MBTA GTFS-RT API](https://www.mbta.com/developers/v3-api) — vehicle positions, trip updates, alerts (public, no API key required)
- **Static schedule:** [MBTA GTFS](https://www.mbta.com/developers/gtfs) — routes, stops, trips, stop times
- **Collection period:** March 2026 – present

---
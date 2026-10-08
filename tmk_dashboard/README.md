# TMK Dashboard — Pure Python (Streamlit)

Rebuild of the single-file `DASHBOARD.html` TMK MIS app as a Streamlit multipage application.

## Features

- Dual Excel ingest (TMK-A + Resource Allocation) with fuzzy column matching
- Optional SharePoint auto-load (`config.AUTO_LOAD_FROM_SHAREPOINT`)
- Billing Projects (5 sub-tabs): details, editable resources/finance, overviews, weekly heatmap, Excel/PDF export
- Period cascade: Year → Quarter → Month → Week
- TMK Overview with engineers / ICR / KPI drill-downs
- High Level Status (RAG + highlights/issues + PDF)
- Risks/Action Items & Future Resourcing (CRUD + Excel)
- Milestone (Excel + Highlights PDF parse + Gantt + updates + exports)
- Account Buffer (year/month drill-down)
- TMK Project Commercials (variance chart + Excel)
- SQLite persistence (replaces localStorage)
- Change log + Full Dashboard PDF from Home sidebar

## Run

```bash
cd tmk_dashboard
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

Open the URL Streamlit prints (usually http://localhost:8501).

### SharePoint auto-load (synced local folder)

Files are read from your OneDrive **Sync** of the TMK-MIS SharePoint library
(configured in `config.py`):

```python
AUTO_LOAD_FROM_SHAREPOINT = True
USE_LOCAL_SYNC_PATHS = True
LOCAL_RESOURCE_INFO_TRACKER = r"C:\Users\…\Resource_Information_Tracker.xlsm"
LOCAL_RESOURCE_ALLOCATION = r"C:\Users\…\Resourse Allocation Files June 2026 (1).xlsx"
```

On Home startup the app loads Resource Info Tracker + Resource Allocation automatically.
On the **Milestone** page it also auto-loads Milestone Excel + Highlights PDF from the same
sync folder. Use **Reload from SharePoint sync** to refresh after SharePoint updates, or
fall back to manual upload if sync is offline.

### Feature parity vs DASHBOARD.html

| Area | Status |
|------|--------|
| Dual Excel ingest + fuzzy columns | Done |
| Billing 5 sub-tabs + cascade + save/export | Done |
| TMK Overview + engineers/ICR/KPI | Done |
| HLS RAG + PDF | Done |
| Risks / Future Resourcing CRUD + Excel | Done |
| Milestone Excel/PDF/Gantt/updates | Done |
| Account Buffer | Done |
| Commercials + variance chart | Done |
| SQLite persistence + change log | Done |
| Full dashboard PDF | Done |
| SharePoint auto-load | Done (config flag) |

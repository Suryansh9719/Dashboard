"""TMK Dashboard configuration."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "tmk.db"

# ── Auto-load from SharePoint-synced local folder (Option 1) ───────────────
# Set True to load workbooks on Home startup without manual upload.
AUTO_LOAD_FROM_SHAREPOINT = True
USE_LOCAL_SYNC_PATHS = True

# Paths from OneDrive "Sync" of the TMK-MIS SharePoint Documents library
LOCAL_RESOURCE_INFO_TRACKER = (
    r"C:\Users\10354172\NTT DATA, Inc\TMK-MIS - Documents\Resource_Information_Tracker.xlsm"
)
# Preferred Resource Allocation workbook. Auto-load also scans sibling folders and
# picks the newest matching *Allocation*.xlsx so the project count always follows
# the latest uploaded / downloaded file (not a stale copy).
LOCAL_RESOURCE_ALLOCATION = (
    r"C:\Users\10354172\NTT DATA, Inc\TMK-MIS - Documents\Resourse Allocation Files June 2026 (1).xlsx"
)
# Extra dirs to search when resolving the newest Allocation workbook
LOCAL_ALLOCATION_SEARCH_DIRS = [
    r"C:\Users\10354172\NTT DATA, Inc\TMK-MIS - Documents",
    r"C:\Users\10354172\Downloads",
]
LOCAL_MILESTONE_XLSX = (
    r"C:\Users\10354172\NTT DATA, Inc\TMK-MIS - Documents\Milestone_Export_21stJuly26 (3).xlsx"
)
LOCAL_HIGHLIGHTS_PDF = (
    r"C:\Users\10354172\NTT DATA, Inc\TMK-MIS - Documents\Highlights (1).pdf"
)

# Online SharePoint URLs (kept for reference / future Graph auth). Not used when
# USE_LOCAL_SYNC_PATHS is True — anonymous HTTP usually returns 401.
SP_FILE1_URL = (
    "https://nttdata.sharepoint.com/sites/SRVS-AS-Account-Kiln/MIS/Shared%20Documents/"
    "Resource_Information_Tracker.xlsm"
)
SP_FILE2_URL = (
    "https://nttdata.sharepoint.com/sites/SRVS-AS-Account-Kiln/MIS/Shared%20Documents/"
    "Resourse%20Allocation%20Files%20June%202026%20(1).xlsx"
)

MS_FIXED_PROJECTS = [
    "AMS",
    "SASR",
    "Eclipse Redaction",
    "1880-RITC",
    "CMS",
    "IDP",
    "EM",
]

# Used on Milestone full-report PDF header (matches DASHBOARD.html .hls-title default)
ACCOUNT_NAME = "Tokio Marine Kiln"

MONTH_NAMES = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]
MONTH_NAMES_FULL = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

DEFAULT_HLS_PROJECTS = [
    "AMS-SRPT", "ADS", "IDP", "CMS", "SASR", "Eclipse Redaction",
]

# ── OneNote → High Level Status Highlights / Issues ─────────────────────────
# Your notebook link is PERSONAL OneDrive (nttdata-my.sharepoint.com/personal/...),
# so there is NO Team Group ID. Use ONENOTE_USER_UPN instead.
#
# From:
#   .../personal/10357769_nttdata_com/Documents/Notebooks/Demo
# UPN is:
#   10357769@nttdata.com
#
# Still need Azure AD app + Notes.Read.All (Application) + admin consent.
ONENOTE_AUTO_SYNC = True
MS_GRAPH_TENANT_ID = ""
MS_GRAPH_CLIENT_ID = ""
MS_GRAPH_CLIENT_SECRET = ""
# Personal notebook owner (preferred for your Demo notebook)
ONENOTE_USER_UPN = "10357769@nttdata.com"
# Only if the notebook later moves into a Team — leave blank for personal
ONENOTE_GROUP_ID = ""
ONENOTE_NOTEBOOK_NAME = "Demo"
ONENOTE_SECTION_NAME = "Weekly Meeting"
ONENOTE_PAGE_TITLE = ""  # empty = newest page
ONENOTE_LOCAL_HTML = ""

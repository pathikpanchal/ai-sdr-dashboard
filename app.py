import streamlit as st
import pandas as pd
import sqlite3
import uuid
import html
import re
import ssl
import smtplib
import secrets as pysecrets
import requests
import json
import os
import hashlib
import time
from email.message import EmailMessage
from email.utils import formataddr
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "ai_sdr.db"

st.set_page_config(page_title="AI SDR Dashboard", page_icon="🎯", layout="wide")

st.markdown(
    """
    <style>
    /* Keep the page compact without placing the title underneath the fixed toolbar. */
    [data-testid="stAppViewContainer"] .main .block-container,
    [data-testid="stMainBlockContainer"],
    .stMainBlockContainer {
        padding-top: 1.8rem !important;
        padding-bottom: 1.4rem !important;
        margin-top: 0 !important;
    }
    [data-testid="stHeader"] {
        height: 2.75rem !important;
        min-height: 2.75rem !important;
    }
    h1 {
        margin-top: 0.1rem !important;
        padding-top: 0 !important;
        line-height: 1.2 !important;
        overflow: visible !important;
    }

    /* Hide only the native Share action where its accessible label is exposed.
       Keep Streamlit's star, edit/Codespace and theme actions visible. */
    [data-testid="stToolbar"] button[aria-label*="share" i],
    [data-testid="stToolbar"] button[title*="share" i],
    [data-testid="stToolbar"] a[aria-label*="share" i],
    [data-testid="stToolbar"] a[title*="share" i],
    div[data-testid="stToolbarActionButton"]:has([aria-label*="share" i]),
    div[data-testid="stToolbarActionButton"]:has([title*="share" i]),
    div.stToolbarActionButton:has([aria-label*="share" i]),
    div.stToolbarActionButton:has([title*="share" i]) {
        display: none !important;
    }

    /* Compact, content-sized Create Campaign action. */
    div[role="dialog"] {
        width: min(1680px, 98vw) !important;
        max-width: 98vw !important;
    }
    @media (min-width: 1200px) {
        div[role="dialog"] [data-testid="stForm"] {
            max-width: none !important;
        }
    }
    div[role="dialog"] [data-testid="stVerticalBlock"] > div {
        min-width: 0;
    }
    div[role="dialog"] [data-testid="stForm"] {
        width: 100%;
    }
    div[role="dialog"] h3 {
        margin-top: 0.15rem;
        margin-bottom: 0.55rem;
    }
    div[role="dialog"] .campaign-section-header {
        background: #dbeafe;
        color: #1e3a8a;
        border: 1px solid #bfdbfe;
        border-radius: 9px;
        padding: 0.68rem 0.9rem;
        /* Consistent breathing room between every section heading and its fields. */
        margin: 0.1rem 0 1.35rem 0;
        font-size: 1.08rem;
        font-weight: 700;
    }
    div[role="dialog"] .campaign-section-header small {
        color: #111827;
        font-size: 0.84rem;
        font-weight: 400;
        margin-left: 0.6rem;
    }
    div[role="dialog"] button[kind="primaryFormSubmit"],
    div[role="dialog"] button[kind="primary"] {
        background: #2563eb !important;
        border-color: #2563eb !important;
        color: #ffffff !important;
    }
    div[role="dialog"] [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 12px;
        border-color: #e6e8f0;
        background: #ffffff;
    }
    div[role="dialog"] [data-testid="stVerticalBlock"] {
        gap: 0.55rem !important;
    }
    /* Keep every selected multi-select value visible; allow chips to wrap. */
    div[role="dialog"] [data-testid="stMultiSelect"] [data-baseweb="select"] > div:first-child {
        display: flex !important;
        flex-wrap: wrap !important;
        height: auto !important;
        min-height: 2.45rem !important;
        align-items: center !important;
        overflow: visible !important;
        max-height: none !important;
    }
    div[role="dialog"] [data-testid="stMultiSelect"] [data-baseweb="select"] [role="combobox"] {
        min-width: 2rem !important;
    }
    div[role="dialog"] [data-testid="stMultiSelect"] [data-baseweb="tag"] {
        max-width: 100% !important;
        white-space: normal !important;
        background: #e5e7eb !important;
        color: #111827 !important;
        border: 1px solid #d1d5db !important;
    }
    div[role="dialog"] [data-testid="stMultiSelect"] [data-baseweb="select"] span {
        white-space: normal !important;
    }
    div[role="dialog"] [data-testid="InputInstructions"],
    div[role="dialog"] [data-testid="stInputInstructions"],
    div[role="dialog"] [aria-label*="Press Enter to submit form" i],
    div[role="dialog"] [title*="Press Enter to submit form" i],
    div[role="dialog"] [data-testid="InputInstructions"] *,
    div[role="dialog"] [data-testid="stInputInstructions"] * {
        display: none !important;
        visibility: hidden !important;
    }
    div[role="dialog"] button[kind="primaryFormSubmit"],
    div[role="dialog"] button[kind="primary"] {
        background: #2563eb !important;
        border-color: #2563eb !important;
        color: #ffffff !important;
    }
    div.st-key-create_campaign_button button {
        min-height: 2rem !important;
        height: 2rem !important;
        width: auto !important;
        min-width: 0 !important;
        padding: 0.2rem 0.6rem !important;
        font-size: 0.82rem !important;
        font-weight: 600 !important;
    }

    /* Team & Access compact sharing layout */
    div[data-testid="stVerticalBlockBorderWrapper"] {border-radius: 12px;}
    div.st-key-share_dashboard_form button[kind="primaryFormSubmit"] {min-height: 2.45rem;}
    [data-testid="stMetricValue"] {font-size: 1.8rem;}
    [data-testid="stMetricLabel"] {font-size: 0.95rem;}
    div[data-testid="stMarkdownContainer"] p {font-size: 1rem; line-height: 1.45;}
    div[data-testid="stCaptionContainer"] p {font-size: 0.92rem;}
    section[data-testid="stSidebar"] {background: #101b35;}
    section[data-testid="stSidebar"] * {color: #f4f6fb;}
    section[data-testid="stSidebar"] [data-testid="stRadio"] label {padding: 0.45rem 0.55rem; border-radius: 0.5rem;}
    section[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {background: rgba(124, 92, 255, 0.22);}
    div.stButton > button[kind="primary"],
    div[data-testid="stFormSubmitButton"] button {
        background: #5b35d5 !important;
        border-color: #5b35d5 !important;
        color: #ffffff !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

SENIORITY_OPTIONS = [
    "Founder", "Owner", "Board Member", "Partner", "C-suite", "VP", "Director",
    "Head", "Manager", "Senior", "Mid-level", "Entry", "Intern / in-training", "Unknown",
]
COMPANY_SIZE_OPTIONS = [
    "2-10 employees", "11-50 employees", "51-200 employees", "201-500 employees",
    "501-1,000 employees", "1,001-5,000 employees", "5,001-10,000 employees",
    "10,001+ employees",
]
# Clay's Public API `sizes` filter takes bucket boundary codes, not the UI labels.
COMPANY_SIZE_CLAY_VALUES = {
    "2-10 employees": "2",
    "11-50 employees": "10",
    "51-200 employees": "50",
    "201-500 employees": "200",
    "501-1,000 employees": "500",
    "1,001-5,000 employees": "1000",
    "5,001-10,000 employees": "5000",
    "10,001+ employees": "10000",
}
JOB_LEVEL_OPTIONS = ["Above", "Any", "Below", "Exact"]
COUNTRY_OPTIONS = [
    "Afghanistan", "Albania", "Algeria", "Andorra", "Angola", "Argentina", "Armenia", "Australia",
    "Austria", "Azerbaijan", "Bahamas", "Bahrain", "Bangladesh", "Barbados", "Belarus", "Belgium",
    "Belize", "Benin", "Bhutan", "Bolivia", "Bosnia and Herzegovina", "Botswana", "Brazil", "Brunei",
    "Bulgaria", "Cambodia", "Cameroon", "Canada", "Chile", "China", "Colombia", "Costa Rica", "Croatia",
    "Cyprus", "Czechia", "Denmark", "Dominican Republic", "Ecuador", "Egypt", "Estonia", "Ethiopia",
    "Finland", "France", "Georgia", "Germany", "Ghana", "Greece", "Guatemala", "Hong Kong", "Hungary",
    "Iceland", "India", "Indonesia", "Ireland", "Israel", "Italy", "Jamaica", "Japan", "Jordan", "Kazakhstan",
    "Kenya", "Kuwait", "Latvia", "Lebanon", "Lithuania", "Luxembourg", "Malaysia", "Maldives", "Malta",
    "Mauritius", "Mexico", "Monaco", "Mongolia", "Morocco", "Nepal", "Netherlands", "New Zealand", "Nigeria",
    "North Macedonia", "Norway", "Oman", "Pakistan", "Panama", "Peru", "Philippines", "Poland", "Portugal",
    "Puerto Rico", "Qatar", "Romania", "Russia", "Saudi Arabia", "Serbia", "Singapore", "Slovakia", "Slovenia",
    "South Africa", "South Korea", "Spain", "Sri Lanka", "Sweden", "Switzerland", "Taiwan", "Tanzania", "Thailand",
    "Tunisia", "Turkey", "Ukraine", "United Arab Emirates", "United Kingdom", "United States", "Uruguay", "Uzbekistan",
    "Venezuela", "Vietnam", "Zambia", "Zimbabwe",
]

# This ordering is used only to interpret Above / Below in this MVP.
# Above includes the selected level itself and every level ranked higher.


def get_connection():
    connection = sqlite3.connect(DB_PATH, check_same_thread=False)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS campaigns (
            id TEXT PRIMARY KEY,
            name TEXT,
            industry TEXT,
            company_country TEXT,
            contact_country TEXT,
            target_titles TEXT,
            min_score INTEGER,
            status TEXT,
            created_at TEXT,
            email_sequence_instructions TEXT DEFAULT ''
        )
        """
    )
    campaign_columns = {
        row[1] for row in connection.execute("PRAGMA table_info(campaigns)").fetchall()
    }
    if "industry_clay_value" not in campaign_columns:
        connection.execute("ALTER TABLE campaigns ADD COLUMN industry_clay_value TEXT DEFAULT ''")
    if "industry_mapping_status" not in campaign_columns:
        connection.execute("ALTER TABLE campaigns ADD COLUMN industry_mapping_status TEXT DEFAULT ''")

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS leads (
            id TEXT PRIMARY KEY,
            campaign_id TEXT,
            company TEXT,
            website TEXT,
            company_type TEXT,
            industry TEXT DEFAULT '',
            company_country TEXT,
            contact_name TEXT,
            title TEXT,
            contact_country TEXT,
            email TEXT,
            company_score INTEGER,
            contact_score INTEGER,
            qualification TEXT,
            reason TEXT,
            email1_subject TEXT,
            email1_body TEXT,
            email2_subject TEXT,
            email2_body TEXT,
            email3_subject TEXT,
            email3_body TEXT,
            review_status TEXT
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT,
            campaign_id TEXT,
            campaign_name TEXT,
            actor TEXT,
            details TEXT,
            created_at TEXT
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS team_members (
            email TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            created_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS campaign_access (
            id TEXT PRIMARY KEY,
            campaign_id TEXT NOT NULL,
            member_email TEXT NOT NULL,
            member_name TEXT NOT NULL,
            permission TEXT NOT NULL,
            invitation_token TEXT,
            invitation_status TEXT NOT NULL DEFAULT 'Pending',
            invited_by TEXT NOT NULL DEFAULT 'Workspace Admin',
            invited_at TEXT NOT NULL,
            expires_at TEXT,
            accepted_at TEXT,
            revoked_at TEXT,
            UNIQUE(campaign_id, member_email)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS workspace_access (
            id TEXT PRIMARY KEY,
            member_email TEXT NOT NULL UNIQUE,
            member_name TEXT NOT NULL,
            permission TEXT NOT NULL,
            invitation_token TEXT,
            invitation_status TEXT NOT NULL DEFAULT 'Pending',
            invited_by TEXT NOT NULL DEFAULT 'Workspace Admin',
            invited_at TEXT NOT NULL,
            expires_at TEXT,
            accepted_at TEXT,
            revoked_at TEXT
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS clay_search_runs (
            id TEXT PRIMARY KEY,
            campaign_id TEXT NOT NULL,
            clay_search_id TEXT,
            query_text TEXT NOT NULL,
            result_count INTEGER NOT NULL DEFAULT 0,
            has_more INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL,
            error_message TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS clay_company_results (
            id TEXT PRIMARY KEY,
            campaign_id TEXT NOT NULL,
            search_run_id TEXT NOT NULL,
            clay_company_id TEXT DEFAULT '',
            company_name TEXT DEFAULT '',
            domain TEXT DEFAULT '',
            industry TEXT DEFAULT '',
            country TEXT DEFAULT '',
            employee_count TEXT DEFAULT '',
            company_type TEXT DEFAULT '',
            location TEXT DEFAULT '',
            description TEXT DEFAULT '',
            linkedin_url TEXT DEFAULT '',
            annual_revenue TEXT DEFAULT '',
            raw_json TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        "CREATE TABLE IF NOT EXISTS clay_people_search_runs ("
        "id TEXT PRIMARY KEY, campaign_id TEXT NOT NULL, clay_search_id TEXT DEFAULT '', "
        "query_text TEXT NOT NULL, result_count INTEGER NOT NULL DEFAULT 0, "
        "has_more INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL, "
        "error_message TEXT DEFAULT '', debug_json TEXT DEFAULT '', created_at TEXT NOT NULL)"
    )
    connection.execute(
        "CREATE TABLE IF NOT EXISTS clay_people_results ("
        "id TEXT PRIMARY KEY, campaign_id TEXT NOT NULL, search_run_id TEXT NOT NULL, "
        "clay_profile_id TEXT DEFAULT '', full_name TEXT DEFAULT '', first_name TEXT DEFAULT '', "
        "last_name TEXT DEFAULT '', job_title TEXT DEFAULT '', seniority TEXT DEFAULT '', "
        "department TEXT DEFAULT '', location TEXT DEFAULT '', location_country TEXT DEFAULT '', "
        "company_name TEXT DEFAULT '', company_domain TEXT DEFAULT '', company_linkedin_url TEXT DEFAULT '', "
        "linkedin_url TEXT DEFAULT '', raw_json TEXT DEFAULT '', created_at TEXT NOT NULL)"
    )


    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS clay_people_search_runs (
            id TEXT PRIMARY KEY,
            campaign_id TEXT NOT NULL,
            clay_search_id TEXT DEFAULT '',
            query_text TEXT NOT NULL,
            result_count INTEGER NOT NULL DEFAULT 0,
            has_more INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL,
            error_message TEXT DEFAULT '',
            debug_json TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS clay_people_results (
            id TEXT PRIMARY KEY,
            campaign_id TEXT NOT NULL,
            search_run_id TEXT NOT NULL,
            clay_profile_id TEXT DEFAULT '',
            full_name TEXT DEFAULT '',
            job_title TEXT DEFAULT '',
            location TEXT DEFAULT '',
            location_country TEXT DEFAULT '',
            company_name TEXT DEFAULT '',
            company_domain TEXT DEFAULT '',
            linkedin_url TEXT DEFAULT '',
            raw_json TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    )

    # Add new columns safely to databases created by the earlier dashboard version.
    migrations = {
        "campaigns": {
            "current_cms": "TEXT DEFAULT ''",
            "company_state": "TEXT DEFAULT ''",
            "company_city": "TEXT DEFAULT ''",
            "company_size": "TEXT DEFAULT ''",
            "department": "TEXT DEFAULT ''",
            "seniority": "TEXT DEFAULT 'Manager'",
            "job_level": "TEXT DEFAULT 'Above'",
            "email_sequence_instructions": "TEXT DEFAULT ''",
            "clay_table_url": "TEXT DEFAULT ''",
            "clay_companies_webhook_url": "TEXT DEFAULT ''",
            "clay_contacts_webhook_url": "TEXT DEFAULT ''",
            "clay_companies_webhook_auth": "TEXT DEFAULT ''",
            "clay_contacts_webhook_auth": "TEXT DEFAULT ''",
            "campaign_owner": "TEXT DEFAULT 'Unassigned'",
            "criteria_approved": "INTEGER DEFAULT 0",
            "criteria_approved_by": "TEXT DEFAULT ''",
            "criteria_approved_at": "TEXT DEFAULT ''",
        },
        "leads": {
            "industry": "TEXT DEFAULT ''",
            "company_cms": "TEXT DEFAULT ''",
            "department": "TEXT DEFAULT ''",
            "seniority": "TEXT DEFAULT ''",
        },
        "clay_company_results": {
            "company_linkedin_url": "TEXT DEFAULT ''",
        },
        "clay_people_search_runs": {
            "debug_json": "TEXT DEFAULT ''",
        },
        "clay_people_results": {
            "first_name": "TEXT DEFAULT ''",
            "last_name": "TEXT DEFAULT ''",
            "seniority": "TEXT DEFAULT ''",
            "department": "TEXT DEFAULT ''",
            "company_linkedin_url": "TEXT DEFAULT ''",
        },
    }
    for table_name, columns in migrations.items():
        existing = {
            row[1] for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        }
        for column_name, column_definition in columns.items():
            if column_name not in existing:
                connection.execute(
                    f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
                )

    # Migrate previously accepted campaign invitees to workspace-wide access.
    # Use View Only during migration so an old campaign-specific permission is never broadened silently.
    active_members = connection.execute(
        "SELECT email, name, created_at FROM team_members WHERE status = 'Active'"
    ).fetchall()
    for member_email, member_name, created_at in active_members:
        connection.execute(
            """
            INSERT OR IGNORE INTO workspace_access
            (id, member_email, member_name, permission, invitation_token,
             invitation_status, invited_by, invited_at, expires_at, accepted_at, revoked_at)
            VALUES (?, ?, ?, 'View Only', NULL, 'Accepted', 'Workspace Admin', ?, NULL, ?, NULL)
            """,
            (str(uuid.uuid4()), member_email, member_name, created_at, created_at),
        )

    # Preserve pending legacy invitations too, but migrate them as View Only because
    # their original permission applied to one campaign rather than the whole workspace.
    legacy_pending = connection.execute(
        """
        SELECT a.member_email, a.member_name, a.invitation_token, a.invitation_status,
               a.invited_by, a.invited_at, a.expires_at
        FROM campaign_access a
        WHERE a.invited_at = (
            SELECT MAX(a2.invited_at) FROM campaign_access a2
            WHERE a2.member_email = a.member_email
        )
        AND a.invitation_status = 'Pending'
        AND NOT EXISTS (
            SELECT 1 FROM workspace_access w WHERE w.member_email = a.member_email
        )
        """
    ).fetchall()
    for row in legacy_pending:
        member_email, member_name, token, invitation_status, invited_by, invited_at, expires_at = row
        connection.execute(
            """
            INSERT OR IGNORE INTO workspace_access
            (id, member_email, member_name, permission, invitation_token,
             invitation_status, invited_by, invited_at, expires_at, accepted_at, revoked_at)
            VALUES (?, ?, ?, 'View Only', ?, ?, ?, ?, ?, NULL, NULL)
            """,
            (
                str(uuid.uuid4()), member_email, member_name,
                token if invitation_status == 'Pending' else None,
                invitation_status, invited_by, invited_at, expires_at,
            ),
        )

    connection.commit()
    return connection


conn = get_connection()


def normalize_country_name(value):
    """Normalize country names and common ISO/name abbreviations to one canonical name."""
    import re

    token = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()
    token = " ".join(token.split())

    # Common country names, short forms, and ISO-2 / ISO-3 codes.
    # All aliases in each group resolve to the first (canonical) name.
    country_alias_groups = {
        "united states": {
            "united states", "united states of america", "us", "usa", "u s",
            "u s a", "america", "us of america", "united states america",
        },
        "united kingdom": {
            "united kingdom", "uk", "u k", "gb", "gbr", "great britain",
            "britain", "england", "scotland", "wales", "northern ireland",
        },
        "india": {"india", "in", "ind"},
        "canada": {"canada", "ca", "can"},
        "australia": {"australia", "au", "aus"},
        "new zealand": {"new zealand", "nz", "nzl"},
        "germany": {"germany", "de", "deu"},
        "france": {"france", "fr", "fra"},
        "italy": {"italy", "it", "ita"},
        "spain": {"spain", "es", "esp"},
        "netherlands": {"netherlands", "the netherlands", "nl", "nld", "holland"},
        "ireland": {"ireland", "ie", "irl"},
        "switzerland": {"switzerland", "ch", "che"},
        "belgium": {"belgium", "be", "bel"},
        "sweden": {"sweden", "se", "swe"},
        "norway": {"norway", "no", "nor"},
        "denmark": {"denmark", "dk", "dnk"},
        "finland": {"finland", "fi", "fin"},
        "poland": {"poland", "pl", "pol"},
        "portugal": {"portugal", "pt", "prt"},
        "austria": {"austria", "at", "aut"},
        "czechia": {"czechia", "czech republic", "cz", "cze"},
        "romania": {"romania", "ro", "rou"},
        "greece": {"greece", "gr", "grc"},
        "turkey": {"turkey", "türkiye", "turkiye", "tr", "tur"},
        "united arab emirates": {
            "united arab emirates", "uae", "u a e", "ae", "are", "emirates",
        },
        "saudi arabia": {"saudi arabia", "ksa", "sa", "sau"},
        "qatar": {"qatar", "qa", "qat"},
        "kuwait": {"kuwait", "kw", "kwt"},
        "bahrain": {"bahrain", "bh", "bhr"},
        "oman": {"oman", "om", "omn"},
        "singapore": {"singapore", "sg", "sgp"},
        "japan": {"japan", "jp", "jpn"},
        "china": {"china", "cn", "chn"},
        "hong kong": {"hong kong", "hk", "hkg"},
        "south korea": {"south korea", "korea republic", "kr", "kor"},
        "taiwan": {"taiwan", "tw", "twn"},
        "malaysia": {"malaysia", "my", "mys"},
        "indonesia": {"indonesia", "id", "idn"},
        "thailand": {"thailand", "th", "tha"},
        "vietnam": {"vietnam", "viet nam", "vn", "vnm"},
        "philippines": {"philippines", "ph", "phl"},
        "pakistan": {"pakistan", "pk", "pak"},
        "bangladesh": {"bangladesh", "bd", "bgd"},
        "sri lanka": {"sri lanka", "lk", "lka"},
        "south africa": {"south africa", "za", "zaf"},
        "nigeria": {"nigeria", "ng", "nga"},
        "kenya": {"kenya", "ke", "ken"},
        "egypt": {"egypt", "eg", "egy"},
        "morocco": {"morocco", "ma", "mar"},
        "ghana": {"ghana", "gh", "gha"},
        "brazil": {"brazil", "br", "bra"},
        "mexico": {"mexico", "mx", "mex"},
        "argentina": {"argentina", "ar", "arg"},
        "chile": {"chile", "cl", "chl"},
        "colombia": {"colombia", "co", "col"},
        "peru": {"peru", "pe", "per"},
        "ukraine": {"ukraine", "ua", "ukr"},
        "russia": {"russia", "ru", "rus"},
        "israel": {"israel", "il", "isr"},
        "luxembourg": {"luxembourg", "lu", "lux"},
    }

    for canonical, aliases in country_alias_groups.items():
        if token in aliases:
            return canonical
    return token


def build_email_sequence_prompt(campaign, lead):
    """Assemble campaign instructions and prospect context for a future AI handoff."""
    instructions = (campaign.get("email_sequence_instructions") or "").strip()
    if not instructions:
        instructions = "Use sensible, concise B2B outbound best practices."

    return f"""Create a personalized 3-email outbound sequence for this prospect.

CAMPAIGN
Campaign name: {campaign.get('name', '')}
Industry: {campaign.get('industry', '')}
Company country: {campaign.get('company_country', '')}
Contact country: {campaign.get('contact_country', '')}
Department: {campaign.get('department', '')}
Seniority: {campaign.get('seniority', '')}
Job level: {campaign.get('job_level', '')}

USER'S EMAIL SEQUENCE INSTRUCTIONS
{instructions}

PROSPECT CONTEXT
Company: {lead.get('company', '')}
Website: {lead.get('website', '')}
Company type: {lead.get('company_type', '')}
Industry: {lead.get('industry', '')}
Current CMS: {lead.get('company_cms', '')}
Contact: {lead.get('contact_name', '')}
Job title: {lead.get('title', '')}
Department: {lead.get('department', '')}
Country: {lead.get('contact_country', '')}
Reason for ICP match: {lead.get('reason', '')}

REQUIREMENTS
- Write 3 connected emails, not 3 unrelated messages.
- Personalize using only the prospect facts supplied above.
- Do not invent company news, results, technology usage, or personal details.
- Keep the writing natural, concise, and relevant to the contact's role.
- Give each email a subject line and body.
- Make follow-up emails add context rather than repeat the first email.
- Follow the user's instructions above wherever they do not conflict with factual accuracy.
- Return drafts for human review; do not send any email.
"""


def load_all_campaigns():
    return pd.read_sql_query("SELECT * FROM campaigns ORDER BY created_at DESC", conn)


def load_campaigns():
    """Show all campaigns to Workspace Admin and all campaigns to accepted workspace members."""
    current_email = st.session_state.get("mock_user_email", "__admin__")
    if current_email == "__admin__":
        return load_all_campaigns()
    return pd.read_sql_query(
        """
        SELECT c.*
        FROM campaigns c
        WHERE EXISTS (
            SELECT 1 FROM workspace_access a
            WHERE a.member_email = ? AND a.invitation_status = 'Accepted'
        )
        ORDER BY c.created_at DESC
        """,
        conn,
        params=(current_email,),
    )


def get_campaign_permission(campaign_id, user_email=None):
    """Return the user's workspace-wide permission for any campaign."""
    user_email = user_email or st.session_state.get("mock_user_email", "__admin__")
    if user_email == "__admin__":
        return "Owner"
    row = conn.execute(
        """
        SELECT permission FROM workspace_access
        WHERE member_email = ? AND invitation_status = 'Accepted'
        """,
        (user_email,),
    ).fetchone()
    return row[0] if row else None


def campaign_label(campaign_id, campaigns):
    match = campaigns[campaigns["id"] == campaign_id]
    return match.iloc[0]["name"] if not match.empty else campaign_id



def on_overview_campaign_checkbox_change(campaign_id, campaign_ids):
    """Keep campaign preview selection single-select while using checkbox controls."""
    clicked_key = f"overview_pick_{campaign_id}"
    if st.session_state.get(clicked_key, False):
        selected_id = campaign_id
    else:
        selected_id = next(
            (
                item for item in campaign_ids
                if st.session_state.get(f"overview_pick_{item}", False)
            ),
            campaign_ids[0] if campaign_ids else None,
        )

    st.session_state["overview_campaign"] = selected_id
    for item in campaign_ids:
        st.session_state[f"overview_pick_{item}"] = item == selected_id

    # If the user changes selection, close any previously opened editor.
    st.session_state["editing_campaign_id"] = None


def get_clay_api_key():
    """Read the Clay Public API key from Streamlit Secrets or an environment variable."""
    secret_value = ""
    try:
        clay_secrets = st.secrets.get("clay", {})
        if hasattr(clay_secrets, "get"):
            secret_value = clay_secrets.get("api_key", "")
    except Exception:
        secret_value = ""
    return str(secret_value or os.getenv("CLAY_API_KEY", "")).strip()


def get_clay_search_result_cap():
    """Return the per-search result cap configured for this Clay workspace.

    Free and Trial workspaces are limited to 50 results per search. Keep 50 as
    the safe default; only raise this value after checking the plan for the
    workspace that owns the API key. This implementation caps one search at 500.
    """
    configured = 50
    try:
        clay_secrets = st.secrets.get("clay", {})
        if hasattr(clay_secrets, "get"):
            configured = clay_secrets.get("max_results_per_search", 50)
    except Exception:
        configured = 50
    try:
        configured = int(configured)
    except (TypeError, ValueError):
        configured = 50
    return max(1, min(configured, 500))


def join_tag_values(values):
    """Store Streamlit tag selections in the existing comma-separated campaign fields."""
    if isinstance(values, (list, tuple, set)):
        cleaned = [str(value).strip() for value in values if str(value).strip()]
    else:
        cleaned = split_clay_values(values)
    return ", ".join(dict.fromkeys(cleaned))


def split_clay_values(query):
    """Split comma/semicolon/newline values without changing their original casing."""
    raw = str(query or "").replace(";", ",").replace("\n", ",")
    values = []
    seen = set()
    for part in raw.split(","):
        value = part.strip()
        if value and value.casefold() not in seen:
            values.append(value)
            seen.add(value.casefold())
    return values


def clay_quote(value):
    """Safely quote a text value for Clay's advanced search query language."""
    value = str(value or "").strip().replace("\\", "\\\\").replace('"', '\\"')
    return f'"{value}"'



@st.cache_data(ttl=3600, show_spinner=False)
def fetch_clay_company_industry_options(api_key):
    """Fetch Clay's live controlled industry values from its company filter schema."""
    response = _clay_api_request(
        "GET",
        "https://api.clay.com/public/v0/search/filters-mode/fields",
        headers={"clay-api-key": api_key},
        params={"source_type": "companies"},
        timeout=30,
    )
    if not response.ok:
        raise RuntimeError(
            f"Could not load Clay industry options (HTTP {response.status_code}): "
            f"{response.text[:500]}"
        )
    payload = response.json()
    fields = payload.get("fields", [])
    industry_field = next(
        (field for field in fields if field.get("name") in ("industries", "industry")),
        None,
    )
    if not industry_field:
        raise RuntimeError("Clay's company-search schema did not return an industry field.")
    options = _field_allowed_values(industry_field)
    options = [str(value).strip() for value in options if str(value).strip()]
    if not options:
        raise RuntimeError("Clay returned no allowed industry values.")
    return options


def normalize_industry_text(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def map_industry_to_clay(user_input, allowed_values):
    """Map one or more industry labels to Clay's live controlled vocabulary."""
    from difflib import get_close_matches

    raw_values = split_clay_values(user_input)
    if not raw_values:
        return [], "No industry filter entered."

    aliases = {
        "finance": ["Financial Services"],
        "financial services": ["Financial Services"],
        "fintech": ["Financial Services"],
        "banking": ["Banking"],
        "insurance": ["Insurance"],
        "accounting": ["Accounting"],
        "healthcare": ["Hospitals and Health Care", "Medical Practices"],
        "health care": ["Hospitals and Health Care", "Medical Practices"],
        "hospital": ["Hospitals and Health Care"],
        "hospitals": ["Hospitals and Health Care"],
        "saas": ["Software Development"],
        "software": ["Software Development"],
        "software company": ["Software Development"],
        "it services": ["IT Services and IT Consulting"],
        "information technology": ["IT Services and IT Consulting"],
    }
    normalized_options = {normalize_industry_text(option): option for option in allowed_values}
    mapped, statuses, unmatched = [], [], []
    for raw in raw_values:
        normalized = normalize_industry_text(raw)
        if normalized in normalized_options:
            mapped.append(normalized_options[normalized])
            statuses.append("Exact Clay category match")
            continue
        alias_hits = [
            normalized_options[normalize_industry_text(target)]
            for target in aliases.get(normalized, [])
            if normalize_industry_text(target) in normalized_options
        ]
        if alias_hits:
            mapped.extend(alias_hits)
            statuses.append("Automatic synonym mapping")
            continue
        close = get_close_matches(normalized, list(normalized_options.keys()), n=1, cutoff=0.88)
        if close:
            mapped.append(normalized_options[close[0]])
            statuses.append(f"Close category match for '{raw}' — please review")
        else:
            unmatched.append(raw)
    if unmatched:
        return [], "No safe Clay category match for: " + ", ".join(unmatched)
    mapped = list(dict.fromkeys(mapped))
    if any(status.startswith("Close category") for status in statuses):
        return mapped, "Close category match — " + "; ".join(statuses)
    if len(set(statuses)) == 1:
        return mapped, statuses[0]
    return mapped, "; ".join(dict.fromkeys(statuses))


def build_clay_company_query(campaign):

    """Build a company-only Clay search from the campaign's company-level filters."""
    clauses = []

    mapped_industry = str(campaign.get("industry_clay_value", "") or "").strip()
    industries = [mapped_industry] if mapped_industry else split_clay_values(campaign.get("industry", ""))
    if industries:
        clauses.append("industry in (" + ", ".join(clay_quote(v) for v in industries) + ")")

    countries = split_clay_values(campaign.get("company_country", ""))
    if countries:
        canonical_countries = [normalize_country_name(v).title() for v in countries]
        country_clause = " or ".join(
            f"country_name = {clay_quote(country)}" for country in canonical_countries
        )
        clauses.append(f"locations.any({country_clause})")

    states = split_clay_values(campaign.get("company_state", ""))
    if states:
        clauses.append("state_name in (" + ", ".join(clay_quote(v) for v in states) + ")")
    cities = split_clay_values(campaign.get("company_city", ""))
    if cities:
        clauses.append("city_name in (" + ", ".join(clay_quote(v) for v in cities) + ")")

    if not clauses:
        raise ValueError(
            "Add at least one company-level filter (Industry, Company Country, or Current CMS) before searching Clay."
        )

    return "select from companies where " + " and ".join(clauses)


def _clay_api_request(method, url, headers, json_body=None, params=None, timeout=40, attempts=3):
    """Call Clay with bounded retries for transient network, rate-limit and server errors."""
    retry_statuses = {408, 425, 429, 500, 502, 503, 504}
    last_error = None
    for attempt in range(attempts):
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=json_body,
                params=params,
                timeout=timeout,
            )
            if response.status_code not in retry_statuses or attempt == attempts - 1:
                return response
            retry_after = response.headers.get("Retry-After", "")
            try:
                wait_seconds = min(8.0, max(1.0, float(retry_after))) if retry_after else min(8.0, 2 ** attempt)
            except (TypeError, ValueError):
                wait_seconds = min(8.0, 2 ** attempt)
            time.sleep(wait_seconds)
        except requests.RequestException as exc:
            last_error = exc
            if attempt == attempts - 1:
                raise RuntimeError(f"Clay request failed after {attempts} attempts: {exc}") from exc
            time.sleep(min(8.0, 2 ** attempt))
    if last_error:
        raise RuntimeError(f"Clay request failed: {last_error}") from last_error
    raise RuntimeError("Clay request failed without a response.")


def _clay_json(response, label):
    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError(f"Clay {label} returned an invalid JSON response (HTTP {response.status_code}).") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"Clay {label} returned an unexpected response format.")
    return payload


def _stable_company_key(row):
    return str(
        row.get("clay_company_id") or row.get("id") or row.get("domain")
        or row.get("linkedin_url") or row.get("company_linkedin_url") or row.get("name") or ""
    ).strip().casefold()


def _stable_person_key(row):
    person = _parse_clay_person_row(row)
    return str(
        person.get("clay_profile_id") or person.get("linkedin_url")
        or "|".join([
            person.get("full_name", "").casefold(),
            person.get("company_domain", "").casefold(),
            person.get("job_title", "").casefold(),
        ])
    ).strip()


def collect_clay_search_results(api_key, search_id, entity_type, max_results=50, page_size=20):
    """Collect at most Clay's 50-result Free/Trial per-search allowance.

    Track requested capacity separately from unique rows: Clay meters the number
    of results requested/returned for a search, while local deduplication can
    reduce the number of rows retained. Never request a page that would take
    this search beyond 50 results on a Free/Trial workspace.
    """
    base_url = "https://api.clay.com/public/v0"
    headers = {"clay-api-key": api_key, "Content-Type": "application/json"}
    rows, seen = [], set()
    has_more = False
    page_count = 0
    requested_total = 0
    # Safe default is 50. A higher cap is configurable only after the workspace
    # plan has been checked in Clay. Clay allows at most 500 results per request.
    search_cap = min(max(1, int(max_results)), 500)
    page_size = min(max(1, int(page_size)), 500)

    while requested_total < search_cap:
        page_limit = min(page_size, search_cap - requested_total)
        response = _clay_api_request(
            "POST",
            f"{base_url}/search/filters-mode/{search_id}/run",
            headers=headers,
            json_body={"limit": page_limit},
            timeout=60,
        )
        if not response.ok:
            error_text = str(getattr(response, "text", "") or "")[:1000]
            # If Clay unexpectedly refuses a later page at the per-search cap,
            # preserve already fetched records as a partial result instead of
            # throwing them away. Other 402 errors (e.g. period quota) remain fatal.
            if (
                response.status_code == 402
                and "single search" in error_text.casefold()
                and rows
            ):
                has_more = True
                break
            raise RuntimeError(
                f"Clay {entity_type} results request failed (HTTP {response.status_code}): {error_text}"
            )
        payload = _clay_json(response, f"{entity_type} results")
        page_rows = payload.get("data", [])
        if not isinstance(page_rows, list):
            raise RuntimeError(f"Clay {entity_type} results response did not contain a data list.")
        page_count += 1
        requested_total += page_limit
        has_more = bool(payload.get("has_more", False))
        new_rows = []
        for row in page_rows:
            if not isinstance(row, dict):
                continue
            stable_key = _stable_company_key(row) if entity_type == "company" else _stable_person_key(row)
            if not stable_key:
                # Keep unidentified rows once; Clay should normally return an ID/domain/profile URL.
                stable_key = hashlib.sha256(json.dumps(row, sort_keys=True, default=str).encode("utf-8")).hexdigest()
            if stable_key in seen:
                continue
            seen.add(stable_key)
            new_rows.append(row)
        rows.extend(new_rows)

        # Stop safely if Clay repeats a page. This avoids an accidental infinite loop.
        if not page_rows or not new_rows or not has_more:
            break

    # Reaching the local per-search cap while Clay still has more matches is an
    # expected partial result, not a failed search.
    if requested_total >= search_cap and has_more:
        has_more = True
    return rows[:search_cap], has_more, page_count


def fetch_clay_company_filter_schema(api_key):
    response = _clay_api_request(
        "GET",
        "https://api.clay.com/public/v0/search/filters-mode/fields",
        headers={"clay-api-key": api_key},
        params={"source_type": "companies"},
        timeout=30,
    )
    if not response.ok:
        raise RuntimeError(
            f"Could not read Clay company-search filter schema (HTTP {response.status_code}): {response.text[:700]}"
        )
    payload = _clay_json(response, "company filter schema")
    fields = payload.get("fields", [])
    schema = {field.get("name"): field for field in fields if isinstance(field, dict) and field.get("name")}
    if not schema:
        raise RuntimeError("Clay returned an empty company-search filter schema.")
    return schema


def run_clay_company_search(campaign, campaign_id, api_key):
    """Search companies in Clay, persist results locally, and return normalized records."""
    campaign = campaign_as_dict(campaign_id) or campaign
    schema = fetch_clay_company_filter_schema(api_key)
    filters = {}

    mapped_industry = str(campaign.get("industry_clay_value", "") or "").strip()
    industry_values = split_clay_values(mapped_industry) if mapped_industry else split_clay_values(campaign.get("industry", ""))
    if industry_values:
        industry_field = schema.get("industries") or schema.get("industry")
        if not industry_field:
            raise RuntimeError("Clay's live company-search schema does not expose an industries filter.")
        filters["industries"] = _clay_filter_values(industry_field, industry_values, "Industry")

    country_values = [normalize_country_name(value).title() for value in split_clay_values(campaign.get("company_country", ""))]
    if country_values:
        if "country_names" not in schema:
            raise RuntimeError("Clay's live company-search schema does not expose country_names.")
        filters["country_names"] = country_values
        if "location_headquarters_only" in schema:
            filters["location_headquarters_only"] = True

    state_values = split_clay_values(campaign.get("company_state", ""))
    if state_values:
        state_field_name = next((name for name in ("location_states_include", "state_names", "states", "location_states", "location_state_names") if name in schema), None)
        if not state_field_name:
            raise RuntimeError("Clay's current company-search schema does not expose a state filter. The dashboard stopped rather than ignoring your selected state(s).")
        filters[state_field_name] = _clay_filter_values(schema[state_field_name], state_values, "Company State")

    city_values = split_clay_values(campaign.get("company_city", ""))
    if city_values:
        city_field_name = next((name for name in ("location_cities_include", "city_names", "cities", "location_cities", "location_city_names") if name in schema), None)
        if not city_field_name:
            raise RuntimeError("Clay's current company-search schema does not expose a city filter. The dashboard stopped rather than ignoring your selected city/cities.")
        filters[city_field_name] = _clay_filter_values(schema[city_field_name], city_values, "Company City")

    if (state_values or city_values) and "location_headquarters_only" in schema:
        filters["location_headquarters_only"] = True

    company_size_labels = split_clay_values(campaign.get("company_size", ""))
    if company_size_labels:
        size_field = schema.get("sizes") or schema.get("company_sizes") or schema.get("company_size")
        if not size_field:
            raise RuntimeError("Clay's live company-search schema does not expose a company size filter.")
        unknown_size_labels = [label for label in company_size_labels if label not in COMPANY_SIZE_CLAY_VALUES]
        if unknown_size_labels:
            raise ValueError("Unsupported Company Size option(s): " + ", ".join(unknown_size_labels))
        # Clay's `sizes` API filter expects bucket codes such as 2, 10, 50, 500,
        # 1000, 5000, and 10000, not the display labels shown in its UI.
        company_size_codes = [COMPANY_SIZE_CLAY_VALUES[label] for label in company_size_labels]
        filters["sizes"] = _clay_filter_values(size_field, company_size_codes, "Company Size")

    # Current CMS is intentionally not used as a search filter in this phase.
    # The sales team will add Clay's website-technology/CMS enrichment after reviewing the sourced list.
    validation_note = (
        "Current CMS is reserved for manual enrichment in the Clay workbook after review."
        if split_clay_values(campaign.get("current_cms", "")) else ""
    )
    if not filters:
        raise ValueError("Add at least one company-search filter (Industry, Company Country, or Company Size). Current CMS is enriched later in Clay.")

    headers = {"clay-api-key": api_key, "Content-Type": "application/json"}
    base_url = "https://api.clay.com/public/v0"
    created_at = datetime.now().isoformat(timespec="seconds")
    run_id = str(uuid.uuid4())
    clay_search_id = ""
    query_text = json.dumps(
        {"source_type": "companies", "filters": filters, "note": validation_note},
        ensure_ascii=False,
        indent=2,
    )
    try:
        create_response = _clay_api_request(
            "POST", f"{base_url}/search/filters-mode", headers=headers,
            json_body={"source_type": "companies", "filters": filters}, timeout=40,
        )
        if not create_response.ok:
            raise RuntimeError(
                f"Clay company search creation failed (HTTP {create_response.status_code}): {create_response.text[:1000]}"
            )
        create_payload = _clay_json(create_response, "company search creation")
        clay_search_id = str(create_payload.get("search_id", "") or "")
        if not clay_search_id:
            raise RuntimeError("Clay did not return a company search ID.")

        rows, has_more, page_count = collect_clay_search_results(
            api_key, clay_search_id, "company", max_results=get_clay_search_result_cap(), page_size=20
        )
        conn.execute(
            """INSERT INTO clay_search_runs
               (id, campaign_id, clay_search_id, query_text, result_count, has_more, status, error_message, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (run_id, campaign_id, clay_search_id, query_text, len(rows), int(has_more), "Complete", "", created_at),
        )

        export_records = []
        company_linkedin_urls, company_domains = [], []
        for row in rows:
            location_value = row.get("location") or {}
            if isinstance(location_value, dict):
                location_text = location_value.get("name") or location_value.get("display_name") or ""
                country_value = location_value.get("country") or location_value.get("country_name") or ""
            else:
                location_text = str(location_value or "")
                country_value = row.get("country", "")
            country_value = row.get("country") or country_value
            company_id_value = str(row.get("clay_company_id", row.get("id", "")) or "")
            company_name = str(row.get("name", row.get("company_name", "")) or "")
            domain = str(row.get("domain", row.get("website", "")) or "").strip()
            linkedin_url = str(
                row.get("linkedin_url") or row.get("company_linkedin_url")
                or row.get("linkedin_url_company") or row.get("social_url") or ""
            ).strip()
            result_id = str(uuid.uuid4())
            conn.execute(
                """INSERT INTO clay_company_results
                   (id, campaign_id, search_run_id, clay_company_id, company_name, domain, industry,
                    country, employee_count, company_type, location, description, linkedin_url,
                    annual_revenue, raw_json, created_at, company_linkedin_url)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    result_id, campaign_id, run_id, company_id_value, company_name, domain,
                    str(row.get("industry", "") or ""), str(country_value or ""),
                    str(row.get("size", row.get("estimated_employee_count", row.get("employee_count", ""))) or ""),
                    str(row.get("type", row.get("company_type", "")) or ""), str(location_text or ""),
                    str(row.get("description", "") or ""), linkedin_url,
                    str(row.get("annual_revenue", "") or ""), json.dumps(row, ensure_ascii=False),
                    created_at, linkedin_url,
                ),
            )
            if linkedin_url:
                company_linkedin_urls.append(linkedin_url)
            if domain:
                company_domains.append(domain.lower())
            export_records.append({
                "campaign_id": campaign_id,
                "campaign_name": str(campaign.get("name", "") or ""),
                "clay_company_id": company_id_value,
                "company_name": company_name,
                "domain": domain,
                "industry": str(row.get("industry", "") or ""),
                "country": str(country_value or ""),
                "employee_count": str(row.get("size", row.get("estimated_employee_count", row.get("employee_count", ""))) or ""),
                "company_type": str(row.get("type", row.get("company_type", "")) or ""),
                "location": str(location_text or ""),
                "description": str(row.get("description", "") or ""),
                "company_linkedin_url": linkedin_url,
                "annual_revenue": str(row.get("annual_revenue", "") or ""),
                "clay_search_id": clay_search_id,
                "search_run_id": run_id,
                "raw_clay_data": json.dumps(row, ensure_ascii=False),
            })

        conn.execute(
            "UPDATE campaigns SET status = ? WHERE id = ?",
            ("Company Search Complete" if rows else "No Companies Found", campaign_id),
        )
        conn.commit()

        company_linkedin_urls = list(dict.fromkeys(company_linkedin_urls))
        company_domains = list(dict.fromkeys(company_domains))
        rows_without_linkedin = [record for record in export_records if not record.get("company_linkedin_url")]
        fallback_domains = list(dict.fromkeys(
            str(record.get("domain", "")).strip().lower()
            for record in rows_without_linkedin if record.get("domain")
        ))
        company_identifiers = list(dict.fromkeys(company_linkedin_urls + fallback_domains))
        company_match_identifiers = list(dict.fromkeys(company_linkedin_urls + company_domains))
        return {
            "run_id": run_id, "search_id": clay_search_id, "query": query_text,
            "count": len(rows), "has_more": has_more, "page_count": page_count,
            "company_domains": company_domains, "company_linkedin_urls": company_linkedin_urls,
            "company_identifiers": company_identifiers,
            "company_match_identifiers": company_match_identifiers,
            "records": export_records, "validation_note": validation_note,
        }
    except Exception as exc:
        existing_run = conn.execute("SELECT 1 FROM clay_search_runs WHERE id = ?", (run_id,)).fetchone()
        if existing_run:
            conn.execute(
                "UPDATE clay_search_runs SET status = ?, error_message = ? WHERE id = ?",
                ("Failed", str(exc)[:1000], run_id),
            )
        else:
            conn.execute(
                """INSERT INTO clay_search_runs
                   (id, campaign_id, clay_search_id, query_text, result_count, has_more, status, error_message, created_at)
                   VALUES (?, ?, ?, ?, 0, 0, ?, ?, ?)""",
                (run_id, campaign_id, clay_search_id, query_text, "Failed", str(exc)[:1000], created_at),
            )
        conn.execute("UPDATE campaigns SET status = ? WHERE id = ?", ("Company Search Failed", campaign_id))
        conn.commit()
        raise

def fetch_clay_people_filter_schema(api_key):
    """Read Clay's live people-search fields before sending controlled filters."""
    response = _clay_api_request(
        "GET",
        "https://api.clay.com/public/v0/search/filters-mode/fields",
        headers={"clay-api-key": api_key},
        params={"source_type": "people"},
        timeout=30,
    )
    if not response.ok:
        raise RuntimeError(
            f"Could not read Clay people-search filter schema (HTTP {response.status_code}): "
            f"{response.text[:700]}"
        )
    payload = response.json()
    fields = payload.get("fields", [])
    return {field.get("name"): field for field in fields if field.get("name")}


def _field_allowed_values(schema_field):
    """Return normalized Clay allowed-values strings, including object-shaped schema values."""
    allowed = (schema_field or {}).get("allowed_values") or (schema_field or {}).get("allowedValues") or []
    values = []
    for item in allowed:
        if isinstance(item, dict):
            item = item.get("value") or item.get("name") or item.get("label") or item.get("id")
        if item not in (None, ""):
            values.append(str(item).strip())
    return list(dict.fromkeys(value for value in values if value))


def _clay_filter_values(schema_field, values, label):
    """Validate/map controlled Clay vocabulary; pass free-text values through unchanged."""
    values = [str(value).strip() for value in values if str(value).strip()]
    allowed_strings = _field_allowed_values(schema_field)
    if not allowed_strings:
        return values
    allowed_lookup = {value.casefold(): value for value in allowed_strings}
    mapped, missing = [], []
    for value in values:
        canonical = allowed_lookup.get(value.casefold())
        if canonical:
            if canonical not in mapped:
                mapped.append(canonical)
        else:
            missing.append(value)
    if missing:
        examples = ", ".join(allowed_strings[:15])
        raise ValueError(
            f"Your {label} value(s) ({', '.join(missing)}) do not match Clay's current options. "
            f"Supported examples: {examples or 'not provided by Clay'}"
        )
    return mapped


def _expand_seniority_for_job_level(campaign):
    """Map dashboard seniority labels to Clay's current seniority enum values."""
    selected_labels = split_clay_values(campaign.get("seniority", ""))
    if not selected_labels:
        return []

    label_to_values = {
        "founder": ["founder"],
        "owner": ["owner"],
        "board member": ["board-member"],
        "board-member": ["board-member"],
        "partner": ["partner"],
        "c-suite": ["c-suite"],
        "vp": ["vp"],
        "director": ["director"],
        "head": ["head"],
        "manager": ["manager"],
        "senior": ["senior"],
        "mid-level": ["mid-level"],
        "mid level": ["mid-level"],
        "entry": ["entry"],
        "intern / in-training": ["intern"],
        "intern/in-training": ["intern"],
        "intern": ["intern"],
        "unknown": ["unknown"],
        # Backward compatibility with campaigns created before the expanded list.
        "owner / founder": ["owner", "founder"],
    }

    selected_values = []
    for label in selected_labels:
        key = label.casefold().strip()
        mapped = label_to_values.get(key)
        if not mapped:
            raise ValueError(f"Unsupported seniority selection: {label}")
        selected_values.extend(mapped)
    selected_values = list(dict.fromkeys(selected_values))

    # Current Create/Edit forms use exact selected levels. Keep the previous
    # Above/Below behaviour only for legacy campaign records that still carry it.
    level = str(campaign.get("job_level", "Exact") or "Exact").strip().casefold()
    if level in ("", "any", "exact", "equal"):
        return [] if level == "any" else selected_values

    rank_groups = [
        (1, ["intern"]), (2, ["entry"]), (3, ["mid-level"]), (4, ["senior"]),
        (5, ["manager"]), (6, ["head"]), (7, ["director"]), (8, ["vp"]),
        (9, ["c-suite"]), (10, ["partner"]), (11, ["owner", "founder"]),
        (12, ["board-member"]), (13, ["unknown"]),
    ]
    selected_ranks = [rank for rank, values in rank_groups if set(values).intersection(selected_values)]
    if not selected_ranks:
        return selected_values
    if level == "above":
        threshold = min(selected_ranks)
        return [value for rank, values in rank_groups if rank >= threshold for value in values]
    if level == "below":
        threshold = max(selected_ranks)
        return [value for rank, values in rank_groups if rank <= threshold for value in values]
    return selected_values


def build_clay_people_filters(campaign, company_identifiers, people_schema):
    """Build Clay people filters using the live schema and target-company scope."""
    if not company_identifiers:
        raise ValueError("No company LinkedIn URLs or domains were returned, so contact search cannot be safely scoped.")

    filters = {}
    if "company_identifier" not in people_schema:
        raise RuntimeError(
            "Clay's live people-search schema does not expose company_identifier. "
            "The dashboard stopped rather than running an unscoped contact search."
        )
    filters["company_identifier"] = list(dict.fromkeys(str(value).strip() for value in company_identifiers if str(value).strip()))

    contact_countries = [
        normalize_country_name(value).title()
        for value in split_clay_values(campaign.get("contact_country", ""))
    ]
    if contact_countries:
        field = people_schema.get("location_countries_include")
        if not field:
            raise RuntimeError("Clay's current people-search schema does not expose location_countries_include.")
        filters["location_countries_include"] = _clay_filter_values(field, contact_countries, "Contact Country")

    title_values = split_clay_values(campaign.get("target_titles", ""))
    title_values = [value for value in title_values if value.casefold() not in ("any", "all")]
    if title_values:
        field = people_schema.get("job_title_keywords")
        if not field:
            raise RuntimeError("Clay's current people-search schema does not expose job_title_keywords.")
        filters["job_title_keywords"] = title_values
        # Smart matching is preferable to strict substring matching because it covers common title variations.
        mode_field = people_schema.get("job_title_mode")
        if mode_field:
            allowed_modes = [value.casefold() for value in _field_allowed_values(mode_field)]
            if not allowed_modes or "smart" in allowed_modes:
                filters["job_title_mode"] = "smart"
            elif "contain" in allowed_modes:
                filters["job_title_mode"] = "contain"

    seniority_values = _expand_seniority_for_job_level(campaign)
    if seniority_values:
        field = people_schema.get("job_title_seniority_levels_v2")
        if not field:
            raise RuntimeError("Clay's current people-search schema does not expose job_title_seniority_levels_v2.")
        filters["job_title_seniority_levels_v2"] = _clay_filter_values(
            field, seniority_values, "Seniority / Job Level"
        )

    department_values = [
        value for value in split_clay_values(campaign.get("department", ""))
        if value.casefold() not in ("any", "all")
    ]
    if department_values:
        field = people_schema.get("job_functions")
        if not field:
            raise RuntimeError(
                "Clay's current people-search schema does not expose job_functions, "
                "so the requested Department filter cannot be safely applied."
            )
        filters["job_functions"] = _clay_filter_values(field, department_values, "Department")

    return filters


def _first_nonempty(mapping, *keys):
    if not isinstance(mapping, dict):
        return ""
    for key in keys:
        value = mapping.get(key)
        if value not in (None, "", [], {}):
            return value
    return ""


def _truthy_current_marker(value):
    if value is True or value == 1:
        return True
    return str(value or "").strip().casefold() in ("true", "yes", "1", "current", "present")


def _extract_current_experience(row):
    """Return the best-supported current role from Clay's profile payload."""
    # Clay may provide a dedicated current_experience object alongside a full
    # experiences list. Prefer that explicit object instead of ignoring it.
    current_exp = _first_nonempty(row, "current_experience", "currentExperience")
    if isinstance(current_exp, dict):
        return current_exp
    if isinstance(current_exp, list):
        current_exp = next((item for item in current_exp if isinstance(item, dict)), None)
        if current_exp:
            return current_exp

    experiences = _first_nonempty(
        row, "experiences", "experience", "employment_history", "employmentHistory"
    )
    if isinstance(experiences, dict):
        experiences = [experiences]
    if not isinstance(experiences, list):
        return {}
    valid_experiences = [item for item in experiences if isinstance(item, dict)]

    current = next(
        (
            item for item in valid_experiences
            if any(_truthy_current_marker(item.get(key)) for key in (
                "is_current", "isCurrent", "current", "is_current_role", "isCurrentRole"
            ))
        ),
        None,
    )
    if current:
        return current

    # Some Clay payloads omit the boolean current flag but explicitly include
    # an empty end-date field or a Present/Current end date. Treat that as a
    # current-role signal; do not infer current status merely from list order.
    end_date_keys = ("end_date", "endDate", "ends_at", "endsAt", "to", "ended_at", "endedAt")
    for item in valid_experiences:
        present_end_key = next((key for key in end_date_keys if key in item), None)
        if present_end_key is None:
            continue
        end_value = item.get(present_end_key)
        if end_value in (None, "", {}, []) or str(end_value).strip().casefold() in ("present", "current"):
            return item
    return {}


def _extract_person_job_title(row, experience):
    """Choose the current role title before generic profile headlines."""
    candidates = [
        ("current_experience", _first_nonempty(experience, "title", "job_title", "jobTitle", "position", "role")),
        ("current_job_title", _first_nonempty(row, "current_job_title", "currentJobTitle")),
        ("job_title", _first_nonempty(row, "job_title", "jobTitle")),
        ("title", _first_nonempty(row, "title")),
        ("headline", _first_nonempty(row, "headline")),
    ]
    normalized = []
    seen = set()
    for source, value in candidates:
        if value in (None, "", [], {}):
            continue
        text_value = str(value).strip()
        if not text_value or text_value.casefold() in seen:
            continue
        seen.add(text_value.casefold())
        normalized.append((source, text_value))
    if normalized:
        return normalized[0][1], normalized[0][0], [value for _, value in normalized]
    return "", "unavailable", []


def _parse_clay_person_row(row):
    """Normalize Clay's returned profile fields across snake_case/camelCase shapes."""
    experience = _extract_current_experience(row)
    company = _first_nonempty(
        experience, "company", "organization", "current_company", "currentCompany"
    )
    if not isinstance(company, dict):
        company = {}
    top_company = _first_nonempty(row, "company", "current_company", "currentCompany", "employer")
    if not isinstance(top_company, dict):
        top_company = {}
    location = _first_nonempty(row, "location", "person_location", "personLocation")
    if isinstance(location, dict):
        location_text = _first_nonempty(location, "name", "display_name", "displayName", "formatted")
        location_country = _first_nonempty(location, "country", "country_name", "countryName")
    else:
        location_text = str(location or "")
        location_country = _first_nonempty(row, "location_country", "locationCountry", "country")
    if not location_country and location_text:
        location_lower = location_text.casefold()
        country_candidates = [
            "United States", "United Kingdom", "Canada", "Australia",
            "India", "Germany", "France", "Japan", "Singapore",
        ]
        location_country = next(
            (country for country in country_candidates if country.casefold() in location_lower),
            "",
        )

    full_name = _first_nonempty(row, "full_name", "fullName", "name", "display_name", "displayName")
    first_name = _first_nonempty(row, "first_name", "firstName")
    last_name = _first_nonempty(row, "last_name", "lastName")
    if full_name and not first_name:
        parts = str(full_name).strip().split()
        first_name = parts[0] if parts else ""
        last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

    seniority = _first_nonempty(row, "seniorities", "seniority", "job_title_seniority", "jobTitleSeniority")
    if isinstance(seniority, list):
        seniority = ", ".join(str(value) for value in seniority)

    department = _first_nonempty(row, "job_functions", "jobFunctions", "department", "function")
    if isinstance(department, list):
        department = ", ".join(str(value) for value in department)

    company_name = (
        _first_nonempty(row, "company_name", "companyName", "current_company_name", "currentCompanyName")
        or _first_nonempty(company, "name", "company_name", "companyName")
        or _first_nonempty(top_company, "name", "company_name", "companyName")
    )
    company_domain = (
        _first_nonempty(row, "company_domain", "companyDomain", "current_company_domain", "currentCompanyDomain")
        or _first_nonempty(experience, "company_domain", "companyDomain")
        or _first_nonempty(company, "domain", "website", "company_domain", "companyDomain")
        or _first_nonempty(top_company, "domain", "website", "company_domain", "companyDomain")
    )
    company_linkedin_url = (
        _first_nonempty(
            row, "company_linkedin_url", "companyLinkedinUrl", "current_company_linkedin_url",
            "currentCompanyLinkedinUrl", "company_social_url", "companySocialUrl",
        )
        or _first_nonempty(experience, "company_linkedin_url", "companyLinkedinUrl", "company_social_url")
        or _first_nonempty(company, "linkedin_url", "linkedinUrl", "social_url", "profile_url", "url")
        or _first_nonempty(top_company, "linkedin_url", "linkedinUrl", "social_url", "profile_url", "url")
    )
    job_title, job_title_source, title_candidates = _extract_person_job_title(row, experience)

    return {
        "clay_profile_id": str(_first_nonempty(row, "clay_profile_id", "clayProfileId", "id", "profile_id", "profileId") or ""),
        "full_name": str(full_name or ""),
        "first_name": str(first_name or ""),
        "last_name": str(last_name or ""),
        "job_title": job_title,
        "job_title_source": job_title_source,
        "title_candidates": title_candidates,
        "has_current_experience": bool(experience),
        "seniority": str(seniority or ""),
        "department": str(department or ""),
        "location": str(location_text or ""),
        "location_country": str(location_country or ""),
        "company_name": str(company_name or ""),
        "company_domain": str(company_domain or ""),
        "company_linkedin_url": str(company_linkedin_url or ""),
        "linkedin_url": str(_first_nonempty(row, "linkedin_url", "linkedinUrl", "profile_url", "profileUrl", "linkedInUrl") or ""),
    }


def _normalize_company_match_identifier(value):
    """Normalize a company domain or LinkedIn company URL for safe comparison."""
    raw = str(value or "").strip()
    if not raw:
        return ""
    candidate = raw if "://" in raw else "https://" + raw
    parsed = urlparse(candidate)
    host = (parsed.netloc or "").casefold().removeprefix("www.")
    path = (parsed.path or "").rstrip("/").casefold()
    if "linkedin.com" in host:
        return host + path
    return host or raw.casefold().removeprefix("www.").rstrip("/")


def run_clay_people_search(campaign, campaign_id, api_key, company_identifiers, company_match_identifiers=None):
    """Search people at the companies returned by the preceding company search."""
    campaign = campaign_as_dict(campaign_id) or campaign
    created_at = datetime.now().isoformat(timespec="seconds")
    run_id = str(uuid.uuid4())
    clay_search_id = ""
    query_text = "{}"
    try:
        # Schema retrieval and filter construction are inside try so every failure is logged.
        people_schema = fetch_clay_people_filter_schema(api_key)
        filters = build_clay_people_filters(campaign, company_identifiers, people_schema)
        query_text = json.dumps({"source_type": "people", "filters": filters}, ensure_ascii=False, indent=2)
        headers = {"clay-api-key": api_key, "Content-Type": "application/json"}
        base_url = "https://api.clay.com/public/v0"

        create_response = _clay_api_request(
            "POST", f"{base_url}/search/filters-mode", headers=headers,
            json_body={"source_type": "people", "filters": filters}, timeout=40,
        )
        if not create_response.ok:
            raise RuntimeError(
                f"Clay contact search creation failed (HTTP {create_response.status_code}): {create_response.text[:1000]}"
            )
        create_payload = _clay_json(create_response, "contact search creation")
        clay_search_id = str(create_payload.get("search_id", "") or "")
        if not clay_search_id:
            raise RuntimeError("Clay did not return a contact search ID.")

        raw_rows, has_more, page_count = collect_clay_search_results(
            api_key, clay_search_id, "people", max_results=get_clay_search_result_cap(), page_size=20
        )
        match_values = company_match_identifiers or company_identifiers
        approved_ids = {
            _normalize_company_match_identifier(value)
            for value in match_values if _normalize_company_match_identifier(value)
        }

        rows, rejected_employer_count, unverified_employer_count = [], 0, 0
        profiles_with_title = 0
        profiles_with_current_experience = 0
        for raw_row in raw_rows:
            person = _parse_clay_person_row(raw_row)
            profiles_with_title += int(bool(person["job_title"]))
            profiles_with_current_experience += int(person["has_current_experience"])
            current_ids = {
                _normalize_company_match_identifier(person["company_linkedin_url"]),
                _normalize_company_match_identifier(person["company_domain"]),
            }
            current_ids.discard("")
            if current_ids.intersection(approved_ids):
                rows.append((raw_row, person))
            elif current_ids:
                rejected_employer_count += 1
                continue
            else:
                # Clay's request was already scoped to target companies. Keep rows missing an employer URL,
                # but make the count visible so sales can spot-check the results.
                unverified_employer_count += 1
                rows.append((raw_row, person))

        debug_data = {
            "raw_profile_count": len(raw_rows),
            "retained_profile_count": len(rows),
            "employer_mismatch_rejected_count": rejected_employer_count,
            "retained_without_employer_identifier_count": unverified_employer_count,
            "profiles_with_parsed_title_count": profiles_with_title,
            "profiles_with_current_experience_count": profiles_with_current_experience,
            "title_filtering": "Applied by Clay Search API; no second strict substring filter applied locally.",
        }
        summary = (
            f"Clay returned {len(raw_rows)} profiles across {page_count} page(s); retained {len(rows)}; "
            f"excluded {rejected_employer_count} with a conflicting employer; "
            f"retained {unverified_employer_count} without employer identifiers under the company-scoped search."
        )
        conn.execute(
            """INSERT INTO clay_people_search_runs
               (id, campaign_id, clay_search_id, query_text, result_count, has_more, status, error_message, debug_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (run_id, campaign_id, clay_search_id, query_text, len(rows), int(has_more), "Complete",
             summary, json.dumps(debug_data, ensure_ascii=False), created_at),
        )

        export_records = []
        for raw_row, person in rows:
            conn.execute(
                """INSERT INTO clay_people_results
                   (id, campaign_id, search_run_id, clay_profile_id, full_name, first_name, last_name,
                    job_title, seniority, department, location, location_country, company_name,
                    company_domain, company_linkedin_url, linkedin_url, raw_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(uuid.uuid4()), campaign_id, run_id, person["clay_profile_id"],
                    person["full_name"], person["first_name"], person["last_name"], person["job_title"],
                    person["seniority"], person["department"], person["location"], person["location_country"],
                    person["company_name"], person["company_domain"], person["company_linkedin_url"],
                    person["linkedin_url"], json.dumps(raw_row, ensure_ascii=False), created_at,
                ),
            )
            export_records.append({
                "campaign_id": campaign_id,
                "campaign_name": str(campaign.get("name", "") or ""),
                "clay_profile_id": person["clay_profile_id"],
                "full_name": person["full_name"],
                "first_name": person["first_name"],
                "last_name": person["last_name"],
                "job_title": person["job_title"],
                "seniority": person["seniority"],
                "department": person["department"],
                "location": person["location"],
                "location_country": person["location_country"],
                "company_name": person["company_name"],
                "company_domain": person["company_domain"],
                "company_linkedin_url": person["company_linkedin_url"],
                "linkedin_url": person["linkedin_url"],
                "clay_search_id": clay_search_id,
                "search_run_id": run_id,
                "raw_clay_data": json.dumps(raw_row, ensure_ascii=False),
            })
        conn.commit()
        return {
            "run_id": run_id, "search_id": clay_search_id, "query": query_text,
            "count": len(rows), "raw_count": len(raw_rows),
            "rejected_count": rejected_employer_count,
            "unverified_employer_count": unverified_employer_count,
            "has_more": has_more, "page_count": page_count, "records": export_records,
        }
    except Exception as exc:
        conn.execute(
            """INSERT INTO clay_people_search_runs
               (id, campaign_id, clay_search_id, query_text, result_count, has_more, status, error_message, debug_json, created_at)
               VALUES (?, ?, ?, ?, 0, 0, ?, ?, ?, ?)""",
            (run_id, campaign_id, clay_search_id, query_text, "Failed", str(exc)[:1000], "{}", created_at),
        )
        conn.execute("UPDATE campaigns SET status = ? WHERE id = ?", ("Contact Search Failed", campaign_id))
        conn.commit()
        raise


def is_valid_https_url(value):
    value = str(value or "").strip()
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _webhook_idempotency_key(campaign_id, entity_type, record):
    if entity_type == "company":
        stable_value = record.get("clay_company_id") or record.get("domain") or record.get("company_linkedin_url") or record.get("company_name")
    else:
        stable_value = record.get("clay_profile_id") or record.get("linkedin_url") or "|".join([
            str(record.get("full_name", "")), str(record.get("company_domain", "")), str(record.get("job_title", ""))
        ])
    source = f"{campaign_id}|{entity_type}|{stable_value or json.dumps(record, sort_keys=True, default=str)}"
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def send_records_to_clay_webhook(webhook_url, auth_token, campaign_id, entity_type, records):
    """Send normalized search results into an existing Clay webhook table with retry-safe keys."""
    if not records:
        return {"sent": 0, "failed": 0}
    webhook_url = str(webhook_url or "").strip()
    parsed = urlparse(webhook_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"The Clay {entity_type} webhook URL must be a valid HTTPS URL.")

    sent, failures = 0, []
    for index, record in enumerate(records, start=1):
        headers = {
            "Content-Type": "application/json",
            "x-clay-webhook-idempotency-key": _webhook_idempotency_key(campaign_id, entity_type, record),
        }
        if str(auth_token or "").strip():
            headers["x-clay-webhook-auth"] = str(auth_token).strip()
        last_error = ""
        for attempt in range(3):
            try:
                response = requests.post(webhook_url, headers=headers, json=record, timeout=20)
                if 200 <= response.status_code < 300:
                    sent += 1
                    last_error = ""
                    break
                last_error = f"HTTP {response.status_code}: {response.text[:350]}"
                if response.status_code not in {408, 425, 429, 500, 502, 503, 504} or attempt == 2:
                    break
                time.sleep(min(6, 2 ** attempt))
            except requests.RequestException as exc:
                last_error = str(exc)
                if attempt == 2:
                    break
                time.sleep(min(6, 2 ** attempt))
        if last_error:
            failures.append({"record": index, "error": last_error})
    if failures:
        examples = "; ".join(f"row {item['record']}: {item['error']}" for item in failures[:3])
        raise RuntimeError(
            f"Clay {entity_type} table received {sent}/{len(records)} records. "
            f"{len(failures)} failed after retries. {examples}"
        )
    return {"sent": sent, "failed": 0}

def load_latest_clay_people_search(campaign_id):
    run = conn.execute(
        "SELECT * FROM clay_people_search_runs WHERE campaign_id = ? ORDER BY created_at DESC LIMIT 1",
        (campaign_id,),
    ).fetchone()
    if not run:
        return None, pd.DataFrame()
    columns = [description[0] for description in conn.execute("PRAGMA table_info(clay_people_search_runs)").description] if False else []
    run_dict = dict(zip(
        [item[1] for item in conn.execute("PRAGMA table_info(clay_people_search_runs)").fetchall()],
        run,
    ))
    results = pd.read_sql_query(
        "SELECT full_name, first_name, last_name, job_title, seniority, department, location, "
        "location_country, company_name, company_domain, company_linkedin_url, linkedin_url "
        "FROM clay_people_results WHERE search_run_id = ? ORDER BY full_name",
        conn,
        params=(run_dict["id"],),
    )
    return run_dict, results


def load_latest_clay_company_search(campaign_id):
    run = conn.execute(
        "SELECT * FROM clay_search_runs WHERE campaign_id = ? ORDER BY created_at DESC LIMIT 1",
        (campaign_id,),
    ).fetchone()
    if not run:
        return None, pd.DataFrame()
    columns = [item[1] for item in conn.execute("PRAGMA table_info(clay_search_runs)").fetchall()]
    run_dict = dict(zip(columns, run))
    results = pd.read_sql_query(
        "SELECT company_name, domain, industry, country, employee_count, company_type, location, linkedin_url, annual_revenue "
        "FROM clay_company_results WHERE search_run_id = ? ORDER BY company_name",
        conn,
        params=(run_dict["id"],),
    )
    return run_dict, results


def format_created_date(value):
    """Show the campaign creation date without the time component."""
    if not value:
        return "—"
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).strftime("%d %b %Y")
    except (TypeError, ValueError):
        return str(value)[:10]


NAV_ITEMS = [
    "Campaigns",
    "Review & Approvals",
    "Team & Access",
    "Activity Log",
    "Settings",
]

if "pending_mock_user_email" in st.session_state:
    st.session_state["mock_user_email"] = st.session_state.pop("pending_mock_user_email")

active_mock_members = conn.execute(
    "SELECT email, name FROM team_members WHERE status = 'Active' ORDER BY name"
).fetchall()
mock_user_labels = {"__admin__": "Workspace Admin"}
for member_email, member_name in active_mock_members:
    mock_user_labels[member_email] = f"{member_name} ({member_email})"

if st.session_state.get("mock_user_email", "__admin__") not in mock_user_labels:
    st.session_state["mock_user_email"] = "__admin__"

with st.sidebar:
    st.markdown("## AI SDR Dashboard")
    st.divider()
    active_page = st.radio(
        "Workspace",
        NAV_ITEMS,
        key="main_navigation",
        label_visibility="collapsed",
    )
    st.divider()
    st.markdown('<div class="mock-mode-badge">TEST MODE</div>', unsafe_allow_html=True)
    st.divider()
    st.selectbox(
        "Switch Mock User",
        options=list(mock_user_labels.keys()),
        format_func=lambda value: mock_user_labels.get(value, value),
        key="mock_user_email",
        help="Simulation only. This is not a secure login system.",
    )
    st.caption("Mock identity switcher — for testing only.")

current_mock_user_email = st.session_state.get("mock_user_email", "__admin__")
current_mock_user_name = mock_user_labels.get(current_mock_user_email, "Workspace Admin")
is_mock_admin = current_mock_user_email == "__admin__"

previous_mock_identity = st.session_state.get("_previous_mock_user_email", current_mock_user_email)
if previous_mock_identity != current_mock_user_email:
    for state_key in (
        "pending_campaign_action",
        "pending_campaign_action_id",
        "editing_campaign_id",
        "campaign_action_confirmed",
        "campaign_action_confirmed_id",
    ):
        st.session_state.pop(state_key, None)
    st.session_state.pop("overview_campaign", None)
    st.session_state["_reset_campaign_preview_widget"] = True
    st.session_state["_previous_mock_user_email"] = current_mock_user_email

# Show saved notices after navigation reruns.
campaign_edit_notice = st.session_state.pop("campaign_edit_notice", None)
if campaign_edit_notice and active_page in ("Campaigns", "Review & Approvals"):
    st.success(campaign_edit_notice)

def campaign_as_dict(campaign_id):
    row = conn.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
    if row is None:
        return None
    columns = [item[1] for item in conn.execute("PRAGMA table_info(campaigns)").fetchall()]
    return dict(zip(columns, row))


@st.dialog("Delete Campaign?", width="small")
def show_campaign_delete_dialog(campaign_id, campaign_name):
    st.write(
        f"Are you sure you want to delete **{campaign_name}**? "
        "Its locally stored company and contact search results will also be deleted. "
        "This action cannot be undone."
    )
    confirm_col, cancel_col = st.columns(2)
    with confirm_col:
        if st.button(
            "Delete Campaign",
            type="primary",
            use_container_width=True,
            key=f"confirm_delete_campaign_{campaign_id}",
        ):
            st.session_state["campaign_action_confirmed"] = True
            st.session_state["campaign_action_confirmed_id"] = campaign_id
            st.session_state["_force_campaign_selection"] = campaign_id
            st.rerun()
    with cancel_col:
        if st.button(
            "Cancel",
            use_container_width=True,
            key=f"cancel_delete_campaign_{campaign_id}",
        ):
            st.session_state.pop("pending_campaign_action", None)
            st.session_state.pop("pending_campaign_action_id", None)
            st.rerun()


def log_activity(action, campaign_id=None, campaign_name="", actor="Unassigned", details=""):
    conn.execute(
        """
        INSERT INTO activity_log (action, campaign_id, campaign_name, actor, details, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            action,
            campaign_id,
            campaign_name or "—",
            actor or "Unassigned",
            details or "",
            datetime.now().isoformat(timespec="seconds"),
        ),
    )
    conn.commit()



def get_invitation_email_config():
    """Read invitation SMTP settings from Streamlit Secrets."""
    try:
        config = dict(st.secrets.get("email", {}))
    except Exception:
        config = {}
    try:
        smtp_port = int(config.get("smtp_port", 587))
    except (TypeError, ValueError):
        smtp_port = 587
    return {
        "smtp_server": str(config.get("smtp_server", "smtp.gmail.com")).strip(),
        "smtp_port": smtp_port,
        "sender_email": str(config.get("sender_email", "")).strip(),
        "app_password": str(config.get("app_password", "")).replace(" ", "").strip(),
        "sender_name": str(config.get("sender_name", "AI SDR Dashboard")).strip(),
        "dashboard_url": str(config.get("dashboard_url", "")).strip().rstrip("/"),
    }


def invitation_email_is_configured():
    config = get_invitation_email_config()
    return bool(config["sender_email"] and config["app_password"] and config["dashboard_url"])


def send_workspace_invitation_email(recipient_name, recipient_email, permission, inviter_name, invitation_token):
    """Send a workspace invitation email; credentials are read only from Streamlit Secrets."""
    config = get_invitation_email_config()
    if not (config["sender_email"] and config["app_password"] and config["dashboard_url"]):
        raise ValueError(
            "Invitation email is not configured. Add sender_email, app_password, and dashboard_url under [email] in Streamlit Secrets."
        )

    invitation_url = f"{config['dashboard_url']}?invite={invitation_token}"
    safe_name = html.escape(recipient_name or "there")
    safe_permission = html.escape(permission)
    safe_inviter = html.escape(inviter_name or "Workspace Admin")
    safe_url = html.escape(invitation_url, quote=True)

    message = EmailMessage()
    message["Subject"] = "You're invited to the AI SDR Dashboard"
    message["From"] = formataddr((config["sender_name"], config["sender_email"]))
    message["To"] = recipient_email
    message.set_content(
        f"Hi {recipient_name or 'there'},\n\n"
        f"{inviter_name or 'Workspace Admin'} has invited you to the AI SDR Dashboard.\n\n"
        f"Dashboard access: {permission}\n\n"
        f"Accept your invitation using this link:\n{invitation_url}\n\n"
        "This invitation link expires in 7 days. If you were not expecting this invitation, you can ignore this email."
    )
    message.add_alternative(
        '<html><body style="font-family:Arial,sans-serif;color:#202938;line-height:1.55">'
        f'<p>Hi {safe_name},</p>'
        f'<p><strong>{safe_inviter}</strong> has invited you to the AI SDR Dashboard.</p>'
        f'<p><strong>Dashboard access:</strong> {safe_permission}</p>'
        f'<p><a href="{safe_url}" style="display:inline-block;background:#5b35d5;color:#fff;'
        'padding:11px 18px;text-decoration:none;border-radius:6px">Accept Invitation</a></p>'
        '<p>This invitation link expires in 7 days.</p>'
        '<p>If you were not expecting this invitation, you can ignore this email.</p>'
        '</body></html>',
        subtype="html",
    )

    with smtplib.SMTP(config["smtp_server"], config["smtp_port"], timeout=25) as server:
        server.ehlo()
        server.starttls(context=ssl.create_default_context())
        server.ehlo()
        server.login(config["sender_email"], config["app_password"])
        server.send_message(message)


def render_invitation_acceptance():
    """Accept an emailed workspace invitation in the current Mock Mode workflow."""
    try:
        invitation_token = st.query_params.get("invite")
    except Exception:
        invitation_token = None
    if not invitation_token:
        return

    invitation = conn.execute(
        """SELECT id, member_email, member_name, permission, invitation_status, invited_by, expires_at
           FROM workspace_access WHERE invitation_token = ?""",
        (str(invitation_token),),
    ).fetchone()

    st.divider()
    with st.container(border=True):
        st.subheader("Dashboard invitation")
        if not invitation:
            st.error("This invitation link is invalid, expired, or has already been revoked.")
            return
        access_id, member_email, member_name, permission, invitation_status, invited_by, expires_at = invitation
        if invitation_status == "Accepted":
            st.success("This invitation has already been accepted.")
            return
        if invitation_status != "Pending":
            st.warning("This invitation is no longer active. Ask the dashboard owner to share access again.")
            return
        try:
            is_expired = bool(expires_at) and datetime.fromisoformat(expires_at) < datetime.now()
        except (TypeError, ValueError):
            is_expired = False
        if is_expired:
            conn.execute(
                "UPDATE workspace_access SET invitation_status = 'Expired', invitation_token = NULL WHERE id = ?",
                (access_id,),
            )
            conn.commit()
            st.error("This invitation has expired. Ask the dashboard owner to share access again.")
            return

        access_label = "View" if permission == "View Only" else "Edit"
        st.write(f"**Email:** {member_email}")
        st.write(f"**Dashboard access:** {access_label}")
        st.write(f"**Shared by:** {invited_by}")
        st.warning(
            "This dashboard is currently in Mock Mode. Accepting activates a simulated dashboard identity; "
            "it does not authenticate the person's email address or provide production-grade access security."
        )
        if st.button("Accept Invitation", type="primary", key="accept_workspace_invitation"):
            now_text = datetime.now().isoformat(timespec="seconds")
            conn.execute(
                """INSERT INTO team_members (email, name, status, created_at)
                   VALUES (?, ?, 'Active', ?)
                   ON CONFLICT(email) DO UPDATE SET name = excluded.name, status = 'Active'""",
                (member_email, member_name, now_text),
            )
            conn.execute(
                "UPDATE workspace_access SET invitation_status = 'Accepted', accepted_at = ? WHERE id = ?",
                (now_text, access_id),
            )
            conn.commit()
            log_activity(
                "Workspace invitation accepted", None, "Workspace", member_name,
                f"{member_email} accepted {access_label} access to the dashboard.",
            )
            st.session_state["pending_mock_user_email"] = member_email
            try:
                del st.query_params["invite"]
            except Exception:
                pass
            st.success("Invitation accepted. The dashboard will open in the invited user's test identity.")
            st.rerun()


def access_label_to_permission(label):
    """Map the compact UI labels to the existing permission values used by access checks."""
    return {"View": "View Only", "Edit": "Can Edit"}[label]


def permission_to_access_label(permission):
    return "Edit" if permission == "Can Edit" else "View"


render_invitation_acceptance()


def next_duplicate_campaign_name(original_name):
    """Return a unique copy name: Name (Copy), Name (Copy 2), etc."""
    existing_names = {
        str(row[0] or "").strip().casefold()
        for row in conn.execute("SELECT name FROM campaigns").fetchall()
    }
    base_name = f"{str(original_name or 'Untitled campaign').strip()} (Copy)"
    candidate = base_name
    suffix = 2
    while candidate.casefold() in existing_names:
        candidate = f"{base_name.rsplit(' (Copy)', 1)[0]} (Copy {suffix})"
        suffix += 1
    return candidate


@st.dialog("Edit Campaign", width="large")
def show_edit_campaign_dialog(campaign_id):
    campaign = campaign_as_dict(campaign_id)
    if not campaign:
        st.error("This campaign could not be found. Close this window and refresh the dashboard.")
        return

    st.caption("Update campaign details and targeting criteria. Changes to filters require criteria approval again.")
    seniority_lookup = {value.casefold(): value for value in SENIORITY_OPTIONS}
    saved_seniority = []
    for value in split_clay_values(campaign.get("seniority", "")):
        if value.casefold() == "owner / founder":
            saved_seniority.extend(["Owner", "Founder"])
        elif value.casefold() in seniority_lookup:
            saved_seniority.append(seniority_lookup[value.casefold()])
    saved_seniority = list(dict.fromkeys(saved_seniority))
    saved_sizes = [
        value.strip() for value in str(campaign.get("company_size", "") or "").split(",")
        if value.strip() in COMPANY_SIZE_OPTIONS
    ]

    with st.form(f"edit_campaign_modal_form_{campaign_id}", enter_to_submit=False):
        with st.container(border=True):
            st.markdown('<div class="campaign-section-header">Campaign Details</div>', unsafe_allow_html=True)
            meta_cols = st.columns(2, gap="large")
            with meta_cols[0]:
                edit_name = st.text_input("Campaign Name *", value=str(campaign.get("name") or ""), placeholder="e.g., Q1 Marketing Campaign")
            with meta_cols[1]:
                edit_owner = st.text_input("Campaign Owner *", value=str(campaign.get("campaign_owner", "") or ""), placeholder="Salesperson name")

        with st.container(border=True):
            st.markdown('<div class="campaign-section-header">1. Companies <small>Define the company criteria to find the right accounts.</small></div>', unsafe_allow_html=True)
            company_row1 = st.columns(3, gap="large")
            with company_row1[0]:
                edit_industry = st.multiselect(
                    "Industry", options=[], default=split_clay_values(campaign.get("industry", "")),
                    accept_new_options=True, placeholder="Add or select industries",
                    help="Each selected industry appears as a tag.",
                )
            with company_row1[1]:
                edit_company_size = st.multiselect("Company Size", COMPANY_SIZE_OPTIONS, default=saved_sizes, placeholder="Select company size")
            with company_row1[2]:
                edit_company_country = st.multiselect(
                    "Company Country", options=COUNTRY_OPTIONS, default=split_clay_values(campaign.get("company_country", "")),
                    accept_new_options=True, placeholder="Select countries", help="Select multiple countries; each appears as a tag.",
                )
            company_row2 = st.columns(3, gap="large")
            with company_row2[0]:
                edit_company_city = st.multiselect(
                    "City", options=[], default=split_clay_values(campaign.get("company_city", "")),
                    accept_new_options=True, placeholder="Add cities", help="Optional company-headquarters location filter.",
                )
            with company_row2[1]:
                edit_company_state = st.multiselect(
                    "State / Region", options=[], default=split_clay_values(campaign.get("company_state", "")),
                    accept_new_options=True, placeholder="Add states or regions", help="Optional company-headquarters location filter.",
                )
            with company_row2[2]:
                edit_current_cms = st.multiselect(
                    "Current CMS", options=[], default=split_clay_values(campaign.get("current_cms", "")),
                    accept_new_options=True, placeholder="Add CMS platforms",
                    help="Optional research note. Each platform appears as a tag; enrichment is done in Clay after review.",
                )

        with st.container(border=True):
            st.markdown('<div class="campaign-section-header">2. Contacts <small>Define the contact criteria to find the right people from selected companies.</small></div>', unsafe_allow_html=True)
            contact_row1 = st.columns(2, gap="large")
            with contact_row1[0]:
                edit_target_titles = st.multiselect(
                    "Job Title", options=[], default=split_clay_values(campaign.get("target_titles", "")),
                    accept_new_options=True, placeholder="Add target job titles", help="Each selected job title appears as a tag.",
                )
            with contact_row1[1]:
                edit_department = st.multiselect(
                    "Department", options=[], default=split_clay_values(campaign.get("department", "")),
                    accept_new_options=True, placeholder="Add departments", help="Each selected department appears as a tag.",
                )
            contact_row2 = st.columns(3, gap="large")
            with contact_row2[0]:
                edit_seniority = st.multiselect("Seniority", SENIORITY_OPTIONS, default=saved_seniority, placeholder="Select seniority levels")
            with contact_row2[1]:
                edit_job_level = st.selectbox(
                    "Job Level", ["Below", "Above", "Equal"],
                    index={"below": 0, "above": 1, "exact": 2, "equal": 2}.get(str(campaign.get("job_level", "Equal") or "Equal").casefold(), 2),
                    help="Compare the selected Seniority level(s) using this rule.",
                )
            with contact_row2[2]:
                edit_contact_country = st.multiselect(
                    "Contact Country", options=COUNTRY_OPTIONS, default=split_clay_values(campaign.get("contact_country", "")),
                    accept_new_options=True, placeholder="Select countries", help="Each selected country appears as a tag.",
                )

        with st.container(border=True):
            st.markdown('<div class="campaign-section-header">3. Clay Details <small>Provide Clay workbook and webhook details.</small></div>', unsafe_allow_html=True)
            st.caption("Optional: add the workbook and webhook destinations now, or save the campaign and configure them later.")
            st.caption("Build Campaign Data requires a valid workbook link and both table webhook URLs.")
            edit_clay_table_url = st.text_input(
                "Clay Workbook Link", value=str(campaign.get("clay_table_url", "") or ""), placeholder="https://app.clay.com/...",
                help="The sales team will open this workbook to review companies and contacts.",
            )
            webhook_cols = st.columns(2, gap="large")
            with webhook_cols[0]:
                edit_companies_webhook = st.text_input("Companies Table Webhook URL", value=str(campaign.get("clay_companies_webhook_url", "") or ""), placeholder="https://api.clay.com/v3/sources/webhook/...")
                edit_companies_webhook_auth = st.text_input("Companies Webhook Auth Token", value=str(campaign.get("clay_companies_webhook_auth", "") or ""), type="password", help="Optional token configured on the Companies webhook in Clay.")
            with webhook_cols[1]:
                edit_contacts_webhook = st.text_input("Contacts Table Webhook URL", value=str(campaign.get("clay_contacts_webhook_url", "") or ""), placeholder="https://api.clay.com/v3/sources/webhook/...")
                edit_contacts_webhook_auth = st.text_input("Contacts Webhook Auth Token", value=str(campaign.get("clay_contacts_webhook_auth", "") or ""), type="password", help="Optional token configured on the Contacts webhook in Clay.")

        save_changes = st.form_submit_button("Save Changes", type="primary", use_container_width=True)

    cancel_col, _ = st.columns([1, 4])
    with cancel_col:
        if st.button("Cancel", key=f"cancel_edit_campaign_modal_{campaign_id}", use_container_width=True):
            st.session_state["editing_campaign_id"] = None
            st.session_state.pop("campaign_edit_context", None)
            st.rerun()

    if save_changes:
        if not edit_name.strip() or not edit_owner.strip():
            st.error("Please enter both Campaign Name and Campaign Owner.")
        elif not edit_industry and not edit_company_country and not edit_company_state and not edit_company_city and not edit_company_size:
            st.error("Add at least one company filter: Industry, Company Size, or Company Country.")
        else:
            owner_value = edit_owner.strip()
            original_campaign = campaign_as_dict(campaign_id) or {}
            search_criteria_fields = {
                "industry": join_tag_values(edit_industry),
                "company_country": join_tag_values(edit_company_country),
                "company_state": join_tag_values(edit_company_state),
                "company_city": join_tag_values(edit_company_city),
                "company_size": ", ".join(edit_company_size),
                "contact_country": join_tag_values(edit_contact_country),
                "target_titles": join_tag_values(edit_target_titles),
                "department": join_tag_values(edit_department),
                "seniority": ", ".join(edit_seniority),
                "job_level": edit_job_level,
            }
            criteria_changed = any(
                str(original_campaign.get(field, "") or "").strip() != str(value or "").strip()
                for field, value in search_criteria_fields.items()
            )
            conn.execute(
                """UPDATE campaigns
                   SET name = ?, campaign_owner = ?, industry = ?, company_country = ?, company_state = ?, company_city = ?, company_size = ?,
                       contact_country = ?, target_titles = ?, current_cms = ?, department = ?, seniority = ?,
                       job_level = ?, clay_table_url = ?, clay_companies_webhook_url = ?, clay_contacts_webhook_url = ?,
                       clay_companies_webhook_auth = ?, clay_contacts_webhook_auth = ?
                   WHERE id = ?""",
                (
                    edit_name.strip(), owner_value, join_tag_values(edit_industry), join_tag_values(edit_company_country),
                    join_tag_values(edit_company_state), join_tag_values(edit_company_city), ", ".join(edit_company_size),
                    join_tag_values(edit_contact_country), join_tag_values(edit_target_titles),
                    join_tag_values(edit_current_cms), join_tag_values(edit_department), ", ".join(edit_seniority), edit_job_level,
                    edit_clay_table_url.strip(), edit_companies_webhook.strip(), edit_contacts_webhook.strip(),
                    edit_companies_webhook_auth.strip(), edit_contacts_webhook_auth.strip(), campaign_id,
                ),
            )
            if criteria_changed:
                conn.execute(
                    """UPDATE campaigns SET status = 'Draft', criteria_approved = 0,
                       criteria_approved_by = '', criteria_approved_at = '',
                       industry_clay_value = '', industry_mapping_status = '' WHERE id = ?""",
                    (campaign_id,),
                )
                conn.execute("DELETE FROM clay_company_results WHERE campaign_id = ?", (campaign_id,))
                conn.execute("DELETE FROM clay_people_results WHERE campaign_id = ?", (campaign_id,))
                conn.execute("DELETE FROM clay_search_runs WHERE campaign_id = ?", (campaign_id,))
                conn.execute("DELETE FROM clay_people_search_runs WHERE campaign_id = ?", (campaign_id,))
                conn.execute("DELETE FROM leads WHERE campaign_id = ?", (campaign_id,))
                notice_text = (
                    "Campaign criteria updated. Approve the revised criteria before running a new Clay search. "
                    "The dashboard cannot delete rows already sent to Clay, so clear the existing Companies and Contacts tables "
                    "or connect fresh webhook tables before rebuilding to avoid mixing old and new results."
                )
                activity_details = "Search criteria changed. Previous approval and search results were cleared; re-approval is required."
                activity_action = "Campaign criteria updated"
            else:
                notice_text = "Campaign details and Clay workbook settings saved. Existing criteria approval and search results were preserved."
                activity_details = "Campaign metadata / Clay workbook connection settings updated; search criteria were unchanged."
                activity_action = "Campaign settings updated"
            conn.commit()
            log_activity(activity_action, campaign_id, edit_name.strip(), owner_value, activity_details)
            st.session_state["campaign_edit_notice"] = notice_text
            st.session_state["active_campaign_id"] = campaign_id
            st.session_state["run_campaign_selector"] = campaign_id
            st.session_state["lead_campaign_selector"] = campaign_id
            st.session_state["editing_campaign_id"] = None
            st.session_state.pop("campaign_edit_context", None)
            st.rerun()


@st.dialog("Create New Campaign", width="large")
def show_create_campaign_dialog():
    st.caption("Define your target companies and contacts to build a prospect list in Clay.")

    with st.form("create_campaign_dialog_form", enter_to_submit=False):
        with st.container(border=True):
            st.markdown('<div class="campaign-section-header">Campaign Details</div>', unsafe_allow_html=True)
            meta_cols = st.columns(2, gap="large")
            with meta_cols[0]:
                campaign_name = st.text_input("Campaign Name *", placeholder="e.g., Q1 Marketing Campaign")
            with meta_cols[1]:
                campaign_owner = st.text_input("Campaign Owner *", placeholder="Salesperson name")

        with st.container(border=True):
            st.markdown('<div class="campaign-section-header">1. Companies <small>Define the company criteria to find the right accounts.</small></div>', unsafe_allow_html=True)
            company_row1 = st.columns(3, gap="large")
            with company_row1[0]:
                industry = st.multiselect("Industry", options=[], default=[], accept_new_options=True, placeholder="Add or select industries", help="Each selected industry appears as a tag.")
            with company_row1[1]:
                company_size = st.multiselect("Company Size", COMPANY_SIZE_OPTIONS, default=[], placeholder="Select company size")
            with company_row1[2]:
                company_country = st.multiselect("Company Country", options=COUNTRY_OPTIONS, default=[], accept_new_options=True, placeholder="Select countries", help="Select multiple countries; each appears as a tag.")
            company_row2 = st.columns(3, gap="large")
            with company_row2[0]:
                company_city = st.multiselect("City", options=[], default=[], accept_new_options=True, placeholder="Add cities", help="Optional company-headquarters location filter.")
            with company_row2[1]:
                company_state = st.multiselect("State / Region", options=[], default=[], accept_new_options=True, placeholder="Add states or regions", help="Optional company-headquarters location filter.")
            with company_row2[2]:
                current_cms = st.multiselect("Current CMS", options=[], default=[], accept_new_options=True, placeholder="Add CMS platforms", help="Optional research note. Each platform appears as a tag.")

        with st.container(border=True):
            st.markdown('<div class="campaign-section-header">2. Contacts <small>Define the contact criteria to find the right people from selected companies.</small></div>', unsafe_allow_html=True)
            contact_row1 = st.columns(2, gap="large")
            with contact_row1[0]:
                target_titles = st.multiselect("Job Title", options=[], default=[], accept_new_options=True, placeholder="Add target job titles", help="Each selected job title appears as a tag.")
            with contact_row1[1]:
                department = st.multiselect("Department", options=[], default=[], accept_new_options=True, placeholder="Add departments", help="Each selected department appears as a tag.")
            contact_row2 = st.columns(3, gap="large")
            with contact_row2[0]:
                seniority = st.multiselect("Seniority", SENIORITY_OPTIONS, default=[], placeholder="Select seniority levels")
            with contact_row2[1]:
                job_level = st.selectbox("Job Level", ["Below", "Above", "Equal"], index=1, help="Compare the selected Seniority level(s) using this rule.")
            with contact_row2[2]:
                contact_country = st.multiselect("Contact Country", options=COUNTRY_OPTIONS, default=[], accept_new_options=True, placeholder="Select countries", help="Each selected country appears as a tag.")

        with st.container(border=True):
            st.markdown('<div class="campaign-section-header">3. Clay Details <small>Provide Clay workbook and webhook details.</small></div>', unsafe_allow_html=True)
            st.caption("Optional: add the workbook and webhook destinations now, or save the campaign and configure them later.")
            st.caption("Build Campaign Data requires a valid workbook link and both table webhook URLs.")
            clay_table_url = st.text_input("Clay Workbook Link", placeholder="https://app.clay.com/...", help="The sales team will open this workbook to review companies and contacts.")
            webhook_cols = st.columns(2, gap="large")
            with webhook_cols[0]:
                clay_companies_webhook_url = st.text_input("Companies Table Webhook URL", placeholder="https://api.clay.com/v3/sources/webhook/...")
                clay_companies_webhook_auth = st.text_input("Companies Webhook Auth Token", value="", type="password", help="Optional token configured on the Companies webhook in Clay.")
            with webhook_cols[1]:
                clay_contacts_webhook_url = st.text_input("Contacts Table Webhook URL", placeholder="https://api.clay.com/v3/sources/webhook/...")
                clay_contacts_webhook_auth = st.text_input("Contacts Webhook Auth Token", value="", type="password", help="Optional token configured on the Contacts webhook in Clay.")

        submitted = st.form_submit_button("Create Campaign", type="primary", use_container_width=True)

    cancel_col, _ = st.columns([1, 4])
    with cancel_col:
        if st.button("Cancel", key="cancel_create_campaign_dialog", use_container_width=True):
            st.rerun()

    if submitted:
        if not campaign_name.strip() or not campaign_owner.strip():
            st.error("Please complete both required fields: Campaign Name and Campaign Owner.")
        elif not industry and not company_country and not company_state and not company_city and not company_size:
            st.error("Add at least one company filter: Industry, Company Size, or Company Country.")
        else:
            campaign_id = str(uuid.uuid4())
            owner_value = campaign_owner.strip()
            conn.execute(
                """INSERT INTO campaigns
                   (id, name, industry, company_country, company_state, company_city, company_size, contact_country, target_titles,
                    min_score, status, created_at, current_cms, department, seniority, job_level,
                    email_sequence_instructions, clay_table_url, campaign_owner,
                    clay_companies_webhook_url, clay_contacts_webhook_url,
                    clay_companies_webhook_auth, clay_contacts_webhook_auth)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    campaign_id, campaign_name.strip(), join_tag_values(industry), join_tag_values(company_country),
                    join_tag_values(company_state), join_tag_values(company_city), ", ".join(company_size),
                    join_tag_values(contact_country), join_tag_values(target_titles),
                    0, "Draft", datetime.now().isoformat(timespec="seconds"), join_tag_values(current_cms),
                    join_tag_values(department), ", ".join(seniority), job_level, "", clay_table_url.strip(),
                    owner_value, clay_companies_webhook_url.strip(), clay_contacts_webhook_url.strip(),
                    clay_companies_webhook_auth.strip(), clay_contacts_webhook_auth.strip(),
                ),
            )
            conn.commit()
            log_activity("Campaign created", campaign_id, campaign_name.strip(), owner_value)
            st.session_state.pop("overview_campaign", None)
            st.session_state["_reset_campaign_preview_widget"] = True
            st.session_state["active_campaign_id"] = campaign_id
            st.session_state["run_campaign_selector"] = campaign_id
            st.session_state["lead_campaign_selector"] = campaign_id
            st.session_state["campaign_create_notice"] = "Campaign created successfully."
            st.rerun()


# Share controls are intentionally removed from the top toolbar.
st.title("AI SDR Dashboard")


if active_page == "Campaigns":
    heading_col, create_col = st.columns([5.5, 1.5])
    with heading_col:
        st.subheader("Campaign Overview")
        st.caption("Manage campaigns, review their criteria, and open the linked Clay table.")
    with create_col:
        if is_mock_admin:
            if st.button("＋ Create Campaign", key="create_campaign_button", type="primary", use_container_width=False):
                st.session_state["editing_campaign_id"] = None
                show_create_campaign_dialog()

    delete_notice = st.session_state.pop("campaign_delete_notice", None)
    if delete_notice:
        st.success(delete_notice)

    create_notice = st.session_state.pop("campaign_create_notice", None)
    if create_notice:
        st.success(create_notice)

    duplicate_notice = st.session_state.pop("campaign_duplicate_notice", None)
    if duplicate_notice:
        st.success(duplicate_notice)

    campaigns = load_campaigns()
    if campaigns.empty:
        if is_mock_admin:
            st.info("No campaigns yet. Select **Create Campaign** to set up your first campaign.")
        else:
            st.info("No campaigns have been shared with this mock user yet.")
        campaign_ids = []
    else:
        # Exact five-column campaign preview requested by the user.
        campaign_preview = campaigns[
            ["id", "name", "created_at", "campaign_owner", "status", "clay_table_url"]
        ].copy()
        campaign_preview["created_at"] = campaign_preview["created_at"].apply(format_created_date)
        campaign_preview["campaign_owner"] = campaign_preview["campaign_owner"].fillna("Unassigned")
        campaign_preview["status"] = campaign_preview["status"].fillna("Draft")
        campaign_preview["clay_table_url"] = campaign_preview["clay_table_url"].fillna("")
        campaign_preview = campaign_preview.rename(
            columns={
                "name": "Campaign Name",
                "created_at": "Created Date",
                "campaign_owner": "Campaign Owner",
                "status": "Status",
                "clay_table_url": "Clay Workbook",
            }
        )
        campaign_preview = campaign_preview[
            [
                "id",
                "Campaign Name",
                "Created Date",
                "Campaign Owner",
                "Status",
                "Clay Workbook",
            ]
        ]
        campaign_ids = campaigns["id"].tolist()

        st.markdown("#### Campaign Preview")
        st.caption("Click a campaign row to select it. Its details and available actions will appear below.")
        if not st.session_state.get("_campaign_preview_initialized", False):
            st.session_state.pop("campaign_preview_table", None)
            st.session_state["_campaign_preview_initialized"] = True
        if st.session_state.pop("_reset_campaign_preview_widget", False):
            st.session_state.pop("campaign_preview_table", None)
        table_event = st.dataframe(
            campaign_preview.drop(columns=["id"]),
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            column_config={
                "Clay Workbook": st.column_config.LinkColumn(
                    "Clay Workbook",
                    display_text="Open Clay Workbook",
                )
            },
            key="campaign_preview_table",
        )

        selected_indexes = []
        try:
            selected_indexes = list(table_event.selection.rows)
        except Exception:
            selected_indexes = []

        selection_signature = tuple(selected_indexes)
        st.session_state["_last_campaign_table_selection"] = list(selection_signature)

        # No campaign is selected by default. Details appear only after a row is selected.
        selected_id = None
        forced_selection = st.session_state.pop("_force_campaign_selection", None)
        if forced_selection in campaign_ids:
            selected_id = forced_selection
            st.session_state["overview_campaign"] = selected_id
        elif selected_indexes:
            selected_index = int(selected_indexes[0])
            if 0 <= selected_index < len(campaigns):
                selected_id = campaigns.iloc[selected_index]["id"]
                st.session_state["overview_campaign"] = selected_id
        else:
            st.session_state.pop("overview_campaign", None)

        if selected_id is not None:
            selected_row = campaigns[campaigns["id"] == selected_id].iloc[0]
            selected_name = str(selected_row["name"] or "Untitled campaign")
            selected_owner = str(selected_row.get("campaign_owner", "Unassigned") or "Unassigned")

            st.divider()
            st.markdown(f"#### Selected Campaign: {selected_name}")
            # Keep all campaign actions in one dedicated row. The campaign title
            # sits above the buttons so it cannot squeeze Build Campaign Data
            # onto a second line on narrower screens.
            approve_col, build_col, edit_col, duplicate_col, delete_col = st.columns(
                [1.25, 1.45, 1.0, 1.35, 1.15], gap="small"
            )
            selected_permission = get_campaign_permission(selected_id)
            selected_approved = bool(int(selected_row.get("criteria_approved", 0) or 0))
            clay_api_key = get_clay_api_key()

            # Resolve the user's industry wording against Clay's current live vocabulary.
            industry_input = str(selected_row.get("industry", "") or "").strip()
            mapped_industry_values = []
            industry_mapping_status = "No industry filter entered."
            industry_mapping_error = ""
            if industry_input and clay_api_key:
                try:
                    live_industry_options = fetch_clay_company_industry_options(clay_api_key)
                    mapped_industry_values, industry_mapping_status = map_industry_to_clay(
                        industry_input, live_industry_options
                    )
                except Exception as mapping_exc:
                    industry_mapping_error = str(mapping_exc)

            if industry_input:
                with st.container(border=True):
                    st.markdown("**Industry Mapping (Clay)**")
                    st.write(f"Your input: **{industry_input}**")
                    if industry_mapping_error:
                        st.error(industry_mapping_error)
                    elif mapped_industry_values:
                        st.write("Clay industry: **" + ", ".join(mapped_industry_values) + "**")
                        st.caption(industry_mapping_status + " · Options checked against Clay's live company-search list.")
                        if industry_mapping_status.startswith("Close category"):
                            st.warning("Please review this suggested category before approving the campaign.")
                    elif not clay_api_key:
                        st.warning("Add the Clay API key in Streamlit Secrets to load and map Clay industry options.")
                    else:
                        st.warning(industry_mapping_status)
            elif not clay_api_key:
                st.caption("Add the Clay API key in Streamlit Secrets to enable live Clay search.")

            mapping_ready = (not industry_input) or bool(mapped_industry_values)
            mapping_needs_review = industry_mapping_status.startswith("Close category")
            with approve_col:
                if selected_permission in ("Owner", "Can Edit"):
                    if selected_approved:
                        st.button("Criteria Approved", key="selected_criteria_approved", disabled=True, use_container_width=True)
                    elif st.button(
                        "Approve Criteria",
                        key="approve_campaign_criteria",
                        type="primary",
                        use_container_width=True,
                        disabled=(not mapping_ready or bool(industry_mapping_error) or mapping_needs_review),
                    ):
                        approved_at = datetime.now().isoformat(timespec="seconds")
                        mapped_value = ", ".join(mapped_industry_values) if industry_input else ""
                        conn.execute(
                            """UPDATE campaigns
                               SET criteria_approved = 1, criteria_approved_by = ?, criteria_approved_at = ?,
                                   industry_clay_value = ?, industry_mapping_status = ?, status = ?
                               WHERE id = ?""",
                            (current_mock_user_name, approved_at, mapped_value, industry_mapping_status,
                             "Criteria Approved", selected_id),
                        )
                        conn.commit()
                        log_activity("Campaign criteria approved", selected_id, selected_name, current_mock_user_name,
                                     "Campaign criteria approved before starting Clay company search.")
                        st.rerun()
                else:
                    st.caption("View Only")
            campaign_destination = campaign_as_dict(selected_id) or {}
            workbook_url = str(campaign_destination.get("clay_table_url", "") or "").strip()
            companies_webhook_url = str(campaign_destination.get("clay_companies_webhook_url", "") or "").strip()
            contacts_webhook_url = str(campaign_destination.get("clay_contacts_webhook_url", "") or "").strip()
            destination_values = (workbook_url, companies_webhook_url, contacts_webhook_url)
            destination_ready = all(is_valid_https_url(value) for value in destination_values)
            destination_partially_configured = any(destination_values) and not destination_ready
            company_search_criteria_ready = bool(
                split_clay_values(selected_row.get("industry", ""))
                or split_clay_values(selected_row.get("company_country", ""))
                or split_clay_values(selected_row.get("company_size", ""))
            )
            build_disabled_reason = ""
            if mapping_needs_review:
                build_disabled_reason = "Review the suggested Clay industry before approving."
            elif not selected_approved:
                build_disabled_reason = "Approve campaign criteria first."
            elif not clay_api_key:
                build_disabled_reason = "Clay API key is not configured."
            elif not company_search_criteria_ready:
                build_disabled_reason = "Add Industry, Company Country, or Company Size. Current CMS is enriched after review in Clay."
            elif not destination_ready:
                build_disabled_reason = "Add a valid Clay workbook link and both webhook URLs in Edit Campaign before building and publishing data."

            with build_col:
                if st.button(
                    "Build Campaign Data",
                    key="build_campaign_data_clay",
                    type="primary",
                    use_container_width=True,
                    disabled=(
                        not selected_approved or not clay_api_key
                        or selected_permission not in ("Owner", "Can Edit")
                        or not mapping_ready or bool(industry_mapping_error) or mapping_needs_review
                        or not company_search_criteria_ready or not destination_ready
                    ),
                ):
                    campaign_for_clay = campaign_as_dict(selected_id) or {}
                    stage = "Company Search"
                    try:
                        conn.execute("UPDATE campaigns SET status = ? WHERE id = ?", ("Company Search Running", selected_id))
                        conn.commit()
                        with st.spinner("Searching companies in Clay, finding matching contacts, and sending both lists to this campaign's Clay workbook..."):
                            clay_result = run_clay_company_search(campaign_for_clay, selected_id, clay_api_key)
                            if clay_result["count"] == 0:
                                conn.execute("UPDATE campaigns SET status = ? WHERE id = ?", ("No Companies Found", selected_id))
                                conn.commit()
                                st.session_state["clay_search_notice"] = {
                                    "state": "no_companies", "company_count": 0,
                                    "company_search_id": clay_result.get("search_id", ""),
                                    "validation_note": clay_result.get("validation_note", ""),
                                }
                                log_activity(
                                    "Clay company search completed with no results", selected_id, selected_name,
                                    current_mock_user_name,
                                    f"Clay returned no companies. Search ID: {clay_result.get('search_id', '')}",
                                )
                                st.rerun()

                            if not clay_result.get("company_identifiers"):
                                raise RuntimeError(
                                    "Clay returned companies, but none had a company LinkedIn URL or domain. "
                                    "The dashboard cannot safely search contacts for these records."
                                )

                            stage = "Contact Search"
                            conn.execute("UPDATE campaigns SET status = ? WHERE id = ?", ("Contact Search Running", selected_id))
                            conn.commit()
                            people_result = run_clay_people_search(
                                campaign_for_clay, selected_id, clay_api_key,
                                clay_result["company_identifiers"],
                                clay_result.get("company_match_identifiers", clay_result["company_identifiers"]),
                            )

                            stage = "Clay Workbook Delivery"
                            conn.execute("UPDATE campaigns SET status = ? WHERE id = ?", ("Sending Results to Clay", selected_id))
                            conn.commit()
                            company_delivery = send_records_to_clay_webhook(
                                companies_webhook_url,
                                campaign_for_clay.get("clay_companies_webhook_auth", ""),
                                selected_id, "company", clay_result.get("records", []),
                            )
                            contact_delivery = send_records_to_clay_webhook(
                                contacts_webhook_url,
                                campaign_for_clay.get("clay_contacts_webhook_auth", ""),
                                selected_id, "person", people_result.get("records", []),
                            )

                            final_status = "Ready for Review" if people_result["count"] else "Ready for Review - No Contacts Found"
                            conn.execute("UPDATE campaigns SET status = ? WHERE id = ?", (final_status, selected_id))
                            conn.commit()

                        log_activity(
                            "Clay database built and published", selected_id, selected_name, current_mock_user_name,
                            f"Companies: {company_delivery['sent']}; contacts: {contact_delivery['sent']}; "
                            f"company search: {clay_result['search_id']}; people search: {people_result['search_id']}; "
                            f"workbook: {workbook_url}",
                        )
                        st.session_state["clay_search_notice"] = {
                            "state": "ready", "company_count": clay_result["count"],
                            "contact_count": people_result["count"],
                            "company_has_more": clay_result["has_more"],
                            "contact_has_more": people_result["has_more"],
                            "company_pages": clay_result.get("page_count", 1),
                            "contact_pages": people_result.get("page_count", 1),
                            "workbook_url": workbook_url,
                            "validation_note": clay_result.get("validation_note", ""),
                            "unverified_employer_count": people_result.get("unverified_employer_count", 0),
                        }
                        st.rerun()
                    except Exception as exc:
                        if stage == "Company Search":
                            failure_status = "Company Search Failed"
                        elif stage == "Contact Search":
                            failure_status = "Contact Search Failed"
                        else:
                            failure_status = "Clay Workbook Delivery Failed"
                        conn.execute("UPDATE campaigns SET status = ? WHERE id = ?", (failure_status, selected_id))
                        conn.commit()
                        log_activity(
                            f"{stage} failed", selected_id, selected_name, current_mock_user_name, str(exc)[:1000]
                        )
                        st.session_state["clay_search_notice"] = {
                            "state": "failed", "stage": stage, "error": str(exc),
                        }
                        st.rerun()
                if build_disabled_reason:
                    st.caption(build_disabled_reason)
            with edit_col:
                if selected_permission in ("Owner", "Can Edit"):
                    if st.button("Edit Campaign", key="selected_edit_campaign", use_container_width=True):
                        st.session_state["editing_campaign_id"] = selected_id
                        st.session_state["overview_campaign"] = selected_id
                        st.session_state["_force_campaign_selection"] = selected_id
                        st.session_state.pop("campaign_edit_context", None)
                        log_activity("Edit opened", selected_id, selected_name, selected_owner)
                        st.rerun()
                else:
                    st.caption("View Only")

            with duplicate_col:
                if selected_permission in ("Owner", "Can Edit"):
                    if st.button("Duplicate Campaign", key="selected_duplicate_campaign", use_container_width=True):
                        # Duplication is immediate; never leave an edit modal open from a prior action.
                        st.session_state["editing_campaign_id"] = None
                        st.session_state.pop("campaign_edit_context", None)
                        source_campaign = campaign_as_dict(selected_id)
                        if source_campaign:
                            new_id = str(uuid.uuid4())
                            new_name = next_duplicate_campaign_name(source_campaign.get("name", selected_name))
                            duplicate_owner = selected_owner if is_mock_admin else current_mock_user_name
                            conn.execute(
                                """
                                INSERT INTO campaigns
                                (id, name, industry, company_country, company_state, company_city, company_size, contact_country, target_titles,
                                 min_score, status, created_at, current_cms, department, seniority,
                                 job_level, email_sequence_instructions, clay_table_url, campaign_owner)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    new_id,
                                    new_name,
                                    source_campaign.get("industry", "") or "",
                                    source_campaign.get("company_country", "") or "",
                                    source_campaign.get("company_state", "") or "",
                                    source_campaign.get("company_city", "") or "",
                                    source_campaign.get("company_size", "") or "",
                                    source_campaign.get("contact_country", "") or "",
                                    source_campaign.get("target_titles", "") or "",
                                    int(source_campaign.get("min_score", 0) or 0),
                                    "Draft",
                                    datetime.now().isoformat(timespec="seconds"),
                                    source_campaign.get("current_cms", "") or "",
                                    source_campaign.get("department", "") or "",
                                    source_campaign.get("seniority", "Manager") or "Manager",
                                    source_campaign.get("job_level", "Above") or "Above",
                                    source_campaign.get("email_sequence_instructions", "") or "",
                                    "",  # A duplicate starts without the original Clay table URL.
                                    duplicate_owner,
                                ),
                            )
                            conn.commit()
                            log_activity(
                                "Campaign duplicated",
                                new_id,
                                new_name,
                                duplicate_owner,
                                f"Duplicated from campaign: {selected_name}",
                            )
                            st.session_state["campaign_duplicate_notice"] = (
                                f"Campaign duplicated successfully: {new_name}"
                            )
                            st.session_state["overview_campaign"] = new_id
                            st.session_state["_force_campaign_selection"] = new_id
                            st.session_state["_reset_campaign_preview_widget"] = True
                            # Keep the duplicate selected, but leave the editor closed.
                            st.session_state["editing_campaign_id"] = None
                            st.session_state.pop("campaign_edit_context", None)
                            st.rerun()
                        else:
                            st.error("The selected campaign could not be found, so it was not duplicated.")

            with delete_col:
                if selected_permission == "Owner":
                    if st.button("Delete Campaign", key="selected_delete_campaign", use_container_width=True):
                        # Delete should open only its confirmation dialog, never the editor.
                        st.session_state["editing_campaign_id"] = None
                        st.session_state.pop("campaign_edit_context", None)
                        st.session_state["pending_campaign_action"] = "delete"
                        st.session_state["pending_campaign_action_id"] = selected_id
                        st.session_state["_force_campaign_selection"] = selected_id
                        st.rerun()

            # Open the editor as a centered modal instead of placing it below search results.
            if (
                st.session_state.get("editing_campaign_id") == selected_id
                and selected_permission in ("Owner", "Can Edit")
            ):
                show_edit_campaign_dialog(selected_id)

            if not selected_approved:
                st.info("Review the campaign filters, then select **Approve Criteria** to unlock Build Campaign Data.")
            elif not clay_api_key:
                st.warning("Clay API key is not configured. Add it in Streamlit Cloud → App settings → Secrets.")
            elif not company_search_criteria_ready:
                st.warning("Add at least Industry, Company Country, or Company Size as a company search filter. Current CMS is enriched after review in Clay.")
            elif not destination_ready:
                st.warning(
                    "Before building data, add valid HTTPS links for the Clay workbook and its Companies and Contacts webhook tables in Edit Campaign. "
                    "The workbook and its two webhook tables must already exist in Clay."
                )
            st.caption(
                "Build Campaign Data searches companies, searches people at those companies, and sends both lists to the configured Clay webhook tables. "
                "Current CMS and email enrichment are intentionally left for the sales team to run in Clay after reviewing the lists."
            )

            clay_notice = st.session_state.pop("clay_search_notice", None)
            if clay_notice:
                if clay_notice.get("state") == "ready":
                    st.success(
                        f"Database ready for review: {clay_notice['company_count']} companies and "
                        f"{clay_notice['contact_count']} contacts were sent to Clay."
                    )
                    st.link_button("Open Clay Workbook", clay_notice["workbook_url"])
                    if clay_notice.get("company_has_more") or clay_notice.get("contact_has_more"):
                        st.warning("Clay had more matching results available than the configured per-search cap. The returned records were sent for review; narrow the filters or raise the configured cap only after confirming the workspace plan.")
                    if clay_notice.get("validation_note"):
                        st.info(clay_notice["validation_note"])
                    if clay_notice.get("unverified_employer_count", 0):
                        st.warning(
                            f"{clay_notice['unverified_employer_count']} contacts did not include a company identifier in the returned profile. "
                            "The underlying search was scoped to the target companies; spot-check these rows in Clay."
                        )
                elif clay_notice.get("state") == "no_companies":
                    st.warning("Clay company search completed successfully but returned zero matching companies. Contact search was not run.")
                    if clay_notice.get("validation_note"):
                        st.info(clay_notice["validation_note"])
                else:
                    st.error(
                        f"{clay_notice.get('stage', 'Clay workflow')} failed. "
                        f"Campaign status was updated and the error was logged: {clay_notice.get('error', 'Unknown error')}"
                    )

            detail_cols = st.columns([1.25, 2.75])
            with detail_cols[0]:
                with st.container(border=True):
                    st.write("**Created Date**", format_created_date(selected_row["created_at"]))
                    st.write("**Campaign Owner**", selected_owner)
                    st.write("**Status**", str(selected_row["status"] or "Draft"))
                    clay_link = str(selected_row.get("clay_table_url", "") or "").strip()
                    if clay_link:
                        st.link_button("Open Clay Workbook", clay_link, use_container_width=True)
                    else:
                        st.caption("Clay Workbook: Not added yet")
            with detail_cols[1]:
                with st.container(border=True):
                    st.markdown("**Campaign Criteria (Filters)**")
                    criteria_cols = st.columns(3)
                    criteria_cols[0].write(f"**Industry**\n\n{selected_row['industry'] or 'Any'}")
                    criteria_cols[1].write(f"**Company Country**\n\n{selected_row['company_country'] or 'Any'}")
                    st.caption(f"Company State / Region: {selected_row.get('company_state', '') or 'Any'} · Company City: {selected_row.get('company_city', '') or 'Any'}")
                    criteria_cols[2].write(f"**Company Size**\n\n{selected_row.get('company_size', '') or 'Any'}")
                    criteria_cols = st.columns(3)
                    criteria_cols[0].write(f"**Contact Country**\n\n{selected_row['contact_country'] or 'Any'}")
                    criteria_cols[1].write(f"**Job Titles**\n\n{selected_row['target_titles'] or 'Any'}")
                    criteria_cols[2].write(f"**Seniority**\n\n{selected_row['seniority'] or 'Any'}")
                    criteria_cols = st.columns(3)
                    criteria_cols[0].write(f"**Department**\n\n{selected_row['department'] or 'Any'}")
                    criteria_cols[1].write(f"**Current CMS enrichment target**\n\n{selected_row['current_cms'] or 'Not specified'}")
                    criteria_cols[2].write(f"**Minimum ICP Score (review target)**\n\n{int(selected_row['min_score'])}/100")
                    st.caption("Current CMS is not applied during sourcing. The sales team will run the website technology/CMS enrichment in Clay after reviewing the company list. Minimum ICP Score is a review target, not a Clay Search API filter in this phase.")
                    with st.expander("Email Sequence Instructions"):
                        st.write(
                            selected_row.get("email_sequence_instructions", "")
                            or "No custom instructions added."
                        )

            latest_clay_run, latest_clay_results = load_latest_clay_company_search(selected_id)
            if latest_clay_run:
                st.markdown("#### Clay Company Search Results")
                if latest_clay_run["status"] == "Complete":
                    run_meta_cols = st.columns(3)
                    run_meta_cols[0].metric("Companies Returned", int(latest_clay_run["result_count"]))
                    run_meta_cols[1].metric("More Results Available", "Yes" if latest_clay_run["has_more"] else "No")
                    run_meta_cols[2].metric("Search Status", latest_clay_run["status"])
                    st.caption(f"Clay Search ID: {latest_clay_run['clay_search_id']} · {latest_clay_run['created_at']}")
                    company_results_display = latest_clay_results.copy()
                    company_results_display["domain"] = company_results_display["domain"].fillna("").astype(str).str.strip().apply(
                        lambda value: value if not value or value.startswith(("http://", "https://")) else "https://" + value
                    )
                    st.dataframe(
                        company_results_display.rename(columns={
                            "company_name": "Company Name", "domain": "Domain", "industry": "Industry",
                            "country": "Country", "employee_count": "Employee Count", "company_type": "Company Type",
                            "location": "Location", "linkedin_url": "LinkedIn URL", "annual_revenue": "Annual Revenue",
                        }),
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Domain": st.column_config.LinkColumn("Domain", display_text=r"https?://([^/]+)"),
                            "LinkedIn URL": st.column_config.LinkColumn("LinkedIn URL", display_text="Company LinkedIn"),
                        },
                    )
                    with st.expander("Clay search query sent"):
                        st.code(latest_clay_run["query_text"], language="sql")


                else:
                    st.error(f"Latest Clay search failed: {latest_clay_run['error_message']}")
                    with st.expander("Clay search query sent"):
                        st.code(latest_clay_run["query_text"], language="sql")

            latest_people_run, latest_people_results = load_latest_clay_people_search(selected_id)
            if latest_people_run:
                st.markdown("#### Clay Contact Search Results")
                if latest_people_run["status"] == "Complete":
                    people_cols = st.columns(3)
                    people_cols[0].metric("Contacts Returned", int(latest_people_run["result_count"]))
                    people_cols[1].metric("More Results Available", "Yes" if latest_people_run["has_more"] else "No")
                    people_cols[2].metric("Contact Search Status", latest_people_run["status"])
                    st.caption(f"Clay People Search ID: {latest_people_run['clay_search_id']} · {latest_people_run['created_at']}")
                    if latest_people_run["error_message"]:
                        st.info(latest_people_run["error_message"])
                    st.dataframe(
                        latest_people_results.rename(columns={
                            "full_name": "Contact Name", "first_name": "First Name",
                            "last_name": "Last Name", "job_title": "Job Title",
                            "seniority": "Seniority", "department": "Department",
                            "location": "Person Location", "location_country": "Person Country",
                            "company_name": "Current Company", "company_domain": "Company Domain",
                            "company_linkedin_url": "Company LinkedIn URL",
                            "linkedin_url": "LinkedIn URL",
                        }),
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "LinkedIn URL": st.column_config.LinkColumn("LinkedIn URL", display_text="LinkedIn Profile"),
                            "Company LinkedIn URL": st.column_config.LinkColumn("Company LinkedIn URL", display_text="Company LinkedIn"),
                        },
                    )
                    with st.expander("Clay contact search query sent"):
                        st.code(latest_people_run["query_text"], language="sql")
                    debug_text = latest_people_run.get("debug_json", "")
                    if debug_text:
                        try:
                            contact_debug = json.loads(debug_text)
                        except (TypeError, ValueError):
                            contact_debug = {}
                        if contact_debug:
                            with st.expander("Contact search diagnostics"):
                                st.write({
                                    "Raw profiles received from Clay": contact_debug.get("raw_profile_count", 0),
                                    "Profiles with a parsed job title": contact_debug.get("profiles_with_parsed_title_count", 0),
                                    "Profiles with a detected current role": contact_debug.get("profiles_with_current_experience_count", 0),
                                    "Title matching": contact_debug.get("title_filtering", "Applied by Clay Search API"),
                                    "Rejected for conflicting employer": contact_debug.get("employer_mismatch_rejected_count", 0),
                                })
                                st.caption("Job-title matching is applied by Clay's Search API using its smart matching mode where available.")
                else:
                    st.error(f"Latest Clay contact search failed: {latest_people_run['error_message']}")
                    with st.expander("Clay contact search query sent"):
                        st.code(latest_people_run["query_text"], language="sql")
            # Delete is the only campaign action that requires confirmation.
            pending_action = st.session_state.get("pending_campaign_action")
            pending_action_id = st.session_state.get("pending_campaign_action_id")
            if pending_action == "delete" and pending_action_id == selected_id:
                show_campaign_delete_dialog(selected_id, selected_name)

            if (
                st.session_state.get("campaign_action_confirmed")
                and st.session_state.get("campaign_action_confirmed_id") == selected_id
                and pending_action == "delete"
                and pending_action_id == selected_id
            ):
                log_activity(
                    "Campaign deleted",
                    selected_id,
                    selected_name,
                    selected_owner,
                    "Campaign and its locally stored Clay search results deleted.",
                )
                conn.execute("DELETE FROM leads WHERE campaign_id = ?", (selected_id,))
                conn.execute("DELETE FROM clay_company_results WHERE campaign_id = ?", (selected_id,))
                conn.execute("DELETE FROM clay_people_results WHERE campaign_id = ?", (selected_id,))
                conn.execute("DELETE FROM clay_search_runs WHERE campaign_id = ?", (selected_id,))
                conn.execute("DELETE FROM clay_people_search_runs WHERE campaign_id = ?", (selected_id,))
                conn.execute("DELETE FROM campaigns WHERE id = ?", (selected_id,))
                conn.commit()
                st.session_state.pop("pending_campaign_action", None)
                st.session_state.pop("pending_campaign_action_id", None)
                st.session_state.pop("campaign_action_confirmed", None)
                st.session_state.pop("campaign_action_confirmed_id", None)
                st.session_state.pop("editing_campaign_id", None)
                st.session_state["campaign_delete_notice"] = (
                    "Campaign and its locally stored search results have been deleted."
                )
                st.session_state.pop("overview_campaign", None)
                st.session_state.pop("_force_campaign_selection", None)
                st.session_state["_reset_campaign_preview_widget"] = True
                st.rerun()


elif active_page == "Review & Approvals":
    st.subheader("Review & Approvals")
    st.caption("Review contact records and email drafts associated with each campaign.")
    campaigns = load_campaigns()
    if campaigns.empty:
        if is_mock_admin:
            st.info("Create a campaign, approve its criteria, and run Build Campaign Data first.")
        else:
            st.info("No campaigns have been shared with this mock user.")
    else:
        if st.session_state.get("lead_campaign_selector") not in campaigns["id"].tolist():
            st.session_state["lead_campaign_selector"] = campaigns.iloc[0]["id"]
        selected_campaign_id = st.selectbox(
            "Campaign",
            campaigns["id"].tolist(),
            format_func=lambda item: campaign_label(item, campaigns),
            key="lead_campaign_selector",
        )
        selected_review_permission = get_campaign_permission(selected_campaign_id)
        can_edit_review = selected_review_permission in ("Owner", "Can Edit")
        if not can_edit_review:
            st.info("You have View Only access. You can review drafts but cannot change or approve them.")
        leads = pd.read_sql_query(
            "SELECT * FROM leads WHERE campaign_id = ?",
            conn,
            params=(selected_campaign_id,),
        )
        if leads.empty:
            st.info("No contact records yet. Company search is the first integration step; contact search will be added next.")
        else:
            metric1, metric2, metric3 = st.columns(3)
            metric1.metric("Matching Contacts", len(leads))
            metric2.metric("Qualified", int((leads["qualification"] == "Qualified").sum()))
            metric3.metric("Needs Review", int((leads["review_status"] == "Needs review").sum()))

            visible_columns = [
                "company", "company_type", "industry", "company_cms", "contact_name",
                "title", "department", "seniority", "company_country", "contact_country",
                "company_score", "contact_score", "qualification", "review_status",
            ]
            lead_display_labels = {
                "company": "Company Name",
                "company_type": "Company Type",
                "industry": "Industry",
                "company_cms": "Current CMS",
                "contact_name": "Contact Name",
                "title": "Job Title",
                "department": "Department",
                "seniority": "Seniority",
                "company_country": "Company Country",
                "contact_country": "Contact Country",
                "company_score": "Company ICP Score",
                "contact_score": "Contact ICP Score",
                "qualification": "ICP Qualification",
                "review_status": "Review Status",
            }
            st.dataframe(
                leads[visible_columns].rename(columns=lead_display_labels),
                use_container_width=True,
                hide_index=True,
            )

            contact_id = st.selectbox(
                "Choose contact to review",
                leads["id"].tolist(),
                format_func=lambda lead_id: (
                    leads.loc[leads.id == lead_id, "contact_name"].iloc[0]
                    + " — "
                    + leads.loc[leads.id == lead_id, "company"].iloc[0]
                ),
            )
            row = leads[leads["id"] == contact_id].iloc[0]
            st.markdown(f"**{row['contact_name']} · {row['title']} · {row['company']}**")
            st.caption(
                f"Department: {row['department']} | Seniority: {row['seniority']} | CMS: {row['company_cms']}"
            )
            st.caption(
                f"Qualification: {row['qualification']} | Company score: {row['company_score']} | "
                f"Contact score: {row['contact_score']}"
            )
            st.write("Reason:", row["reason"])

            selected_campaign = campaign_as_dict(selected_campaign_id) or {}
            with st.expander("Email Sequence Instructions"):
                st.write(
                    selected_campaign.get("email_sequence_instructions", "")
                    or "No custom instructions were added to this campaign."
                )
            with st.expander("Email-generation prompt preview"):
                st.caption(
                    "This is a prompt preview only. No enrichment or email sending is triggered here."
                )
                st.code(build_email_sequence_prompt(selected_campaign, row.to_dict()), language="text")

            st.markdown("#### Email Sequence Drafts")
            with st.form(f"email_review_form_{contact_id}"):
                email_values = {}
                for sequence_number in (1, 2, 3):
                    st.markdown(f"**Email {sequence_number}**")
                    email_values[f"email{sequence_number}_subject"] = st.text_input(
                        f"Subject {sequence_number}",
                        value=str(row[f"email{sequence_number}_subject"] or ""),
                    )
                    email_values[f"email{sequence_number}_body"] = st.text_area(
                        f"Body {sequence_number}",
                        value=str(row[f"email{sequence_number}_body"] or ""),
                        height=120,
                    )
                save_drafts = st.form_submit_button("Save Email Drafts", disabled=not can_edit_review)
            if save_drafts:
                conn.execute(
                    """
                    UPDATE leads SET email1_subject = ?, email1_body = ?,
                        email2_subject = ?, email2_body = ?, email3_subject = ?, email3_body = ?
                    WHERE id = ?
                    """,
                    (
                        email_values["email1_subject"], email_values["email1_body"],
                        email_values["email2_subject"], email_values["email2_body"],
                        email_values["email3_subject"], email_values["email3_body"], contact_id,
                    ),
                )
                conn.commit()
                owner = selected_campaign.get("campaign_owner", "Unassigned")
                log_activity(
                    "Email drafts updated",
                    selected_campaign_id,
                    selected_campaign.get("name", ""),
                    owner,
                    f"Updated email drafts for {row['contact_name']}.",
                )
                st.success("Email drafts saved. No email has been sent.")

            if st.button("Approve Contact for Campaign Review", key=f"approve_{contact_id}", disabled=not can_edit_review):
                conn.execute(
                    "UPDATE leads SET review_status = ? WHERE id = ?",
                    ("Approved for campaign review", contact_id),
                )
                conn.commit()
                log_activity(
                    "Contact approved for review",
                    selected_campaign_id,
                    selected_campaign.get("name", ""),
                    selected_campaign.get("campaign_owner", "Unassigned"),
                    f"Approved contact: {row['contact_name']}.",
                )
                st.success("Contact marked as approved. No email has been sent.")

            st.info(
                "Clay company search is connected separately. Contact search, enrichment, and email sending are not part of this first integration test."
            )

elif active_page == "Team & Access":
    st.subheader("Team & Access")
    st.caption("Share the AI SDR dashboard with your team and manage their access.")

    if is_mock_admin:
        with st.container(border=True):
            st.markdown("### Share Dashboard")
            st.caption("Invite a team member to access the dashboard. The permission applies to all campaigns.")
            with st.form("share_dashboard_form", enter_to_submit=False):
                share_cols = st.columns([2.4, 1.8, 0.72], gap="medium")
                with share_cols[0]:
                    share_email = st.text_input(
                        "Email ID *", placeholder="e.g., john@company.com", label_visibility="visible"
                    )
                with share_cols[1]:
                    share_access = st.selectbox(
                        "Dashboard access *", ["View", "Edit"], index=None,
                        placeholder="Select access", label_visibility="visible",
                        help="View can access campaigns and results. Edit can also change campaign details and approve records.",
                    )
                with share_cols[2]:
                    st.markdown("<div style='height: 1.82rem'></div>", unsafe_allow_html=True)
                    share_submit = st.form_submit_button("Share", type="primary", use_container_width=True)

            if share_submit:
                email_value = str(share_email or "").strip().lower()
                if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email_value):
                    st.error("Enter a valid email address.")
                elif not share_access:
                    st.error("Select View or Edit access.")
                elif not invitation_email_is_configured():
                    st.error(
                        "Invitation email is not configured. Add the SMTP settings shown below to Streamlit Secrets before sharing."
                    )
                else:
                    existing = conn.execute(
                        "SELECT invitation_status FROM workspace_access WHERE member_email = ?",
                        (email_value,),
                    ).fetchone()
                    if existing and existing[0] == "Accepted":
                        st.warning("This email already has dashboard access. Change its access level in Shared Users below.")
                    else:
                        permission_value = access_label_to_permission(share_access)
                        # The design asks only for Email ID and Dashboard access. A display name is
                        # inferred from the email prefix for the existing invitation schema/email greeting.
                        inferred_name = email_value.split("@", 1)[0].replace(".", " ").replace("_", " ").replace("-", " ").title()
                        invitation_token = pysecrets.token_urlsafe(32)
                        now = datetime.now()
                        now_text = now.isoformat(timespec="seconds")
                        expiry_text = (now + timedelta(days=7)).isoformat(timespec="seconds")
                        inviter_name = current_mock_user_name
                        conn.execute(
                            """INSERT INTO team_members (email, name, status, created_at)
                               VALUES (?, ?, 'Pending', ?)
                               ON CONFLICT(email) DO UPDATE SET name = excluded.name, status = 'Pending'""",
                            (email_value, inferred_name, now_text),
                        )
                        conn.execute(
                            """INSERT INTO workspace_access
                               (id, member_email, member_name, permission, invitation_token,
                                invitation_status, invited_by, invited_at, expires_at, accepted_at, revoked_at)
                               VALUES (?, ?, ?, ?, ?, 'Pending', ?, ?, ?, NULL, NULL)
                               ON CONFLICT(member_email) DO UPDATE SET
                                   member_name = excluded.member_name,
                                   permission = excluded.permission,
                                   invitation_token = excluded.invitation_token,
                                   invitation_status = 'Pending',
                                   invited_by = excluded.invited_by,
                                   invited_at = excluded.invited_at,
                                   expires_at = excluded.expires_at,
                                   accepted_at = NULL,
                                   revoked_at = NULL""",
                            (
                                str(uuid.uuid4()), email_value, inferred_name, permission_value,
                                invitation_token, inviter_name, now_text, expiry_text,
                            ),
                        )
                        conn.commit()
                        try:
                            send_workspace_invitation_email(
                                inferred_name, email_value, permission_value, inviter_name, invitation_token
                            )
                            log_activity(
                                "Dashboard access shared", None, "Workspace", inviter_name,
                                f"Shared dashboard with {email_value} using {share_access} access.",
                            )
                            st.success(f"Invitation sent to {email_value} with {share_access} access.")
                        except Exception as exc:
                            conn.execute(
                                "UPDATE workspace_access SET invitation_status = 'Email Failed', invitation_token = NULL WHERE member_email = ?",
                                (email_value,),
                            )
                            conn.execute(
                                "UPDATE team_members SET status = 'Inactive' WHERE email = ?", (email_value,)
                            )
                            conn.commit()
                            st.error(f"The invitation could not be emailed: {exc}")

        if not invitation_email_is_configured():
            with st.expander("Email delivery setup", expanded=False):
                st.write("Configure SMTP once to send dashboard invitations by email.")
                st.code(
                    '[email]\nsmtp_server = "smtp.gmail.com"\nsmtp_port = 587\n'
                    'sender_email = "your.account@gmail.com"\n'
                    'app_password = "your-google-app-password"\n'
                    'sender_name = "AI SDR Dashboard"\n'
                    'dashboard_url = "https://your-app-name.streamlit.app"',
                    language="toml",
                )
                st.caption("Use a Google App Password, not your normal Gmail password. Keep these values in Streamlit Secrets.")
                st.markdown("[Google instructions: create an App Password](https://support.google.com/mail/answer/185833)")

        st.markdown("### Shared Users")
        st.caption("People who can access the dashboard and their assigned access levels.")
        search_shared_users = st.text_input(
            "Search by email", placeholder="Search by email...", label_visibility="collapsed",
            key="shared_users_search",
        )
        access_rows = conn.execute(
            """SELECT id, member_name, member_email, permission, invitation_status, invited_at, invited_by
               FROM workspace_access ORDER BY invited_at DESC"""
        ).fetchall()
        if search_shared_users:
            needle = search_shared_users.strip().casefold()
            access_rows = [row for row in access_rows if needle in str(row[2]).casefold()]

        header_cols = st.columns([2.7, 1.15, 1.1, 1.2, 1.15], gap="small")
        header_cols[0].markdown("**Email ID**")
        header_cols[1].markdown("**Dashboard access**")
        header_cols[2].markdown("**Status**")
        header_cols[3].markdown("**Shared on**")
        header_cols[4].markdown("**Actions**")
        st.divider()

        if not access_rows:
            st.info("No one has been invited yet. Share the dashboard using the form above.")
        else:
            for access_row in access_rows:
                access_id, member_name, member_email, current_permission, invitation_status, invited_at, invited_by = access_row
                row_cols = st.columns([2.7, 1.15, 1.1, 1.2, 1.15], gap="small")
                row_cols[0].write(member_email)
                with row_cols[1]:
                    current_label = permission_to_access_label(current_permission)
                    new_access_label = st.selectbox(
                        "Dashboard access", ["View", "Edit"],
                        index=["View", "Edit"].index(current_label),
                        key=f"workspace_access_select_{access_id}",
                        label_visibility="collapsed",
                    )
                row_cols[2].write(invitation_status)
                row_cols[3].write(format_created_date(invited_at))
                action_cols = row_cols[4].columns(2, gap="small")
                if action_cols[0].button("Save", key=f"save_shared_user_{access_id}", help="Save access level"):
                    permission_value = access_label_to_permission(new_access_label)
                    if invitation_status == "Revoked":
                        st.error("This access has been revoked. Share the dashboard again to re-invite this person.")
                    elif invitation_status in ("Pending", "Email Failed", "Expired"):
                        # Re-issue a fresh invitation when changing permission for a pending user.
                        if not invitation_email_is_configured():
                            st.error("Configure invitation email before updating a pending invitation.")
                        else:
                            new_token = pysecrets.token_urlsafe(32)
                            now = datetime.now()
                            now_text = now.isoformat(timespec="seconds")
                            expiry_text = (now + timedelta(days=7)).isoformat(timespec="seconds")
                            conn.execute(
                                "UPDATE workspace_access SET permission = ?, invitation_token = ?, invitation_status = 'Pending', invited_at = ?, expires_at = ?, accepted_at = NULL WHERE id = ?",
                                (permission_value, new_token, now_text, expiry_text, access_id),
                            )
                            conn.commit()
                            try:
                                send_workspace_invitation_email(member_name, member_email, permission_value, invited_by, new_token)
                                st.success(f"Access updated and a new invitation sent to {member_email}.")
                            except Exception as exc:
                                conn.execute(
                                    "UPDATE workspace_access SET invitation_status = 'Email Failed', invitation_token = NULL WHERE id = ?",
                                    (access_id,),
                                )
                                conn.commit()
                                st.error(f"Access was saved, but the updated invitation could not be emailed: {exc}")
                    else:
                        conn.execute(
                            "UPDATE workspace_access SET permission = ? WHERE id = ?",
                            (permission_value, access_id),
                        )
                        conn.commit()
                        log_activity(
                            "Dashboard access updated", None, "Workspace", current_mock_user_name,
                            f"Changed {member_email} access to {new_access_label}.",
                        )
                        st.success(f"Dashboard access updated for {member_email}.")
                    st.rerun()

                if action_cols[1].button("Remove", key=f"remove_shared_user_{access_id}", help="Revoke dashboard access"):
                    conn.execute(
                        """UPDATE workspace_access SET invitation_status = 'Revoked', invitation_token = NULL,
                           revoked_at = ? WHERE id = ?""",
                        (datetime.now().isoformat(timespec="seconds"), access_id),
                    )
                    conn.execute("UPDATE team_members SET status = 'Inactive' WHERE email = ?", (member_email,))
                    conn.commit()
                    log_activity(
                        "Dashboard access revoked", None, "Workspace", current_mock_user_name,
                        f"Revoked dashboard access for {member_email}.",
                    )
                    st.success(f"Dashboard access removed for {member_email}.")
                    st.rerun()

                st.caption(f"Shared by {invited_by}")
    else:
        current_access = conn.execute(
            """SELECT permission, invitation_status, invited_by, invited_at, accepted_at
               FROM workspace_access WHERE member_email = ?""",
            (current_mock_user_email,),
        ).fetchone()
        st.markdown("### Your Dashboard Access")
        if current_access:
            permission, invitation_status, invited_by, invited_at, accepted_at = current_access
            st.write(f"**Dashboard access:** {permission_to_access_label(permission)}")
            st.write(f"**Status:** {invitation_status}")
            st.caption(f"Shared by {invited_by} on {format_created_date(invited_at)}")
        else:
            st.info("No dashboard access has been assigned to this test identity.")
        st.caption("Only the dashboard owner can share access or change another user's permission.")

    st.warning(
        "This dashboard still uses Mock Mode identity selection and a local SQLite database. "
        "Invitations can be emailed, but this is not production-grade authentication: users can switch the mock identity. "
        "Use real authentication and a shared database before relying on these permissions for sensitive company data."
    )

elif active_page == "Activity Log":
    st.subheader("Activity Log")
    st.caption("A record of campaign and review actions performed in this dashboard.")
    activity_df = pd.read_sql_query(
        """
        SELECT created_at, actor, action, campaign_name, details
        FROM activity_log
        ORDER BY id DESC
        LIMIT 500
        """,
        conn,
    )
    if activity_df.empty:
        st.info("No activity has been recorded yet.")
    else:
        activity_df["created_at"] = activity_df["created_at"].apply(
            lambda value: datetime.fromisoformat(str(value)).strftime("%d %b %Y %H:%M")
            if value else "—"
        )
        activity_df = activity_df.rename(
            columns={
                "created_at": "Date & Time",
                "actor": "Campaign Owner / Actor",
                "action": "Action",
                "campaign_name": "Campaign",
                "details": "Details",
            }
        )
        st.dataframe(activity_df, use_container_width=True, hide_index=True)

elif active_page == "Settings":
    st.subheader("Settings")
    st.caption("Dashboard mode and integration status")
    settings_cols = st.columns(3)
    settings_cols[0].metric("Execution Mode", "Clay API Test" if get_clay_api_key() else "Test Mode")
    settings_cols[1].metric("Clay API Key", "Configured" if get_clay_api_key() else "Not Configured")
    settings_cols[2].metric(
        "Invitation Email",
        "Configured" if invitation_email_is_configured() else "Not Configured",
    )
    st.markdown("#### Connect Clay")
    st.write("Build Campaign Data uses Clay's Public Search API to find companies and people, then sends the resulting rows to pre-created Clay webhook tables in the campaign's workbook.")
    st.write("To connect it, create a Clay API key in your Clay workspace under API and CLI → API keys, then add it to Streamlit Cloud → App settings → Secrets:")
    st.code('[clay]\napi_key = "PASTE_YOUR_CLAY_API_KEY_HERE"', language="toml")
    st.caption("Keep the key in Streamlit Secrets. Do not paste it into the dashboard, GitHub source code, or this chat.")
    st.markdown("#### Integration scope")
    st.write("- Company search applies Industry and Company Country. Contact search is scoped to the discovered companies and applies Job Titles, Department, Seniority/Job Level, and Contact Country.")
    st.write("- Current CMS, work email, phone, and other enrichment are intentionally left for sales to run manually in Clay after list review.")
    st.write("- The workbook and its Companies/Contacts webhook tables must be created in Clay first. Add the workbook URL and both webhook URLs to the campaign.")
    st.write("- Search results are also retained in the dashboard's SQLite database for run history and diagnostics.")
    st.write(f"- The search collector retrieves up to {get_clay_search_result_cap()} companies and {get_clay_search_result_cap()} contacts per search. The safe default is 50; raise it only after confirming the Clay workspace plan.")
    st.write("- Email drafts are not sent. Team invitations can be emailed when SMTP is configured in Streamlit Secrets.")

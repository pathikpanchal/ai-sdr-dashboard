import streamlit as st
import pandas as pd
import sqlite3
import uuid
import html
import re
import ssl
import smtplib
import secrets as pysecrets
from email.message import EmailMessage
from email.utils import formataddr
from datetime import datetime, timedelta
from pathlib import Path

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
    div[data-testid="stToolbarActionButton"]:has(button[aria-label="Share"]),
    div[data-testid="stToolbarActionButton"]:has(button[title="Share"]),
    div[data-testid="stToolbarActionButton"]:has(a[aria-label="Share"]),
    div[data-testid="stToolbarActionButton"]:has(a[title="Share"]),
    div.stToolbarActionButton:has(button[aria-label="Share"]),
    div.stToolbarActionButton:has(button[title="Share"]) {
        display: none !important;
    }
    div.st-key-toolbar_share_button {
        position: fixed !important;
        top: 0.12rem !important;
        right: 12.5rem !important;
        z-index: 1000001 !important;
        width: auto !important;
        margin: 0 !important;
    }
    div.st-key-toolbar_share_button button {
        min-height: 1.85rem !important;
        height: 1.85rem !important;
        width: auto !important;
        padding: 0 0.45rem !important;
        border: 0 !important;
        border-radius: 0.35rem !important;
        background: transparent !important;
        color: var(--text-color) !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        box-shadow: none !important;
    }
    div.st-key-toolbar_share_button button:hover {
        background: rgba(128, 128, 128, 0.12) !important;
    }

    /* Compact, content-sized Create Campaign action. */
    div.st-key-create_campaign_button button {
        min-height: 2rem !important;
        height: 2rem !important;
        width: auto !important;
        min-width: 0 !important;
        padding: 0.2rem 0.6rem !important;
        font-size: 0.82rem !important;
        font-weight: 600 !important;
    }

    [data-testid="stMetricValue"] {font-size: 1.8rem;}
    [data-testid="stMetricLabel"] {font-size: 0.95rem;}
    div[data-testid="stMarkdownContainer"] p {font-size: 1rem; line-height: 1.45;}
    div[data-testid="stCaptionContainer"] p {font-size: 0.92rem;}
    section[data-testid="stSidebar"] {background: #101b35;}
    section[data-testid="stSidebar"] * {color: #f4f6fb;}
    section[data-testid="stSidebar"] [data-testid="stRadio"] label {padding: 0.45rem 0.55rem; border-radius: 0.5rem;}
    section[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {background: rgba(124, 92, 255, 0.22);}
    div.stButton > button[kind="primary"] {background: #5b35d5; border-color: #5b35d5;}
    </style>
    """,
    unsafe_allow_html=True,
)

SENIORITY_OPTIONS = ["Manager", "Head", "Director", "VP", "C-Suite", "Owner / Founder"]
JOB_LEVEL_OPTIONS = ["Above", "Any", "Below", "Exact"]

# This ordering is used only to interpret Above / Below in this MVP.
# Above includes the selected level itself and every level ranked higher.
SENIORITY_RANK = {
    "Manager": 1,
    "Head": 2,
    "Director": 3,
    "VP": 4,
    "C-Suite": 5,
    "Owner / Founder": 6,
}


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

    # Add new columns safely to databases created by the earlier dashboard version.
    migrations = {
        "campaigns": {
            "current_cms": "TEXT DEFAULT ''",
            "department": "TEXT DEFAULT ''",
            "seniority": "TEXT DEFAULT 'Manager'",
            "job_level": "TEXT DEFAULT 'Above'",
            "email_sequence_instructions": "TEXT DEFAULT ''",
            "clay_table_url": "TEXT DEFAULT ''",
            "campaign_owner": "TEXT DEFAULT 'Unassigned'",
        },
        "leads": {
            "industry": "TEXT DEFAULT ''",
            "company_cms": "TEXT DEFAULT ''",
            "department": "TEXT DEFAULT ''",
            "seniority": "TEXT DEFAULT ''",
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


def normalize(value):
    return " ".join(str(value or "").strip().lower().split())


def split_filter_values(query):
    """Split a multi-value filter on commas or semicolons and normalize each option."""
    raw = str(query or "").replace(";", ",").replace("\n", ",")
    return [normalize(part) for part in raw.split(",") if normalize(part)]


def text_filter_matches(query, *values):
    """Match any comma/semicolon-separated option; blank means no restriction."""
    options = split_filter_values(query)
    if not options:
        return True

    def normalize_industry_terms(value):
        value = normalize(value)
        # Treat common singular/plural forms as equivalent for industry matching.
        value = value.replace("pharmaceuticals", "pharmaceutical")
        value = value.replace("retails", "retail")
        return value

    options = [normalize_industry_terms(option) for option in options]
    searchable = [
        normalize_industry_terms(value)
        for value in values
        if normalize_industry_terms(value)
    ]
    return any(option in item or item in option for option in options for item in searchable)


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


def country_filter_matches(query, country):
    """Match any supplied country name or abbreviation using canonical country names."""
    options = split_filter_values(query)
    if not options:
        return True

    actual_country = normalize_country_name(country)
    normalized_options = [normalize_country_name(option) for option in options]
    return actual_country in normalized_options



def job_title_filter_matches(query, title):
    """Match job titles, including common executive-title abbreviations."""
    title_aliases = {
        "cmo": "chief marketing officer",
        "ceo": "chief executive officer",
        "cfo": "chief financial officer",
        "cto": "chief technology officer",
        "coo": "chief operating officer",
        "svp": "senior vice president",
        "evp": "executive vice president",
    }
    options = split_filter_values(query)
    if not options:
        return True
    expanded_options = []
    for option in options:
        expanded_options.append(option)
        if option in title_aliases:
            expanded_options.append(title_aliases[option])
    return text_filter_matches(", ".join(expanded_options), title)


def classify_seniority(title):
    title_norm = normalize(title)
    if any(term in title_norm for term in ["owner", "founder", "co-founder"]):
        return "Owner / Founder"
    if any(term in title_norm for term in ["chief", "c-suite", "ceo", "cmo", "cfo", "cto", "coo"]):
        return "C-Suite"
    if any(term in title_norm for term in ["vice president", "vp ", "vp,", "svp", "evp"]):
        return "VP"
    if "head" in title_norm:
        return "Head"
    if "director" in title_norm:
        return "Director"
    if "manager" in title_norm:
        return "Manager"
    return "Manager"


def seniority_matches(selected_seniority, job_level, actual_seniority):
    if job_level == "Any":
        return True

    if isinstance(selected_seniority, (list, tuple, set)):
        selected_levels = list(selected_seniority)
    else:
        selected_levels = split_filter_values(selected_seniority)

    selected_ranks = [
        SENIORITY_RANK[level]
        for level in selected_levels
        if level in SENIORITY_RANK
    ]
    if not selected_ranks:
        return True

    actual_rank = SENIORITY_RANK.get(actual_seniority, 1)
    if job_level == "Above":
        # With multiple selected levels, use the lowest selected level as the baseline.
        return actual_rank >= min(selected_ranks)
    if job_level == "Below":
        # With multiple selected levels, use the highest selected level as the baseline.
        return actual_rank <= max(selected_ranks)
    return actual_rank in selected_ranks  # Exact


def synthetic_records():
    # All records below are fictional. They are used only in Mock Mode.
    return [
        {
            "company": "Northbridge Pharma Group",
            "website": "https://northbridge.example",
            "company_type": "Pharmaceutical manufacturer and distributor",
            "industry": "Pharmaceuticals",
            "company_country": "United Kingdom",
            "company_cms": "WordPress",
            "contact_name": "Amelia Carter",
            "title": "Head of Marketing",
            "department": "Marketing",
            "contact_country": "United Kingdom",
            "email": "amelia.carter@northbridge.example",
            "company_score": 94,
            "contact_score": 92,
            "reason": "Pharmaceutical business with a senior marketing decision-maker.",
        },
        {
            "company": "Westhaven Pharmaceutical Services",
            "website": "https://westhaven.example",
            "company_type": "Pharmaceutical services provider",
            "industry": "Pharmaceutical Services",
            "company_country": "United Kingdom",
            "company_cms": "Drupal",
            "contact_name": "Oliver Bennett",
            "title": "Marketing Director",
            "department": "Marketing",
            "contact_country": "United Kingdom",
            "email": "oliver.bennett@westhaven.example",
            "company_score": 88,
            "contact_score": 89,
            "reason": "UK pharmaceutical services business with a marketing director.",
        },
        {
            "company": "Crownwell Pharma Distribution",
            "website": "https://crownwell.example",
            "company_type": "Pharmaceutical wholesaler and distributor",
            "industry": "Pharmaceuticals",
            "company_country": "United Kingdom",
            "company_cms": "Sitecore",
            "contact_name": "Sophie Williams",
            "title": "Chief Marketing Officer",
            "department": "Marketing",
            "contact_country": "United Kingdom",
            "email": "sophie.williams@crownwell.example",
            "company_score": 91,
            "contact_score": 96,
            "reason": "UK pharmaceutical distributor with an executive marketing owner.",
        },
        {
            "company": "Harborview Pharma Ltd",
            "website": "https://harborview.example",
            "company_type": "Pharmaceutical manufacturer",
            "industry": "Pharmaceuticals",
            "company_country": "United Kingdom",
            "company_cms": "WordPress",
            "contact_name": "Isabella Reed",
            "title": "Marketing Manager",
            "department": "Marketing",
            "contact_country": "United Kingdom",
            "email": "isabella.reed@harborview.example",
            "company_score": 90,
            "contact_score": 84,
            "reason": "UK pharmaceutical manufacturer with a marketing manager.",
        },
        {
            "company": "Meridian BioHealth",
            "website": "https://meridianbio.example",
            "company_type": "Biotechnology research company",
            "industry": "Biotechnology",
            "company_country": "United Kingdom",
            "company_cms": "Webflow",
            "contact_name": "Noah Hughes",
            "title": "VP Marketing",
            "department": "Marketing",
            "contact_country": "United Kingdom",
            "email": "noah.hughes@meridianbio.example",
            "company_score": 62,
            "contact_score": 88,
            "reason": "Biotechnology-only profile; separate from the pharmaceutical industry filter.",
        },
        {
            "company": "Ironcrest Industrial Manufacturing",
            "website": "https://ironcrest.example",
            "company_type": "Industrial equipment manufacturer",
            "industry": "Industrial Manufacturing",
            "company_country": "United Kingdom",
            "company_cms": "HubSpot",
            "contact_name": "Ethan Cole",
            "title": "Head of Marketing",
            "department": "Marketing",
            "contact_country": "United Kingdom",
            "email": "ethan.cole@ironcrest.example",
            "company_score": 25,
            "contact_score": 85,
            "reason": "Generic industrial manufacturer; not a pharmaceutical business.",
        },
        {
            "company": "Brightwell Retail Group",
            "website": "https://brightwell-retail.example",
            "company_type": "Multi-channel retail company",
            "industry": "Retail",
            "company_country": "United Kingdom",
            "company_cms": "Shopify",
            "contact_name": "Grace Morgan",
            "title": "Marketing Director",
            "department": "Marketing",
            "contact_country": "United Kingdom",
            "email": "grace.morgan@brightwell-retail.example",
            "company_score": 89,
            "contact_score": 91,
            "reason": "UK retail business with a senior marketing decision-maker.",
        },
        {
            "company": "Northstar Consumer Retail",
            "website": "https://northstar-retail.example",
            "company_type": "Retail and ecommerce group",
            "industry": "Retail",
            "company_country": "United Kingdom",
            "company_cms": "Magento",
            "contact_name": "Daniel Foster",
            "title": "Chief Marketing Officer",
            "department": "Marketing",
            "contact_country": "United Kingdom",
            "email": "daniel.foster@northstar-retail.example",
            "company_score": 92,
            "contact_score": 94,
            "reason": "UK retail and ecommerce group with an executive marketing owner.",
        },
        {
            "company": "Alpine Pharma Europe",
            "website": "https://alpine.example",
            "company_type": "Pharmaceutical manufacturer",
            "industry": "Pharmaceuticals",
            "company_country": "Germany",
            "company_cms": "WordPress",
            "contact_name": "Lucas Meyer",
            "title": "VP Marketing",
            "department": "Marketing",
            "contact_country": "Germany",
            "email": "lucas.meyer@alpine.example",
            "company_score": 86,
            "contact_score": 94,
            "reason": "Pharmaceutical company, but outside the requested geography.",
        },
    ]


def run_mock_research(campaign):
    results = []
    records = synthetic_records()

    for record in records:
        if not text_filter_matches(
            campaign["industry"], record["industry"], record["company_type"]
        ):
            continue
        if not country_filter_matches(campaign["company_country"], record["company_country"]):
            continue
        if not country_filter_matches(campaign["contact_country"], record["contact_country"]):
            continue
        if not text_filter_matches(campaign["current_cms"], record["company_cms"]):
            continue
        if not text_filter_matches(campaign["department"], record["department"]):
            continue
        if not job_title_filter_matches(campaign.get("target_titles", ""), record["title"]):
            continue

        actual_seniority = classify_seniority(record["title"])
        if not seniority_matches(
            campaign["seniority"], campaign["job_level"], actual_seniority
        ):
            continue

        threshold = int(campaign["min_score"])
        qualification = (
            "Qualified"
            if record["company_score"] >= threshold and record["contact_score"] >= threshold
            else "Review / Exclude"
        )

        first_name = record["contact_name"].split()[0]
        results.append(
            {
                "id": str(uuid.uuid4()),
                "campaign_id": campaign["id"],
                "company": record["company"],
                "website": record["website"],
                "company_type": record["company_type"],
                "industry": record["industry"],
                "company_country": record["company_country"],
                "contact_name": record["contact_name"],
                "title": record["title"],
                "contact_country": record["contact_country"],
                "email": record["email"],
                "company_score": record["company_score"],
                "contact_score": record["contact_score"],
                "qualification": qualification,
                "reason": record["reason"],
                "email1_subject": f"A thought for {record['company']}'s marketing team",
                "email1_body": (
                    f"Hi {first_name},\n\n"
                    f"I was looking at {record['company']} and thought it could be worth "
                    "comparing notes on how pharmaceutical businesses are approaching marketing.\n\n"
                    "Would you be open to a brief conversation?"
                ),
                "email2_subject": f"Re: marketing priorities at {record['company']}",
                "email2_body": (
                    f"Hi {first_name},\n\n"
                    "Following up in case this is relevant. We help teams review their current "
                    "approach and identify practical opportunities to improve results.\n\n"
                    "Would a short overview be useful?"
                ),
                "email3_subject": "Should I close the loop?",
                "email3_body": (
                    f"Hi {first_name},\n\n"
                    "I appreciate you may have other priorities. Should I close the loop for now, "
                    "or would a short conversation be worthwhile?"
                ),
                "review_status": "Needs review",
                "company_cms": record["company_cms"],
                "department": record["department"],
                "seniority": actual_seniority,
            }
        )
    return results



def mock_research_diagnostics(campaign):
    """Return remaining mock-record counts after each campaign filter."""
    remaining = synthetic_records()
    diagnostics = [("Available mock records", len(remaining))]

    def apply_filter(label, predicate):
        nonlocal remaining
        remaining = [record for record in remaining if predicate(record)]
        diagnostics.append((label, len(remaining)))

    apply_filter(
        "Industry",
        lambda record: text_filter_matches(
            campaign["industry"], record["industry"], record["company_type"]
        ),
    )
    apply_filter(
        "Company country",
        lambda record: country_filter_matches(
            campaign["company_country"], record["company_country"]
        ),
    )
    apply_filter(
        "Contact country",
        lambda record: country_filter_matches(
            campaign["contact_country"], record["contact_country"]
        ),
    )
    apply_filter(
        "Current CMS",
        lambda record: text_filter_matches(
            campaign["current_cms"], record["company_cms"]
        ),
    )
    apply_filter(
        "Department",
        lambda record: text_filter_matches(
            campaign["department"], record["department"]
        ),
    )
    apply_filter(
        "Job Titles",
        lambda record: job_title_filter_matches(
            campaign.get("target_titles", ""), record["title"]
        ),
    )
    apply_filter(
        "Seniority / job level",
        lambda record: seniority_matches(
            campaign["seniority"],
            campaign["job_level"],
            classify_seniority(record["title"]),
        ),
    )
    return diagnostics



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


def insert_mock_research_results(campaign_id, records):
    """Replace a campaign's mock results and update its status."""
    conn.execute("DELETE FROM leads WHERE campaign_id = ?", (campaign_id,))
    if records:
        conn.executemany(
            """
            INSERT INTO leads
            (id, campaign_id, company, website, company_type, industry, company_country,
             contact_name, title, contact_country, email, company_score, contact_score,
             qualification, reason, email1_subject, email1_body, email2_subject,
             email2_body, email3_subject, email3_body, review_status,
             company_cms, department, seniority)
            VALUES
            (:id, :campaign_id, :company, :website, :company_type, :industry, :company_country,
             :contact_name, :title, :contact_country, :email, :company_score, :contact_score,
             :qualification, :reason, :email1_subject, :email1_body, :email2_subject,
             :email2_body, :email3_subject, :email3_body, :review_status,
             :company_cms, :department, :seniority)
            """,
            records,
        )
    new_status = "Draft ready" if records else "No matches"
    conn.execute(
        "UPDATE campaigns SET status = ? WHERE id = ?",
        (new_status, campaign_id),
    )
    conn.commit()
    return new_status


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
    st.markdown('<div class="mock-mode-badge">MOCK MODE — ON</div>', unsafe_allow_html=True)
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

@st.dialog("Share AI SDR Dashboard", width="small")
def show_share_dialog():
    st.caption("Manage workspace access. Permissions apply to all current and future campaigns.")

    if is_mock_admin:
        st.markdown("#### Invite people")
        with st.form("header_share_invitation_form"):
            share_name = st.text_input("Name", key="header_share_name")
            share_email = st.text_input("Email address", key="header_share_email")
            share_permission = st.selectbox(
                "Permission",
                ["View Only", "Can Edit"],
                index=None,
                placeholder="Select permission",
                key="header_share_permission",
            )
            share_invite = st.form_submit_button("Send invite", type="primary", use_container_width=True)

        if share_invite:
            email_value = share_email.strip().lower()
            if not share_name.strip():
                st.error("Please enter the person's name.")
            elif not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email_value):
                st.error("Please enter a valid email address.")
            elif not share_permission:
                st.error("Please select View Only or Can Edit.")
            elif not invitation_email_is_configured():
                st.error("Invitation email is not configured. Set it up in Team & Access first.")
            else:
                invitation_token = pysecrets.token_urlsafe(32)
                now = datetime.now()
                now_text = now.isoformat(timespec="seconds")
                expiry_text = (now + timedelta(days=7)).isoformat(timespec="seconds")
                try:
                    conn.execute(
                        """
                        INSERT INTO team_members (email, name, status, created_at)
                        VALUES (?, ?, 'Pending', ?)
                        ON CONFLICT(email) DO UPDATE SET name = excluded.name, status = 'Pending'
                        """,
                        (email_value, share_name.strip(), now_text),
                    )
                    conn.execute(
                        """
                        INSERT INTO workspace_access
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
                            revoked_at = NULL
                        """,
                        (
                            str(uuid.uuid4()), email_value, share_name.strip(), share_permission,
                            invitation_token, current_mock_user_name, now_text, expiry_text,
                        ),
                    )
                    conn.commit()
                    send_workspace_invitation_email(
                        share_name.strip(), email_value, share_permission,
                        current_mock_user_name, invitation_token
                    )
                    log_activity(
                        "Workspace invitation sent",
                        None,
                        "Workspace",
                        current_mock_user_name,
                        f"Invitation sent to {email_value} with {share_permission} access to all campaigns.",
                    )
                    st.success(f"Invitation sent to {email_value}.")
                    st.rerun()
                except Exception as exc:
                    conn.execute(
                        "UPDATE workspace_access SET invitation_status = 'Email Failed', invitation_token = NULL WHERE member_email = ?",
                        (email_value,),
                    )
                    conn.execute(
                        "UPDATE team_members SET status = 'Inactive' WHERE email = ?",
                        (email_value,),
                    )
                    conn.commit()
                    st.error(f"Could not send the invitation: {exc}")

        with st.expander("Manage existing access", expanded=False):
            access_rows = conn.execute(
                """
                SELECT id, member_name, member_email, permission, invitation_status,
                       invited_at, accepted_at
                FROM workspace_access
                ORDER BY invited_at DESC
                """
            ).fetchall()

            if not access_rows:
                st.info("No one has been invited yet.")
            else:
                for row in access_rows:
                    access_id, member_name, member_email, current_permission, invitation_status, invited_at, accepted_at = row
                    with st.container(border=True):
                        name_col, email_col = st.columns([1, 1.7])
                        name_col.write(f"**{member_name}**")
                        email_col.write(member_email)
                        permission_col, status_col = st.columns([1, 1])
                        with permission_col:
                            new_permission = st.selectbox(
                                "Access",
                                ["View Only", "Can Edit"],
                                index=["View Only", "Can Edit"].index(current_permission),
                                key=f"header_share_permission_{access_id}",
                            )
                        status_col.write(f"**Status:** {invitation_status}")
                        action_col, revoke_col = st.columns([1, 1])
                        with action_col:
                            if st.button("Save access", key=f"header_share_save_{access_id}"):
                                conn.execute(
                                    "UPDATE workspace_access SET permission = ? WHERE id = ?",
                                    (new_permission, access_id),
                                )
                                conn.commit()
                                if invitation_status == "Pending":
                                    latest = conn.execute(
                                        """
                                        SELECT invitation_token, member_name, member_email, invited_by
                                        FROM workspace_access WHERE id = ?
                                        """,
                                        (access_id,),
                                    ).fetchone()
                                    try:
                                        send_workspace_invitation_email(
                                            latest[1], latest[2], new_permission, latest[3], latest[0]
                                        )
                                        st.success("Permission updated and revised invitation sent.")
                                    except Exception as exc:
                                        st.error(f"Permission updated, but revised email could not be sent: {exc}")
                                else:
                                    st.success("Permission updated for all campaigns.")
                                st.rerun()
                        with revoke_col:
                            if invitation_status != "Revoked":
                                if st.button("Revoke access", key=f"header_share_revoke_{access_id}"):
                                    now_text = datetime.now().isoformat(timespec="seconds")
                                    conn.execute(
                                        """
                                        UPDATE workspace_access
                                        SET invitation_status = 'Revoked',
                                            invitation_token = NULL,
                                            revoked_at = ?
                                        WHERE id = ?
                                        """,
                                        (now_text, access_id),
                                    )
                                    conn.execute(
                                        "UPDATE team_members SET status = 'Inactive' WHERE email = ?",
                                        (member_email,),
                                    )
                                    conn.commit()
                                    log_activity(
                                        "Workspace access revoked",
                                        None,
                                        "Workspace",
                                        current_mock_user_name,
                                        f"Revoked all-campaign access for {member_email}.",
                                    )
                                    st.success(f"Access revoked for {member_email}.")
                                    st.rerun()
                        st.caption(
                            f"Invited: {format_created_date(invited_at)}"
                            + (f" · Accepted: {format_created_date(accepted_at)}" if accepted_at else "")
                        )
    else:
        current_access = conn.execute(
            """
            SELECT permission, invitation_status
            FROM workspace_access WHERE member_email = ?
            """,
            (current_mock_user_email,),
        ).fetchone()
        if current_access and current_access[1] == "Accepted":
            st.write(f"**Your access:** {current_access[0]}")
            st.caption("This permission applies across all campaigns.")
        else:
            st.info("You do not have active workspace access.")

    if st.button("Open full Team & Access settings", key="header_open_team_access"):
        st.session_state["main_navigation"] = "Team & Access"
        st.rerun()




previous_mock_identity = st.session_state.get("_previous_mock_user_email", current_mock_user_email)
if previous_mock_identity != current_mock_user_email:
    for state_key in (
        "pending_campaign_action",
        "pending_campaign_action_id",
        "editing_campaign_id",
    ):
        st.session_state.pop(state_key, None)
    st.session_state.pop("overview_campaign", None)
    st.session_state["_reset_campaign_preview_widget"] = True
    st.session_state["_previous_mock_user_email"] = current_mock_user_email

# Show saved notices after navigation reruns.
campaign_edit_notice = st.session_state.pop("campaign_edit_notice", None)
if campaign_edit_notice and active_page in ("Campaigns", "Review & Approvals"):
    st.success(campaign_edit_notice)

last_research_notice = st.session_state.pop("last_research_notice", None)
if last_research_notice and active_page == "Campaigns":
    if last_research_notice["found"]:
        st.success(
            f"Mock research complete: {last_research_notice['count']} matching contacts found; "
            f"{last_research_notice['qualified_count']} passed the ICP score threshold."
        )
    else:
        st.warning(
            "No sample records matched all selected filters. No Clay search was performed."
        )
        with st.expander("Why were no records found? — filter diagnostics", expanded=True):
            st.caption("Counts show how many fictional sample records remain after each filter.")
            for filter_name, remaining_count in last_research_notice["diagnostics"]:
                st.write(f"**{filter_name}:** {remaining_count}")
            st.caption(
                "The minimum ICP score labels records as Qualified or Review / Exclude; "
                "it does not remove them from the results."
            )


def campaign_as_dict(campaign_id):
    row = conn.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
    if row is None:
        return None
    columns = [item[1] for item in conn.execute("PRAGMA table_info(campaigns)").fetchall()]
    return dict(zip(columns, row))


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
    """Read SMTP settings from Streamlit Secrets; never store credentials in the app database."""
    try:
        config = dict(st.secrets.get("email", {}))
    except Exception:
        config = {}
    return {
        "smtp_server": config.get("smtp_server", "smtp.gmail.com"),
        "smtp_port": int(config.get("smtp_port", 587)),
        "sender_email": config.get("sender_email", "").strip(),
        "app_password": config.get("app_password", "").replace(" ", "").strip(),
        "sender_name": config.get("sender_name", "AI SDR Dashboard").strip(),
        "dashboard_url": config.get("dashboard_url", "").strip().rstrip("/"),
    }


def invitation_email_is_configured():
    config = get_invitation_email_config()
    return bool(config["sender_email"] and config["app_password"] and config["dashboard_url"])


def send_workspace_invitation_email(
    recipient_name, recipient_email, permission, inviter_name, invitation_token
):
    """Send a real workspace invitation email using configured SMTP settings."""
    config = get_invitation_email_config()
    if not config["sender_email"] or not config["app_password"] or not config["dashboard_url"]:
        raise ValueError(
            "Email is not configured. Add sender_email, app_password, and dashboard_url "
            "under [email] in Streamlit Secrets."
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
        f"{inviter_name or 'Workspace Admin'} has invited you to the AI SDR Dashboard workspace.\n\n"
        f"Workspace access: All campaigns\nYour permission: {permission}\n\n"
        f"Accept your invitation using this link:\n{invitation_url}\n\n"
        "This invitation link expires in 7 days.\n"
        "If you were not expecting this invitation, you can ignore this email."
    )
    message.add_alternative(
        f'<html><body style="font-family:Arial,sans-serif;color:#202938;line-height:1.55">'
        f'<p>Hi {safe_name},</p>'
        f'<p><strong>{safe_inviter}</strong> has invited you to the AI SDR Dashboard workspace.</p>'
        f'<p><strong>Workspace access:</strong> All campaigns<br>'
        f'<strong>Your permission:</strong> {safe_permission}</p>'
        f'<p><a href="{safe_url}" style="display:inline-block;background:#5b35d5;color:#fff;'
        f'padding:11px 18px;text-decoration:none;border-radius:6px">Accept Invitation</a></p>'
        f'<p>This invitation link expires in 7 days.</p>'
        f'<p>If you were not expecting this invitation, you can ignore this email.</p>'
        f'</body></html>',
        subtype="html",
    )

    with smtplib.SMTP(config["smtp_server"], config["smtp_port"], timeout=25) as server:
        server.ehlo()
        server.starttls(context=ssl.create_default_context())
        server.ehlo()
        server.login(config["sender_email"], config["app_password"])
        server.send_message(message)


def render_invitation_acceptance():
    """Allow a mock invitee to accept a workspace-wide invitation from the email link."""
    try:
        invitation_token = st.query_params.get("invite")
    except Exception:
        invitation_token = None
    if not invitation_token:
        return

    invitation = conn.execute(
        """
        SELECT id, member_email, member_name, permission, invitation_status,
               invited_by, expires_at
        FROM workspace_access
        WHERE invitation_token = ?
        """,
        (invitation_token,),
    ).fetchone()

    st.divider()
    with st.container(border=True):
        st.subheader("Workspace Invitation")
        if not invitation:
            st.error("This invitation link is invalid or has already been revoked.")
            return

        (
            access_id, member_email, member_name, permission,
            invitation_status, invited_by, expires_at,
        ) = invitation

        if invitation_status == "Accepted":
            st.success("This invitation has already been accepted.")
            return
        if invitation_status != "Pending":
            st.warning("This invitation is no longer active.")
            return

        try:
            is_expired = bool(expires_at) and datetime.fromisoformat(expires_at) < datetime.now()
        except ValueError:
            is_expired = False
        if is_expired:
            conn.execute(
                "UPDATE workspace_access SET invitation_status = 'Expired', invitation_token = NULL WHERE id = ?",
                (access_id,),
            )
            conn.commit()
            st.error("This invitation has expired. Ask the Workspace Admin to send a new one.")
            return

        st.write(f"**Hello, {member_name}!**")
        st.write(f"**Invited by:** {invited_by}")
        st.write("**Workspace access:** All campaigns")
        st.write(f"**Permission:** {permission}")
        st.caption(f"Invitation sent to {member_email}.")
        st.warning(
            "Mock Mode note: accepting activates the simulated user and workspace permission. "
            "It does not verify identity or provide secure authentication."
        )
        if st.button("Accept Invitation", type="primary", key="accept_workspace_invitation"):
            now = datetime.now().isoformat(timespec="seconds")
            conn.execute(
                """
                INSERT INTO team_members (email, name, status, created_at)
                VALUES (?, ?, 'Active', ?)
                ON CONFLICT(email) DO UPDATE SET name = excluded.name, status = 'Active'
                """,
                (member_email, member_name, now),
            )
            conn.execute(
                "UPDATE workspace_access SET invitation_status = 'Accepted', accepted_at = ? WHERE id = ?",
                (now, access_id),
            )
            conn.commit()
            log_activity(
                "Workspace invitation accepted",
                None,
                "Workspace",
                member_name,
                f"{member_email} accepted {permission} access to all campaigns.",
            )
            st.session_state["pending_mock_user_email"] = member_email
            try:
                del st.query_params["invite"]
            except Exception:
                pass
            st.success("Invitation accepted. You are now previewing the dashboard as this mock user.")
            st.rerun()


render_invitation_acceptance()


@st.dialog("Create New Campaign", width="large")
def show_create_campaign_dialog():
    st.caption("Add a campaign name. All targeting filters are optional; leave any field blank to skip it.")

    with st.form("create_campaign_dialog_form"):
        name_col, owner_col = st.columns(2)
        with name_col:
            campaign_name = st.text_input(
                "Campaign Name *",
                value="",
                placeholder="Enter a campaign name",
            )
        with owner_col:
            campaign_owner = st.text_input(
                "Campaign Owner (optional)",
                value="",
                placeholder="Owner's name",
            )

        industry_col, company_country_col, contact_country_col = st.columns(3)
        with industry_col:
            industry = st.text_input("Industry (optional)", value="", placeholder="e.g. Pharmaceuticals")
        with company_country_col:
            company_country = st.text_input("Company Country (optional)", value="", placeholder="e.g. United Kingdom")
        with contact_country_col:
            contact_country = st.text_input("Contact Country (optional)", value="", placeholder="e.g. United Kingdom")

        department_col, titles_col, cms_col = st.columns(3)
        with department_col:
            department = st.text_input("Department (optional)", value="", placeholder="e.g. Marketing")
        with titles_col:
            target_titles = st.text_input(
                "Job Titles (optional)",
                value="",
                placeholder="e.g. CMO, Marketing Director",
                help="Enter multiple titles separated by commas. Leave blank for any job title.",
            )
        with cms_col:
            current_cms = st.text_input("Current CMS (optional)", value="", placeholder="e.g. WordPress")

        seniority_col, job_level_col, threshold_col = st.columns([1.2, 1, 1])
        with seniority_col:
            seniority = st.multiselect("Seniority (optional)", SENIORITY_OPTIONS, default=[])
        with job_level_col:
            job_level = st.selectbox(
                "Job Level (optional)",
                JOB_LEVEL_OPTIONS,
                index=JOB_LEVEL_OPTIONS.index("Any"),
            )
        with threshold_col:
            threshold = st.slider(
                "Minimum ICP score (optional)",
                min_value=0,
                max_value=100,
                value=0,
                help="0 means no minimum score filter.",
            )

        with st.expander("Additional options (optional)", expanded=False):
            clay_table_url = st.text_input(
                "Clay Table Link",
                value="",
                placeholder="Paste a Clay table URL if available",
            )
            email_sequence_instructions = st.text_area(
                "Email Sequence Instructions",
                value="",
                placeholder="Add the campaign goal, audience, tone, personalization and CTA if needed.",
                height=75,
            )

        submitted = st.form_submit_button("Create Campaign", type="primary", use_container_width=True)

    if submitted:
        if not campaign_name.strip():
            st.error("Campaign Name is required. All targeting filters are optional.")
        else:
            campaign_id = str(uuid.uuid4())
            owner_value = campaign_owner.strip() or "Unassigned"
            conn.execute(
                """
                INSERT INTO campaigns
                (id, name, industry, company_country, contact_country, target_titles,
                 min_score, status, created_at, current_cms, department, seniority,
                 job_level, email_sequence_instructions, clay_table_url, campaign_owner)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    campaign_id,
                    campaign_name.strip(),
                    industry.strip(),
                    company_country.strip(),
                    contact_country.strip(),
                    target_titles.strip(),
                    int(threshold),
                    "Draft",
                    datetime.now().isoformat(timespec="seconds"),
                    current_cms.strip(),
                    department.strip(),
                    ", ".join(seniority),
                    job_level,
                    email_sequence_instructions.strip(),
                    clay_table_url.strip(),
                    owner_value,
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


# Single Share control, positioned where Streamlit's native Share action appears.
if st.button("Share", key="toolbar_share_button", type="secondary"):
    show_share_dialog()

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
                "clay_table_url": "List Link (Clay Table)",
            }
        )
        campaign_preview = campaign_preview[
            [
                "id",
                "Campaign Name",
                "Created Date",
                "Campaign Owner",
                "Status",
                "List Link (Clay Table)",
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
                "List Link (Clay Table)": st.column_config.LinkColumn(
                    "List Link (Clay Table)",
                    display_text="Open Clay Table",
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
            action_title, edit_col, duplicate_col, delete_col = st.columns([3.4, 1.3, 1.55, 1.3])
            with action_title:
                st.markdown(f"#### Selected Campaign: {selected_name}")
            selected_permission = get_campaign_permission(selected_id)
            with edit_col:
                if selected_permission in ("Owner", "Can Edit"):
                    if st.button("Edit Campaign", key="selected_edit_campaign", use_container_width=True):
                        st.session_state["pending_campaign_action"] = "edit"
                        st.session_state["pending_campaign_action_id"] = selected_id
                        st.rerun()
                else:
                    st.caption("View Only")
            with duplicate_col:
                if selected_permission in ("Owner", "Can Edit"):
                    if st.button("Duplicate Campaign", key="selected_duplicate_campaign", use_container_width=True):
                        st.session_state["pending_campaign_action"] = "duplicate"
                        st.session_state["pending_campaign_action_id"] = selected_id
                        st.rerun()
            with delete_col:
                if selected_permission == "Owner":
                    if st.button("Delete Campaign", key="selected_delete_campaign", use_container_width=True):
                        st.session_state["pending_campaign_action"] = "delete"
                        st.session_state["pending_campaign_action_id"] = selected_id
                        st.rerun()

            detail_cols = st.columns([1.25, 2.75])
            with detail_cols[0]:
                with st.container(border=True):
                    st.write("**Created Date**", format_created_date(selected_row["created_at"]))
                    st.write("**Campaign Owner**", selected_owner)
                    st.write("**Status**", str(selected_row["status"] or "Draft"))
                    clay_link = str(selected_row.get("clay_table_url", "") or "").strip()
                    if clay_link:
                        st.link_button("Open Clay Table", clay_link, use_container_width=True)
                    else:
                        st.caption("List Link (Clay Table): Not added yet")
            with detail_cols[1]:
                with st.container(border=True):
                    st.markdown("**Campaign Criteria (Filters)**")
                    criteria_cols = st.columns(3)
                    criteria_cols[0].write(f"**Industry**\n\n{selected_row['industry'] or 'Any'}")
                    criteria_cols[1].write(f"**Company Country**\n\n{selected_row['company_country'] or 'Any'}")
                    criteria_cols[2].write(f"**Contact Country**\n\n{selected_row['contact_country'] or 'Any'}")
                    criteria_cols = st.columns(3)
                    criteria_cols[0].write(f"**Job Titles**\n\n{selected_row['target_titles'] or 'Any'}")
                    criteria_cols[1].write(f"**Department**\n\n{selected_row['department'] or 'Any'}")
                    criteria_cols[2].write(f"**Current CMS**\n\n{selected_row['current_cms'] or 'Any'}")
                    criteria_cols = st.columns(3)
                    criteria_cols[0].write(f"**Seniority**\n\n{selected_row['seniority'] or 'Any'}")
                    criteria_cols[1].write(f"**Job Level**\n\n{selected_row['job_level'] or 'Any'}")
                    criteria_cols[2].write(f"**Minimum ICP Score**\n\n{int(selected_row['min_score'])}/100")
                    with st.expander("Email Sequence Instructions"):
                        st.write(
                            selected_row.get("email_sequence_instructions", "")
                            or "No custom instructions added."
                        )

            # A confirmation is always required before any selected-campaign action.
            pending_action = st.session_state.get("pending_campaign_action")
            pending_action_id = st.session_state.get("pending_campaign_action_id")
            if pending_action and pending_action_id == selected_id:
                action_prompts = {
                    "edit": (
                        f"Are you sure you want to edit the '{selected_name}' campaign? "
                        "The campaign criteria editor will open."
                    ),
                    "duplicate": (
                        f"Are you sure you want to duplicate the '{selected_name}' campaign? "
                        "A separate copy will be created and opened in the editor; the original will remain unchanged."
                    ),
                    "delete": (
                        f"Are you sure you want to delete the '{selected_name}' campaign? "
                        "Its associated local mock results will also be deleted. This cannot be undone."
                    ),
                }
                with st.container(border=True):
                    st.warning(action_prompts[pending_action])
                    yes_col, cancel_col = st.columns(2)
                    with yes_col:
                        confirm_label = {
                            "edit": "Yes, Edit Campaign",
                            "duplicate": "Yes, Duplicate Campaign",
                            "delete": "Yes, Delete Campaign",
                        }[pending_action]
                        if st.button(confirm_label, type="primary", key="confirm_selected_campaign_action"):
                            if pending_action == "edit":
                                st.session_state["editing_campaign_id"] = selected_id
                                log_activity("Edit opened", selected_id, selected_name, selected_owner)
                                st.session_state.pop("pending_campaign_action", None)
                                st.session_state.pop("pending_campaign_action_id", None)
                                st.rerun()
                            elif pending_action == "duplicate":
                                new_id = str(uuid.uuid4())
                                new_name = selected_name + " (Copy)"
                                duplicate_owner = selected_owner if is_mock_admin else current_mock_user_name
                                conn.execute(
                                    """
                                    INSERT INTO campaigns
                                    (id, name, industry, company_country, contact_country, target_titles,
                                     min_score, status, created_at, current_cms, department, seniority,
                                     job_level, email_sequence_instructions, clay_table_url, campaign_owner)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    """,
                                    (
                                        new_id,
                                        new_name,
                                        selected_row["industry"] or "",
                                        selected_row["company_country"] or "",
                                        selected_row["contact_country"] or "",
                                        selected_row["target_titles"] or "",
                                        int(selected_row["min_score"]),
                                        "Draft",
                                        datetime.now().isoformat(timespec="seconds"),
                                        selected_row.get("current_cms", "") or "",
                                        selected_row.get("department", "") or "",
                                        selected_row.get("seniority", "Manager") or "Manager",
                                        selected_row.get("job_level", "Above") or "Above",
                                        selected_row.get("email_sequence_instructions", "") or "",
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
                                st.session_state["overview_campaign"] = new_id
                                st.session_state["_force_campaign_selection"] = new_id
                                st.session_state["_reset_campaign_preview_widget"] = True
                                st.session_state["editing_campaign_id"] = new_id
                                st.session_state["campaign_edit_context"] = "duplicate"
                                st.session_state.pop("pending_campaign_action", None)
                                st.session_state.pop("pending_campaign_action_id", None)
                                st.rerun()
                            elif pending_action == "delete":
                                log_activity(
                                    "Campaign deleted",
                                    selected_id,
                                    selected_name,
                                    selected_owner,
                                    "Campaign and associated local mock results deleted.",
                                )
                                conn.execute("DELETE FROM leads WHERE campaign_id = ?", (selected_id,))
                                conn.execute("DELETE FROM campaigns WHERE id = ?", (selected_id,))
                                conn.commit()
                                remaining_ids = [item for item in campaign_ids if item != selected_id]
                                st.session_state.pop("pending_campaign_action", None)
                                st.session_state.pop("pending_campaign_action_id", None)
                                st.session_state.pop("editing_campaign_id", None)
                                st.session_state["campaign_delete_notice"] = "Campaign and its local mock results have been deleted."
                                st.session_state.pop("overview_campaign", None)
                                st.session_state.pop("_force_campaign_selection", None)
                                st.session_state["_reset_campaign_preview_widget"] = True
                                st.rerun()
                    with cancel_col:
                        if st.button("Cancel", key="cancel_selected_campaign_action"):
                            st.session_state.pop("pending_campaign_action", None)
                            st.session_state.pop("pending_campaign_action_id", None)
                            st.rerun()

            # The same criteria editor is used for normal edits and newly duplicated campaigns.
            if st.session_state.get("editing_campaign_id") == selected_id and selected_permission in ("Owner", "Can Edit"):
                st.markdown("#### Edit Campaign Criteria")
                st.caption(
                    "Update the criteria for this campaign. A duplicated campaign is independent "
                    "of its original campaign."
                )
                saved_seniority = [
                    value.strip()
                    for value in str(selected_row["seniority"] or "Manager").split(",")
                    if value.strip() in SENIORITY_OPTIONS
                ] or ["Manager"]

                with st.form(f"edit_campaign_form_{selected_id}"):
                    edit_name = st.text_input("Campaign Name", value=str(selected_row["name"] or ""))
                    edit_owner = st.text_input(
                        "Campaign Owner",
                        value=str(selected_row.get("campaign_owner", "Unassigned") or "Unassigned"),
                    )
                    edit_industry = st.text_input(
                        "Industry",
                        value=str(selected_row["industry"] or ""),
                        help="Enter multiple industries separated by commas, e.g. Pharmaceuticals, Retail.",
                    )
                    edit_company_country = st.text_input(
                        "Company Country",
                        value=str(selected_row["company_country"] or ""),
                        help="Multiple countries are allowed, e.g. United Kingdom, Germany.",
                    )
                    edit_contact_country = st.text_input(
                        "Contact Country",
                        value=str(selected_row["contact_country"] or ""),
                        help="Multiple countries are allowed, e.g. United Kingdom, Germany.",
                    )
                    edit_target_titles = st.text_input(
                        "Job Titles",
                        value=str(selected_row["target_titles"] or ""),
                        help="Enter several titles separated by commas, e.g. CMO, Marketing Director, Head of Marketing.",
                    )
                    edit_current_cms = st.text_input(
                        "Current CMS",
                        value=str(selected_row["current_cms"] or ""),
                        help="Multiple CMS platforms are allowed, e.g. WordPress, Drupal, Sitecore.",
                    )
                    edit_department = st.text_input(
                        "Department",
                        value=str(selected_row["department"] or ""),
                        help="Multiple departments are allowed, e.g. Marketing, Sales.",
                    )
                    edit_seniority = st.multiselect(
                        "Seniority",
                        SENIORITY_OPTIONS,
                        default=saved_seniority,
                        help="Select one or more seniority levels.",
                    )
                    current_job_level = str(selected_row.get("job_level", "Above") or "Above")
                    if current_job_level not in JOB_LEVEL_OPTIONS:
                        current_job_level = "Above"
                    edit_job_level = st.selectbox(
                        "Job Level",
                        JOB_LEVEL_OPTIONS,
                        index=JOB_LEVEL_OPTIONS.index(current_job_level),
                        help=(
                            "Above includes the selected level(s) and higher. Below includes "
                            "the selected level(s) and lower. Exact matches only selected levels."
                        ),
                    )
                    edit_min_score = st.slider(
                        "Minimum company and contact ICP score",
                        min_value=0,
                        max_value=100,
                        value=int(selected_row["min_score"]),
                    )
                    edit_email_instructions = st.text_area(
                        "Email Sequence Instructions",
                        value=str(selected_row.get("email_sequence_instructions", "") or ""),
                        height=150,
                    )
                    edit_clay_table_url = st.text_input(
                        "Clay Table Link (optional)",
                        value=str(selected_row.get("clay_table_url", "") or ""),
                        placeholder="Paste the Clay table URL here when available",
                        help="This saves a link only. Clay is not connected in Mock Mode.",
                    )
                    save_changes = st.form_submit_button("Save Changes")
                    save_and_rerun = st.form_submit_button("Save Changes & Re-run Search", type="primary")

                if save_changes or save_and_rerun:
                    if not edit_name.strip():
                        st.error("Please enter a campaign name.")
                    elif not edit_seniority and edit_job_level != "Any":
                        st.error("Select at least one seniority level, or choose Job Level = Any.")
                    else:
                        owner_value = edit_owner.strip() or "Unassigned"
                        conn.execute(
                            """
                            UPDATE campaigns
                            SET name = ?, campaign_owner = ?, industry = ?, company_country = ?,
                                contact_country = ?, target_titles = ?, min_score = ?, current_cms = ?,
                                department = ?, seniority = ?, job_level = ?,
                                email_sequence_instructions = ?, clay_table_url = ?, status = ?
                            WHERE id = ?
                            """,
                            (
                                edit_name.strip(), owner_value, edit_industry.strip(),
                                edit_company_country.strip(), edit_contact_country.strip(),
                                edit_target_titles.strip(), int(edit_min_score), edit_current_cms.strip(),
                                edit_department.strip(), ", ".join(edit_seniority), edit_job_level,
                                edit_email_instructions.strip(), edit_clay_table_url.strip(),
                                "Draft", selected_id,
                            ),
                        )

                        if save_and_rerun:
                            campaign_for_run = dict(selected_row)
                            campaign_for_run.update(
                                {
                                    "name": edit_name.strip(),
                                    "campaign_owner": owner_value,
                                    "industry": edit_industry.strip(),
                                    "company_country": edit_company_country.strip(),
                                    "contact_country": edit_contact_country.strip(),
                                    "target_titles": edit_target_titles.strip(),
                                    "current_cms": edit_current_cms.strip(),
                                    "department": edit_department.strip(),
                                    "seniority": ", ".join(edit_seniority),
                                    "job_level": edit_job_level,
                                    "min_score": int(edit_min_score),
                                    "email_sequence_instructions": edit_email_instructions.strip(),
                                    "clay_table_url": edit_clay_table_url.strip(),
                                }
                            )
                            records = run_mock_research(campaign_for_run)
                            new_status = insert_mock_research_results(selected_id, records)
                            st.session_state["last_research_notice"] = {
                                "found": bool(records),
                                "count": len(records),
                                "qualified_count": sum(
                                    record["qualification"] == "Qualified" for record in records
                                ),
                                "diagnostics": mock_research_diagnostics(campaign_for_run) if not records else [],
                            }
                            log_activity(
                                "Campaign edited and mock search re-run",
                                selected_id,
                                edit_name.strip(),
                                owner_value,
                                f"Updated criteria. New status: {new_status}.",
                            )
                            st.session_state["campaign_edit_notice"] = (
                                f"Campaign updated and mock search re-run. Status: {new_status}."
                            )
                        else:
                            conn.execute("DELETE FROM leads WHERE campaign_id = ?", (selected_id,))
                            conn.commit()
                            log_activity(
                                "Campaign edited",
                                selected_id,
                                edit_name.strip(),
                                owner_value,
                                "Campaign criteria updated; previous mock results cleared.",
                            )
                            st.session_state["campaign_edit_notice"] = (
                                "Campaign updated. Previous mock results were cleared. "
                                "Use 'Save Changes & Re-run Search' to run the updated criteria."
                            )

                        st.session_state["active_campaign_id"] = selected_id
                        st.session_state["run_campaign_selector"] = selected_id
                        st.session_state["lead_campaign_selector"] = selected_id
                        st.session_state["editing_campaign_id"] = None
                        st.session_state.pop("campaign_edit_context", None)
                        st.rerun()

                if st.button("Cancel Editing", key=f"cancel_campaign_editor_{selected_id}"):
                    st.session_state["editing_campaign_id"] = None
                    st.session_state.pop("campaign_edit_context", None)
                    st.rerun()

    # Keep the mock research runner available without a separate navigation tab.
    campaigns_for_run = load_campaigns()
    if not campaigns_for_run.empty:
        campaigns_for_run = campaigns_for_run[
            campaigns_for_run["id"].apply(
                lambda campaign_id: get_campaign_permission(campaign_id) in ("Owner", "Can Edit")
            )
        ]
    if not campaigns_for_run.empty:
        with st.expander("Run Mock Research", expanded=False):
            st.caption(
                "This runs against fictional sample records only. It does not connect to Clay "
                "or consume Clay credits."
            )
            run_ids = campaigns_for_run["id"].tolist()
            if st.session_state.get("run_campaign_selector") not in run_ids:
                st.session_state["run_campaign_selector"] = run_ids[0]
            active_default = st.session_state.get("active_campaign_id")
            default_index = run_ids.index(active_default) if active_default in run_ids else 0
            run_campaign_id = st.selectbox(
                "Select campaign to research",
                run_ids,
                index=default_index,
                format_func=lambda item: campaign_label(item, campaigns_for_run),
                key="run_campaign_selector",
            )
            if st.button("Start Simulated Research", type="primary", key="start_mock_research"):
                campaign = campaign_as_dict(run_campaign_id)
                records = run_mock_research(campaign)
                new_status = insert_mock_research_results(run_campaign_id, records)
                qualified_count = sum(record["qualification"] == "Qualified" for record in records)
                st.session_state["last_research_notice"] = {
                    "found": bool(records),
                    "count": len(records),
                    "qualified_count": qualified_count,
                    "diagnostics": mock_research_diagnostics(campaign) if not records else [],
                }
                log_activity(
                    "Mock research completed",
                    run_campaign_id,
                    campaign.get("name", ""),
                    campaign.get("campaign_owner", "Unassigned"),
                    f"{len(records)} sample contacts found; status: {new_status}.",
                )
                st.session_state["lead_campaign_selector"] = run_campaign_id
                st.rerun()

elif active_page == "Review & Approvals":
    st.subheader("Review & Approvals")
    st.caption("Review the sample contacts and email drafts associated with each campaign.")
    campaigns = load_campaigns()
    if campaigns.empty:
        if is_mock_admin:
            st.info("Create a campaign and run Mock Research first.")
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
            st.info("No sample contacts yet. Run Mock Research from the Campaigns page.")
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
                    "This is a preview only. Mock Mode does not send a request to Clay or an AI model."
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

            st.warning(
                "This MVP uses fictional sample data. It does not connect to Clay, "
                "enrich real records, or send emails."
            )

elif active_page == "Team & Access":
    st.subheader("Team & Access")
    st.caption("Manage workspace members. Each permission applies to every campaign in the dashboard.")

    if invitation_email_is_configured():
        st.success("Invitation email is configured. Invitations will be sent as real emails.")
    else:
        st.warning("Gmail is not configured yet. Add the email settings in Streamlit Secrets before sending invitations.")

    with st.expander("Gmail setup for testing", expanded=not invitation_email_is_configured()):
        st.write(
            "Use a Gmail account with 2-Step Verification enabled and a Google App Password. "
            "Do not use your normal Gmail password."
        )
        st.code(
            "[email]\nsmtp_server = \"smtp.gmail.com\"\nsmtp_port = 587\n"
            "sender_email = \"your.test.account@gmail.com\"\n"
            "app_password = \"your-16-character-google-app-password\"\n"
            "sender_name = \"AI SDR Dashboard\"\n"
            "dashboard_url = \"https://your-app-name.streamlit.app\"",
            language="toml",
        )
        st.caption(
            "Add this under your Streamlit app's Settings → Secrets. Keep the app password private "
            "and never commit it to GitHub."
        )
        st.markdown("[Google instructions: create an App Password](https://support.google.com/mail/answer/185833)")

    if is_mock_admin:
        st.markdown("### Invite a teammate")
        st.caption("The selected permission will apply to all current and future campaigns.")
        with st.form("send_workspace_invitation_form"):
            invite_name = st.text_input("User name")
            invite_email = st.text_input("User email address")
            invite_permission = st.selectbox(
                "Access permission",
                ["View Only", "Can Edit"],
                index=None,
                placeholder="Select permission",
                help="You must choose a permission. Nothing is selected by default.",
            )
            send_invitation = st.form_submit_button("Send Invitation", type="primary")

        if send_invitation:
            email_value = invite_email.strip().lower()
            if not invite_name.strip():
                st.error("Please enter the user's name.")
            elif not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email_value):
                st.error("Please enter a valid email address.")
            elif not invite_permission:
                st.error("Please select View Only or Can Edit.")
            elif not invitation_email_is_configured():
                st.error("Configure Gmail in Streamlit Secrets before sending invitations.")
            else:
                invitation_token = pysecrets.token_urlsafe(32)
                now = datetime.now()
                now_text = now.isoformat(timespec="seconds")
                expiry_text = (now + timedelta(days=7)).isoformat(timespec="seconds")
                inviter_name = current_mock_user_name

                conn.execute(
                    """
                    INSERT INTO team_members (email, name, status, created_at)
                    VALUES (?, ?, 'Pending', ?)
                    ON CONFLICT(email) DO UPDATE SET name = excluded.name, status = 'Pending'
                    """,
                    (email_value, invite_name.strip(), now_text),
                )
                conn.execute(
                    """
                    INSERT INTO workspace_access
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
                        revoked_at = NULL
                    """,
                    (
                        str(uuid.uuid4()), email_value, invite_name.strip(), invite_permission,
                        invitation_token, inviter_name, now_text, expiry_text,
                    ),
                )
                conn.commit()
                try:
                    send_workspace_invitation_email(
                        invite_name.strip(), email_value, invite_permission, inviter_name, invitation_token
                    )
                    log_activity(
                        "Workspace invitation sent",
                        None,
                        "Workspace",
                        inviter_name,
                        f"Invitation sent to {email_value} with {invite_permission} access to all campaigns.",
                    )
                    st.success(f"Workspace invitation email sent to {email_value}.")
                except Exception as exc:
                    conn.execute(
                        "UPDATE workspace_access SET invitation_status = 'Email Failed', invitation_token = NULL WHERE member_email = ?",
                        (email_value,),
                    )
                    conn.execute(
                        "UPDATE team_members SET status = 'Inactive' WHERE email = ?",
                        (email_value,),
                    )
                    conn.commit()
                    st.error(f"Could not send the invitation email: {exc}")

        st.markdown("### Manage Workspace Access")
        st.caption("Each person appears once. Their permission applies across the entire workspace.")
        access_rows = conn.execute(
            """
            SELECT id, member_name, member_email, permission, invitation_status,
                   invited_at, accepted_at
            FROM workspace_access
            ORDER BY invited_at DESC
            """
        ).fetchall()

        if not access_rows:
            st.info("No teammates have been invited yet.")
        else:
            for access_row in access_rows:
                (
                    access_id, member_name, member_email, current_permission,
                    invitation_status, invited_at, accepted_at,
                ) = access_row
                with st.container(border=True):
                    member_cols = st.columns([1.5, 2.1, 1.25, 1.4, 1.0])
                    member_cols[0].write(f"**{member_name}**")
                    member_cols[1].write(member_email)
                    member_cols[2].write(invitation_status)
                    with member_cols[3]:
                        new_permission = st.selectbox(
                            "Permission",
                            ["View Only", "Can Edit"],
                            index=["View Only", "Can Edit"].index(current_permission),
                            key=f"workspace_permission_{access_id}",
                            label_visibility="collapsed",
                        )
                    with member_cols[4]:
                        if st.button("Save", key=f"save_workspace_access_{access_id}"):
                            conn.execute(
                                "UPDATE workspace_access SET permission = ? WHERE id = ?",
                                (new_permission, access_id),
                            )
                            conn.commit()
                            if invitation_status == "Pending":
                                latest = conn.execute(
                                    """
                                    SELECT invitation_token, member_name, member_email, invited_by
                                    FROM workspace_access WHERE id = ?
                                    """,
                                    (access_id,),
                                ).fetchone()
                                try:
                                    send_workspace_invitation_email(
                                        latest[1], latest[2], new_permission, latest[3], latest[0]
                                    )
                                    st.success("Permission updated and revised invitation email sent.")
                                except Exception as exc:
                                    st.error(f"Permission updated, but revised email could not be sent: {exc}")
                            else:
                                st.success("Workspace permission updated for all campaigns.")
                            st.rerun()

                    revoke_col, info_col = st.columns([1, 4])
                    with revoke_col:
                        if invitation_status != "Revoked":
                            if st.button("Revoke Access", key=f"revoke_workspace_access_{access_id}"):
                                conn.execute(
                                    """
                                    UPDATE workspace_access
                                    SET invitation_status = 'Revoked',
                                        invitation_token = NULL,
                                        revoked_at = ?
                                    WHERE id = ?
                                    """,
                                    (datetime.now().isoformat(timespec="seconds"), access_id),
                                )
                                conn.execute(
                                    "UPDATE team_members SET status = 'Inactive' WHERE email = ?",
                                    (member_email,),
                                )
                                conn.commit()
                                log_activity(
                                    "Workspace access revoked",
                                    None,
                                    "Workspace",
                                    current_mock_user_name,
                                    f"Revoked all-campaign access for {member_email}.",
                                )
                                st.success(f"Workspace access revoked for {member_email}.")
                                st.rerun()
                    with info_col:
                        st.caption(
                            f"Invited: {format_created_date(invited_at)}"
                            + (f" · Accepted: {format_created_date(accepted_at)}" if accepted_at else "")
                        )

    else:
        current_access = conn.execute(
            """
            SELECT permission, invitation_status, invited_by, invited_at, accepted_at
            FROM workspace_access WHERE member_email = ?
            """,
            (current_mock_user_email,),
        ).fetchone()
        st.markdown("### Your Workspace Access")
        if current_access:
            permission, invitation_status, invited_by, invited_at, accepted_at = current_access
            st.write(f"**Workspace:** All campaigns")
            st.write(f"**Permission:** {permission}")
            st.write(f"**Status:** {invitation_status}")
            st.caption(f"Invited by {invited_by} on {format_created_date(invited_at)}")
        else:
            st.info("No workspace access has been assigned to this mock user.")
        st.caption("Only Workspace Admin can invite teammates, change workspace permissions, or revoke access.")

    st.markdown("### Mock Access Testing")
    st.write(f"**Current mock identity:** {current_mock_user_name}")
    st.caption(
        "Use Switch Mock User in the sidebar to preview the dashboard as an accepted invitee. "
        "View Only users can view all campaigns and drafts; Can Edit users can edit and duplicate all campaigns. "
        "Only Workspace Admin can delete campaigns."
    )
    st.warning(
        "This is a permission simulation for testing, not secure authentication. Anyone who can open "
        "the public dashboard can change the mock identity selector. Add real login and a shared production "
        "database before using this for confidential company data."
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
    settings_cols[0].metric("Execution Mode", "Mock Mode")
    settings_cols[1].metric("Clay Connection", "Not Connected")
    settings_cols[2].metric(
        "Invitation Email",
        "Configured" if invitation_email_is_configured() else "Not Configured",
    )
    st.markdown("#### Current setup")
    st.write("- The dashboard uses fictional sample company and contact records.")
    st.write("- No Clay API requests are made and no Clay credits are consumed.")
    st.write("- Clay table URLs can be saved and opened, but the dashboard does not read or update Clay tables.")
    st.write("- Email drafts are not sent. Team invitations can be emailed when SMTP is configured in Streamlit Secrets.")
    st.write("- Campaign data is stored in the app's SQLite database.")

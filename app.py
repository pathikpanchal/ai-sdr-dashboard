import streamlit as st
import pandas as pd
import sqlite3
import uuid
import html
from datetime import datetime
from pathlib import Path

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "ai_sdr.db"

st.set_page_config(page_title="AI SDR Dashboard", page_icon="🎯", layout="wide")

st.markdown(
    """
    <style>
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


def load_campaigns():
    return pd.read_sql_query("SELECT * FROM campaigns ORDER BY created_at DESC", conn)


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


st.title("AI SDR Dashboard")
st.caption("Phase I MVP · Mock Mode · No Clay API calls or Clay credits used")

NAV_ITEMS = [
    "Campaigns",
    "Review & Approvals",
    "Team & Access",
    "Activity Log",
    "Settings",
]

with st.sidebar:
    st.markdown("## AI SDR Dashboard")
    st.caption("Phase I workspace")
    st.divider()
    active_page = st.radio(
        "Workspace",
        NAV_ITEMS,
        key="main_navigation",
        label_visibility="collapsed",
    )
    st.divider()
    st.success("MOCK MODE — ON")
    st.caption("Fictional sample data only. Clay is not connected.")

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


if active_page == "Campaigns":
    heading_col, create_col = st.columns([5.5, 1.5])
    with heading_col:
        st.subheader("Campaign Overview")
        st.caption("Manage campaigns, review their criteria, and open the linked Clay table.")
    with create_col:
        if st.button("＋ Create Campaign", type="primary", use_container_width=True):
            st.session_state["show_create_campaign_form"] = True
            st.session_state["editing_campaign_id"] = None
            st.rerun()

    delete_notice = st.session_state.pop("campaign_delete_notice", None)
    if delete_notice:
        st.success(delete_notice)

    create_notice = st.session_state.pop("campaign_create_notice", None)
    if create_notice:
        st.success(create_notice)

    campaigns = load_campaigns()
    if campaigns.empty:
        st.info("No campaigns yet. Select **Create Campaign** to set up your first campaign.")
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
        previous_selection_signature = tuple(
            st.session_state.get("_last_campaign_table_selection", [])
        )
        if selected_indexes and selection_signature != previous_selection_signature:
            selected_index = int(selected_indexes[0])
            if 0 <= selected_index < len(campaigns):
                st.session_state["overview_campaign"] = campaigns.iloc[selected_index]["id"]
        st.session_state["_last_campaign_table_selection"] = list(selection_signature)

        selected_id = st.session_state.get("overview_campaign")
        if selected_id not in campaign_ids:
            selected_id = campaign_ids[0]
            st.session_state["overview_campaign"] = selected_id

        selected_row = campaigns[campaigns["id"] == selected_id].iloc[0]
        selected_name = str(selected_row["name"] or "Untitled campaign")
        selected_owner = str(selected_row.get("campaign_owner", "Unassigned") or "Unassigned")

        st.divider()
        action_title, edit_col, duplicate_col, delete_col = st.columns([3.4, 1.3, 1.55, 1.3])
        with action_title:
            st.markdown(f"#### Selected Campaign: {selected_name}")
        with edit_col:
            if st.button("Edit Campaign", key="selected_edit_campaign", use_container_width=True):
                st.session_state["pending_campaign_action"] = "edit"
                st.session_state["pending_campaign_action_id"] = selected_id
                st.rerun()
        with duplicate_col:
            if st.button("Duplicate Campaign", key="selected_duplicate_campaign", use_container_width=True):
                st.session_state["pending_campaign_action"] = "duplicate"
                st.session_state["pending_campaign_action_id"] = selected_id
                st.rerun()
        with delete_col:
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
                                    selected_owner,
                                ),
                            )
                            conn.commit()
                            log_activity(
                                "Campaign duplicated",
                                new_id,
                                new_name,
                                selected_owner,
                                f"Duplicated from campaign: {selected_name}",
                            )
                            st.session_state["overview_campaign"] = new_id
                            st.session_state["_last_campaign_table_selection"] = list(selection_signature)
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
                            st.session_state["_last_campaign_table_selection"] = list(selection_signature)
                            if remaining_ids:
                                st.session_state["overview_campaign"] = remaining_ids[0]
                            else:
                                st.session_state.pop("overview_campaign", None)
                            st.rerun()
                with cancel_col:
                    if st.button("Cancel", key="cancel_selected_campaign_action"):
                        st.session_state.pop("pending_campaign_action", None)
                        st.session_state.pop("pending_campaign_action_id", None)
                        st.rerun()

        # The same criteria editor is used for normal edits and newly duplicated campaigns.
        if st.session_state.get("editing_campaign_id") == selected_id:
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

    # Campaign creation is opened from the Create Campaign button above.
    if st.session_state.get("show_create_campaign_form"):
        st.divider()
        with st.container(border=True):
            create_title_col, create_cancel_col = st.columns([5, 1])
            with create_title_col:
                st.markdown("#### Create New Campaign")
            with create_cancel_col:
                if st.button("Close", key="close_create_campaign_form"):
                    st.session_state["show_create_campaign_form"] = False
                    st.rerun()

            with st.form("create_campaign_form"):
                campaign_name = st.text_input(
                    "Campaign Name",
                    value="UK Pharmaceutical Marketing Decision Makers",
                )
                campaign_owner = st.text_input(
                    "Campaign Owner",
                    value="",
                    placeholder="Enter SDR or campaign owner's name",
                )
                industry = st.text_input("Industry", value="Pharmaceuticals")
                company_country = st.text_input("Company Country", value="United Kingdom")
                contact_country = st.text_input("Contact Country", value="United Kingdom")
                target_titles = st.text_input(
                    "Job Titles",
                    value="",
                    placeholder="e.g. CMO, Marketing Director, Head of Marketing",
                    help="Enter multiple titles separated by commas. Blank means any job title.",
                )
                current_cms = st.text_input("Current CMS", value="", placeholder="e.g. WordPress, Drupal, Sitecore")
                department = st.text_input("Department", value="Marketing", placeholder="e.g. Marketing, Sales")
                seniority_col, job_level_col = st.columns(2)
                with seniority_col:
                    seniority = st.multiselect("Seniority", SENIORITY_OPTIONS, default=["Manager"])
                with job_level_col:
                    job_level = st.selectbox(
                        "Job Level",
                        JOB_LEVEL_OPTIONS,
                        index=JOB_LEVEL_OPTIONS.index("Above"),
                    )
                clay_table_url = st.text_input(
                    "Clay Table Link (optional)",
                    value="",
                    placeholder="Paste the Clay table URL here when available",
                )
                email_sequence_instructions = st.text_area(
                    "Email Sequence Instructions",
                    value=(
                        "Goal: Start relevant conversations with the target decision-maker.\n"
                        "Audience: Address the contact's role and business context.\n"
                        "Personalization: Use relevant company, industry, technology, and role details only when available.\n"
                        "Tone: Professional, natural, concise, and conversational.\n"
                        "Call to action: Ask for the next step you want the prospect to take.\n"
                        "Avoid: Generic claims, exaggerated promises, and unsupported facts."
                    ),
                    height=150,
                )
                threshold = st.slider(
                    "Minimum company and contact ICP score",
                    min_value=0,
                    max_value=100,
                    value=75,
                )
                submitted = st.form_submit_button("Save Campaign", type="primary")

            if submitted:
                if not campaign_name.strip():
                    st.error("Please enter a campaign name.")
                elif not seniority and job_level != "Any":
                    st.error("Select at least one seniority level, or choose Job Level = Any.")
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
                            campaign_id, campaign_name.strip(), industry.strip(),
                            company_country.strip(), contact_country.strip(), target_titles.strip(),
                            int(threshold), "Draft", datetime.now().isoformat(timespec="seconds"),
                            current_cms.strip(), department.strip(), ", ".join(seniority),
                            job_level, email_sequence_instructions.strip(), clay_table_url.strip(),
                            owner_value,
                        ),
                    )
                    conn.commit()
                    log_activity("Campaign created", campaign_id, campaign_name.strip(), owner_value)
                    st.session_state["overview_campaign"] = campaign_id
                    st.session_state["active_campaign_id"] = campaign_id
                    st.session_state["run_campaign_selector"] = campaign_id
                    st.session_state["lead_campaign_selector"] = campaign_id
                    st.session_state["show_create_campaign_form"] = False
                    st.session_state["campaign_create_notice"] = "Campaign created successfully."
                    st.rerun()

    # Keep the mock research runner available without a separate navigation tab.
    campaigns_for_run = load_campaigns()
    if not campaigns_for_run.empty:
        with st.expander("Run Mock Research", expanded=False):
            st.caption(
                "This runs against fictional sample records only. It does not connect to Clay "
                "or consume Clay credits."
            )
            run_ids = campaigns_for_run["id"].tolist()
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
        st.info("Create a campaign and run Mock Research first.")
    else:
        selected_campaign_id = st.selectbox(
            "Campaign",
            campaigns["id"].tolist(),
            format_func=lambda item: campaign_label(item, campaigns),
            key="lead_campaign_selector",
        )
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
                save_drafts = st.form_submit_button("Save Email Drafts")
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

            if st.button("Approve Contact for Campaign Review", key=f"approve_{contact_id}"):
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
    st.caption("Campaign-level sharing and individual permissions")
    st.info(
        "The sharing workflow is planned, but secure multi-user access is not active in this Mock Mode build."
    )
    st.markdown("#### Planned sharing controls")
    st.write(
        "Campaign owners will be able to select individual teammates and explicitly assign "
        "**View Only** or **Can Edit** access to each person. No permission will be selected by default."
    )
    st.write(
        "Owners will also be able to change a teammate's permission or revoke access from a "
        "Manage Access view. Different teammates can have different permissions for the same campaign."
    )
    st.warning(
        "This deployment currently uses a local SQLite database and does not enforce individual user logins "
        "or campaign-level access restrictions. Do not treat the current app as a secure multi-user workspace. "
        "Authentication and shared database storage are required before enabling real sharing."
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
    settings_cols[2].metric("Email Sending", "Disabled")
    st.markdown("#### Current setup")
    st.write("- The dashboard uses fictional sample company and contact records.")
    st.write("- No Clay API requests are made and no Clay credits are consumed.")
    st.write("- Clay table URLs can be saved and opened, but the dashboard does not read or update Clay tables.")
    st.write("- Email drafts can be reviewed and edited, but no email is sent from this dashboard.")
    st.write("- Campaign data is stored in the app's SQLite database.")

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

    # Add new columns safely to databases created by the earlier dashboard version.
    migrations = {
        "campaigns": {
            "current_cms": "TEXT DEFAULT ''",
            "department": "TEXT DEFAULT ''",
            "seniority": "TEXT DEFAULT 'Manager'",
            "job_level": "TEXT DEFAULT 'Above'",
            "email_sequence_instructions": "TEXT DEFAULT ''",
            "clay_table_url": "TEXT DEFAULT ''",
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

with st.sidebar:
    st.header("Execution mode")
    st.success("MOCK MODE — ON")
    st.caption("This version uses fictional sample data. Clay is not connected.")
    st.divider()
    st.caption(
        "Phase I: campaign filters → simulated prospecting → ICP scoring → "
        "email drafts → human review."
    )

tabs = st.tabs(["Campaigns", "Create campaign", "Leads & email review"])

# Display the last research result after the app reruns, so the message and
# filter diagnostics remain visible instead of being cleared by st.rerun().
campaign_edit_notice = st.session_state.pop("campaign_edit_notice", None)
if campaign_edit_notice:
    st.success(campaign_edit_notice)

last_research_notice = st.session_state.pop("last_research_notice", None)
if last_research_notice:
    if last_research_notice["found"]:
        st.success(
            f"Mock research complete: {last_research_notice['count']} matching contacts found; "
            f"{last_research_notice['qualified_count']} passed the ICP score threshold."
        )
    else:
        st.warning(
            "No sample records matched all selected filters. The filter diagnostics below "
            "show where the records were excluded. No Clay search was performed."
        )
        with st.expander("Why were no records found? — filter diagnostics", expanded=True):
            st.caption("Counts show how many fictional sample records remain after each filter.")
            for filter_name, remaining_count in last_research_notice["diagnostics"]:
                st.write(f"**{filter_name}:** {remaining_count}")
            st.caption(
                "The minimum ICP score labels records as Qualified or Review / Exclude; "
                "it does not remove them from the results."
            )

with tabs[0]:
    st.subheader("Campaign overview")
    st.caption(
        "A clear view of your campaigns, target audience, research results, and Clay table links."
    )
    delete_notice = st.session_state.pop("campaign_delete_notice", None)
    if delete_notice:
        st.success(delete_notice)

    campaigns = load_campaigns()
    if not campaigns.empty:
        lead_counts = pd.read_sql_query(
            """
            SELECT campaign_id,
                   COUNT(DISTINCT company) AS total_companies,
                   COUNT(*) AS total_contacts
            FROM leads
            GROUP BY campaign_id
            """,
            conn,
        )
        campaigns = campaigns.merge(
            lead_counts, how="left", left_on="id", right_on="campaign_id"
        )
        campaigns["total_companies"] = campaigns["total_companies"].fillna(0).astype(int)
        campaigns["total_contacts"] = campaigns["total_contacts"].fillna(0).astype(int)

    if campaigns.empty:
        st.info("No campaigns yet. Create your first campaign in the Create campaign tab.")
        selected_id = None
        selected_row = None
    else:
        total_campaigns = len(campaigns)
        ready_campaigns = int((campaigns["status"] == "Draft ready").sum())
        total_companies = int(campaigns["total_companies"].sum())
        total_contacts = int(campaigns["total_contacts"].sum())

        metric_cols = st.columns(4)
        metric_cols[0].metric("Campaigns", total_campaigns)
        metric_cols[1].metric("Company matches", total_companies)
        metric_cols[2].metric("Contact matches", total_contacts)
        metric_cols[3].metric("Drafts ready", ready_campaigns)

        st.markdown("#### Campaign preview")
        st.caption(
            "Select one campaign using the checkbox. Its filters appear automatically. "
            "Use Edit, Duplicate, or Delete directly from that campaign's row."
        )

        campaign_ids = campaigns["id"].tolist()
        current_selected = st.session_state.get("overview_campaign")
        if current_selected not in campaign_ids:
            current_selected = campaign_ids[0]
            st.session_state["overview_campaign"] = current_selected

        # Keep exactly one checkbox selected and make it follow the selected campaign.
        for campaign_id in campaign_ids:
            st.session_state[f"overview_pick_{campaign_id}"] = (
                campaign_id == current_selected
            )

        table_widths = [0.48, 2.55, 0.95, 0.72, 0.72, 0.90, 0.62, 0.86, 0.68]
        header_cols = st.columns(table_widths)
        headers = [
            "Select", "Campaign", "Created", "Companies", "Contacts",
            "Status", "Edit", "Duplicate", "Delete",
        ]
        for header_col, label in zip(header_cols, headers):
            header_col.markdown(f"**{label}**")

        st.divider()
        for _, campaign_row in campaigns.iterrows():
            campaign_id = campaign_row["id"]
            row_cols = st.columns(table_widths)

            with row_cols[0]:
                st.checkbox(
                    "Select campaign",
                    key=f"overview_pick_{campaign_id}",
                    label_visibility="collapsed",
                    on_change=on_overview_campaign_checkbox_change,
                    args=(campaign_id, campaign_ids),
                )

            with row_cols[1]:
                campaign_name_display = str(campaign_row["name"] or "Untitled campaign")
                st.markdown(f"**{html.escape(campaign_name_display)}**")
                clay_url = str(campaign_row.get("clay_table_url", "") or "").strip()
                if clay_url:
                    st.markdown(f"[Open Clay table]({html.escape(clay_url, quote=True)})")

            row_cols[2].write(format_created_date(campaign_row["created_at"]))
            row_cols[3].write(int(campaign_row["total_companies"]))
            row_cols[4].write(int(campaign_row["total_contacts"]))
            row_cols[5].write(str(campaign_row["status"] or "Draft"))

            with row_cols[6]:
                if st.button("Edit", key=f"overview_edit_{campaign_id}", use_container_width=True):
                    st.session_state["overview_campaign"] = campaign_id
                    st.session_state["editing_campaign_id"] = campaign_id
                    st.rerun()

            with row_cols[7]:
                if st.button(
                    "Duplicate",
                    key=f"overview_duplicate_{campaign_id}",
                    use_container_width=True,
                ):
                    new_id = str(uuid.uuid4())
                    conn.execute(
                        """
                        INSERT INTO campaigns
                        (id, name, industry, company_country, contact_country, target_titles,
                         min_score, status, created_at, current_cms, department, seniority,
                         job_level, email_sequence_instructions, clay_table_url)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            new_id,
                            str(campaign_row["name"] or "Untitled campaign") + " (Copy)",
                            campaign_row["industry"] or "",
                            campaign_row["company_country"] or "",
                            campaign_row["contact_country"] or "",
                            campaign_row["target_titles"] or "",
                            int(campaign_row["min_score"]),
                            "Draft",
                            datetime.now().isoformat(timespec="seconds"),
                            campaign_row.get("current_cms", "") or "",
                            campaign_row.get("department", "") or "",
                            campaign_row.get("seniority", "Manager") or "Manager",
                            campaign_row.get("job_level", "Above") or "Above",
                            campaign_row.get("email_sequence_instructions", "") or "",
                            "",  # New campaign should be linked to its own Clay table.
                        ),
                    )
                    conn.commit()
                    st.session_state["overview_campaign"] = new_id
                    st.session_state["editing_campaign_id"] = None
                    st.session_state["campaign_duplicate_notice"] = (
                        "Campaign duplicated with its filters and email instructions."
                    )
                    st.rerun()

            with row_cols[8]:
                if st.button(
                    "Delete",
                    key=f"overview_delete_{campaign_id}",
                    use_container_width=True,
                ):
                    st.session_state["pending_delete_campaign"] = campaign_id
                    st.rerun()

            if campaign_id == st.session_state.get("overview_campaign"):
                st.markdown(
                    "<div style='border-bottom: 2px solid #64748b; margin: 0.2rem 0 0.5rem 0;'></div>",
                    unsafe_allow_html=True,
                )
            else:
                st.divider()

        duplicate_notice = st.session_state.pop("campaign_duplicate_notice", None)
        if duplicate_notice:
            st.success(duplicate_notice)

        pending_delete_id = st.session_state.get("pending_delete_campaign")
        if pending_delete_id in campaign_ids:
            pending_delete_name = campaign_label(pending_delete_id, campaigns)
            with st.container(border=True):
                st.warning(
                    f"Delete **{pending_delete_name}** and all of its local mock results? "
                    "This cannot be undone."
                )
                confirm_col, cancel_col = st.columns(2)
                with confirm_col:
                    if st.button(
                        "Yes, delete campaign",
                        key="confirm_delete_campaign",
                        type="primary",
                    ):
                        conn.execute(
                            "DELETE FROM leads WHERE campaign_id = ?", (pending_delete_id,)
                        )
                        conn.execute(
                            "DELETE FROM campaigns WHERE id = ?", (pending_delete_id,)
                        )
                        conn.commit()

                        remaining_ids = [
                            item for item in campaign_ids if item != pending_delete_id
                        ]
                        fallback_id = remaining_ids[0] if remaining_ids else None
                        st.session_state.pop("pending_delete_campaign", None)
                        st.session_state.pop("editing_campaign_id", None)
                        for state_key in (
                            "overview_campaign",
                            "active_campaign_id",
                            "run_campaign_selector",
                            "lead_campaign_selector",
                        ):
                            if st.session_state.get(state_key) == pending_delete_id:
                                if fallback_id:
                                    st.session_state[state_key] = fallback_id
                                else:
                                    st.session_state.pop(state_key, None)
                        st.session_state["campaign_delete_notice"] = (
                            "Campaign and its local mock leads have been deleted."
                        )
                        st.rerun()
                with cancel_col:
                    if st.button("Cancel", key="cancel_delete_campaign"):
                        st.session_state.pop("pending_delete_campaign", None)
                        st.rerun()

        selected_id = st.session_state.get("overview_campaign", campaign_ids[0])
        selected_row = campaigns[campaigns["id"] == selected_id].iloc[0]

        st.markdown(f"#### Selected campaign filters: {html.escape(str(selected_row['name']))}")
        with st.container(border=True):
            filter_cols = st.columns(3)
            filter_cols[0].write(f"**Industry**\n\n{selected_row['industry'] or 'Any'}")
            filter_cols[1].write(
                f"**Company country**\n\n{selected_row['company_country'] or 'Any'}"
            )
            filter_cols[2].write(
                f"**Contact country**\n\n{selected_row['contact_country'] or 'Any'}"
            )
            filter_cols = st.columns(3)
            filter_cols[0].write(
                f"**Job titles**\n\n{selected_row['target_titles'] or 'Any'}"
            )
            filter_cols[1].write(
                f"**Current CMS**\n\n{selected_row['current_cms'] or 'Any'}"
            )
            filter_cols[2].write(
                f"**Department**\n\n{selected_row['department'] or 'Any'}"
            )
            filter_cols = st.columns(3)
            filter_cols[0].write(
                f"**Seniority**\n\n{selected_row['seniority'] or 'Any'}"
            )
            filter_cols[1].write(
                f"**Job level**\n\n{selected_row['job_level'] or 'Any'}"
            )
            filter_cols[2].write(f"**Minimum ICP score**\n\n{int(selected_row['min_score'])}/100")
            st.write(
                "**Email Sequence Instructions**\n\n"
                + (
                    selected_row.get("email_sequence_instructions", "")
                    or "No custom instructions added."
                )
            )
            clay_table_url = str(selected_row.get("clay_table_url", "") or "").strip()
            if clay_table_url:
                st.link_button("Open Clay table", clay_table_url)
            else:
                st.caption("Clay table link: Not added yet")

        if st.session_state.get("editing_campaign_id") == selected_id:
            st.markdown("#### Edit campaign filters")
            st.caption(
                "Broaden or refine the criteria, then save the changes or save and run "
                "the search again using the updated filters."
            )
            saved_seniority = [
                value.strip()
                for value in str(selected_row["seniority"] or "Manager").split(",")
                if value.strip() in SENIORITY_OPTIONS
            ] or ["Manager"]

            with st.form(f"edit_campaign_form_{selected_id}"):
                edit_name = st.text_input(
                    "Campaign Name", value=str(selected_row["name"] or "")
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
                    help="Enter several job titles separated by commas, e.g. CMO, Marketing Director, Head of Marketing.",
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
                edit_job_level = st.selectbox(
                    "Job Level",
                    JOB_LEVEL_OPTIONS,
                    index=JOB_LEVEL_OPTIONS.index(
                        selected_row["job_level"]
                        if selected_row["job_level"] in JOB_LEVEL_OPTIONS
                        else "Above"
                    ),
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
                    help="Save the Clay table URL for quick access. Clay is not connected in Mock Mode.",
                )
                save_changes = st.form_submit_button("Save changes")
                save_and_rerun = st.form_submit_button(
                    "Save changes & Re-run Search", type="primary"
                )

            if save_changes or save_and_rerun:
                if not edit_name.strip():
                    st.error("Please enter a campaign name.")
                elif not edit_seniority and edit_job_level != "Any":
                    st.error("Select at least one seniority level, or choose Job Level = Any.")
                else:
                    conn.execute(
                        """
                        UPDATE campaigns
                        SET name = ?, industry = ?, company_country = ?, contact_country = ?,
                            target_titles = ?, min_score = ?, current_cms = ?, department = ?,
                            seniority = ?, job_level = ?, email_sequence_instructions = ?,
                            clay_table_url = ?, status = ?
                        WHERE id = ?
                        """,
                        (
                            edit_name.strip(),
                            edit_industry.strip(),
                            edit_company_country.strip(),
                            edit_contact_country.strip(),
                            edit_target_titles.strip(),
                            int(edit_min_score),
                            edit_current_cms.strip(),
                            edit_department.strip(),
                            ", ".join(edit_seniority),
                            edit_job_level,
                            edit_email_instructions.strip(),
                            edit_clay_table_url.strip(),
                            "Draft",
                            selected_id,
                        ),
                    )

                    if save_and_rerun:
                        campaign_for_run = dict(selected_row)
                        campaign_for_run.update(
                            {
                                "name": edit_name.strip(),
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
                                record["qualification"] == "Qualified"
                                for record in records
                            ),
                            "diagnostics": (
                                mock_research_diagnostics(campaign_for_run)
                                if not records else []
                            ),
                        }
                        st.session_state["campaign_edit_notice"] = (
                            f"Campaign updated and search re-run. Status: {new_status}."
                        )
                    else:
                        # Remove old results to avoid showing records that no longer match.
                        conn.execute(
                            "DELETE FROM leads WHERE campaign_id = ?", (selected_id,)
                        )
                        conn.commit()
                        st.session_state["campaign_edit_notice"] = (
                            "Campaign updated. Previous results were cleared. "
                            "Use 'Save changes & Re-run Search' to search with the new filters."
                        )

                    st.session_state["active_campaign_id"] = selected_id
                    st.session_state["run_campaign_selector"] = selected_id
                    st.session_state["lead_campaign_selector"] = selected_id
                    st.session_state["editing_campaign_id"] = None
                    st.rerun()
            if st.button(
                "Cancel editing",
                key=f"cancel_campaign_editor_{selected_id}",
            ):
                st.session_state["editing_campaign_id"] = None
                st.rerun()


with tabs[1]:
    st.subheader("Create campaign")
    st.caption(
        "Use commas or semicolons to enter multiple values in a field. Values within one "
        "field work as OR (e.g. Pharmaceuticals, Retail); different fields work as AND."
    )

    with st.form("create_campaign_form"):
        campaign_name = st.text_input(
            "Campaign Name",
            value="UK Pharmaceutical Marketing Decision Makers",
        )
        industry = st.text_input(
            "Industry",
            value="Pharmaceuticals",
            placeholder="e.g. Pharmaceuticals, Healthcare",
        )
        company_country = st.text_input(
            "Company Country",
            value="United Kingdom",
            placeholder="e.g. United Kingdom",
        )
        contact_country = st.text_input(
            "Contact Country",
            value="United Kingdom",
            placeholder="e.g. United Kingdom",
        )
        target_titles = st.text_input(
            "Job Titles",
            value="",
            placeholder="e.g. CMO, Marketing Director, Head of Marketing",
            help="Enter multiple titles separated by commas. A blank field allows any job title.",
        )
        current_cms = st.text_input(
            "Current CMS",
            value="",
            placeholder="e.g. WordPress, Drupal, Sitecore (leave blank for any CMS)",
        )
        department = st.text_input(
            "Department",
            value="Marketing",
            placeholder="e.g. Marketing, Sales, HR, Finance",
        )

        seniority_col, job_level_col = st.columns(2)
        with seniority_col:
            seniority = st.multiselect(
                "Seniority",
                SENIORITY_OPTIONS,
                default=["Manager"],
                help="Select one or more seniority levels.",
            )
        with job_level_col:
            job_level = st.selectbox(
                "Job Level",
                JOB_LEVEL_OPTIONS,
                index=JOB_LEVEL_OPTIONS.index("Above"),
                help=(
                    "Above includes the selected level(s) and higher. Below includes "
                    "the selected level(s) and lower. Exact matches only selected levels."
                ),
            )

        clay_table_url = st.text_input(
            "Clay Table Link (optional)",
            value="",
            placeholder="Paste the Clay table URL here when available",
            help="You can add the Clay table link now or later by editing the campaign. Clay is not connected in Mock Mode.",
        )

        email_sequence_instructions = st.text_area(
            "Email Sequence Instructions",
            value=(
                "Goal: Start relevant conversations with the target decision-maker.\n"
                "Audience: Address the contact's role and business context.\n"
                "Personalization: Use relevant company, industry, technology, and role details "
                "only when available.\n"
                "Tone: Professional, natural, concise, and conversational.\n"
                "Call to action: Ask for the next step you want the prospect to take.\n"
                "Avoid: Generic claims, exaggerated promises, and unsupported facts."
            ),
            height=150,
            help=(
                "Describe the sequence goal, audience, tone, personalization, offer, CTA, "
                "and anything the emails should avoid. These instructions are saved with "
                "the campaign and prepared for a future AI/Clay handoff."
            ),
        )
        st.caption(
            "Mock Mode saves these instructions and prepares a contact-specific prompt preview. "
            "It does not send the instructions to Clay or generate AI-written emails."
        )

        threshold = st.slider(
            "Minimum company and contact ICP score",
            min_value=0,
            max_value=100,
            value=75,
        )
        submitted = st.form_submit_button("Create campaign", type="primary")

    if submitted:
        if not campaign_name.strip():
            st.error("Please enter a campaign name.")
        elif not seniority and job_level != "Any":
            st.error("Select at least one seniority level, or choose Job Level = Any.")
        else:
            campaign_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO campaigns
                (id, name, industry, company_country, contact_country, target_titles,
                 min_score, status, created_at, current_cms, department, seniority, job_level,
                 email_sequence_instructions, clay_table_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    campaign_id,
                    campaign_name.strip(),
                    industry.strip(),
                    company_country.strip(),
                    contact_country.strip(),
                    target_titles.strip(),
                    threshold,
                    "Draft",
                    datetime.now().isoformat(timespec="seconds"),
                    current_cms.strip(),
                    department.strip(),
                    ", ".join(seniority),
                    job_level,
                    email_sequence_instructions.strip(),
                    clay_table_url.strip(),
                ),
            )
            conn.commit()
            st.session_state["active_campaign_id"] = campaign_id
            st.session_state["run_campaign_selector"] = campaign_id
            st.session_state["lead_campaign_selector"] = campaign_id
            st.success("Campaign configuration saved.")

    campaigns = load_campaigns()
    if not campaigns.empty:
        st.divider()
        st.subheader("Run mock research")
        st.caption(
            "This runs against fictional sample records only. It does not connect to Clay "
            "or consume Clay credits."
        )
        active_default = st.session_state.get("active_campaign_id")
        campaign_ids = campaigns["id"].tolist()
        default_index = campaign_ids.index(active_default) if active_default in campaign_ids else 0

        run_campaign_id = st.selectbox(
            "Select campaign to research",
            campaign_ids,
            index=default_index,
            format_func=lambda campaign_id: campaign_label(campaign_id, campaigns),
            key="run_campaign_selector",
        )

        if st.button("Start simulated research", type="primary"):
            campaign_row = conn.execute(
                "SELECT * FROM campaigns WHERE id = ?", (run_campaign_id,)
            ).fetchone()
            campaign_columns = [
                item[1] for item in conn.execute("PRAGMA table_info(campaigns)").fetchall()
            ]
            campaign = dict(zip(campaign_columns, campaign_row))

            # Re-running research replaces this campaign's previous mock results.
            records = run_mock_research(campaign)
            new_status = insert_mock_research_results(run_campaign_id, records)
            # Keep the Leads tab aligned with the campaign that was just researched.
            st.session_state["lead_campaign_selector"] = run_campaign_id

            qualified_count = sum(
                record["qualification"] == "Qualified" for record in records
            )
            st.session_state["last_research_notice"] = {
                "found": bool(records),
                "count": len(records),
                "qualified_count": qualified_count,
                "diagnostics": (
                    mock_research_diagnostics(campaign) if not records else []
                ),
            }
            st.rerun()

with tabs[2]:
    st.subheader("Qualified contacts & email review")
    campaigns = load_campaigns()

    if campaigns.empty:
        st.info("Create a campaign and run mock research first.")
    else:
        selected_campaign_id = st.selectbox(
            "Campaign",
            campaigns["id"].tolist(),
            format_func=lambda campaign_id: campaign_label(campaign_id, campaigns),
            key="lead_campaign_selector",
        )
        leads = pd.read_sql_query(
            "SELECT * FROM leads WHERE campaign_id = ?",
            conn,
            params=(selected_campaign_id,),
        )

        if leads.empty:
            st.info("No results yet. Run simulated research in the Create campaign tab.")
        else:
            metric1, metric2, metric3 = st.columns(3)
            metric1.metric("Matching contacts", len(leads))
            metric2.metric("Qualified", int((leads["qualification"] == "Qualified").sum()))
            metric3.metric(
                "Needs review", int((leads["review_status"] == "Needs review").sum())
            )

            visible_columns = [
                "company", "company_type", "industry", "company_cms",
                "contact_name", "title", "department", "seniority",
                "company_country", "contact_country", "company_score", "contact_score",
                "qualification",
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
                f"Department: {row['department']} | Seniority: {row['seniority']} | "
                f"CMS: {row['company_cms']}"
            )
            st.caption(
                f"Qualification: {row['qualification']} | Company score: "
                f"{row['company_score']} | Contact score: {row['contact_score']}"
            )
            st.write("Reason:", row["reason"])

            selected_campaign_row = conn.execute(
                "SELECT * FROM campaigns WHERE id = ?", (selected_campaign_id,)
            ).fetchone()
            campaign_columns = [
                item[1] for item in conn.execute("PRAGMA table_info(campaigns)").fetchall()
            ]
            selected_campaign = dict(zip(campaign_columns, selected_campaign_row))

            with st.expander("Email Sequence Instructions"):
                st.write(
                    selected_campaign.get("email_sequence_instructions", "")
                    or "No custom instructions were added to this campaign."
                )

            with st.expander("AI email-generation prompt preview (future Clay handoff)"):
                st.caption(
                    "This combines your campaign instructions with the selected contact's "
                    "details. In Mock Mode it is only a preview; no AI or Clay request is made."
                )
                st.code(
                    build_email_sequence_prompt(selected_campaign, row.to_dict()),
                    language="text",
                )

            for sequence_number in (1, 2, 3):
                st.markdown(f"**Email {sequence_number}**")
                st.text_input(
                    f"Subject {sequence_number}",
                    row[f"email{sequence_number}_subject"],
                    key=f"subject_{sequence_number}_{contact_id}",
                )
                st.text_area(
                    f"Body {sequence_number}",
                    row[f"email{sequence_number}_body"],
                    height=130,
                    key=f"body_{sequence_number}_{contact_id}",
                )

            if st.button("Mark contact approved for campaign review"):
                conn.execute(
                    "UPDATE leads SET review_status = ? WHERE id = ?",
                    ("Approved for campaign review", contact_id),
                )
                conn.commit()
                st.success("Marked as approved for review. No email has been sent.")

            st.caption(
                "The visible email drafts are mock examples. Custom instructions are saved "
                "and included in the prompt preview, but are not applied by an AI model in Mock Mode."
            )
            st.warning(
                "This MVP uses fictional sample data. It does not connect to Clay, "
                "enrich real records, or send emails."
            )

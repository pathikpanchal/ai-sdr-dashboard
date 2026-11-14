import streamlit as st
import pandas as pd
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "ai_sdr.db"

st.set_page_config(page_title="AI SDR Dashboard", page_icon="🎯", layout="wide")

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


def text_filter_matches(query, *values):
    """Free-text filters accept comma-separated alternatives; blank means no restriction."""
    query = normalize(query)
    if not query:
        return True
    options = [normalize(part) for part in str(query).split(",") if normalize(part)]
    searchable = [normalize(value) for value in values if normalize(value)]
    return any(option in item or item in option for option in options for item in searchable)


def country_filter_matches(query, country):
    query_norm = normalize(query)
    if not query_norm:
        return True

    aliases = {
        "uk": "united kingdom",
        "gb": "united kingdom",
        "great britain": "united kingdom",
        "us": "united states",
        "usa": "united states",
    }
    query_norm = aliases.get(query_norm, query_norm)
    country_norm = aliases.get(normalize(country), normalize(country))
    return query_norm in country_norm or country_norm in query_norm


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

    selected_rank = SENIORITY_RANK.get(selected_seniority, 1)
    actual_rank = SENIORITY_RANK.get(actual_seniority, 1)

    if job_level == "Above":
        return actual_rank >= selected_rank
    if job_level == "Below":
        return actual_rank <= selected_rank
    return actual_rank == selected_rank  # Exact


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
    else:
        col1, col2, col3 = st.columns(3)
        col1.metric("Campaigns", len(campaigns))
        col2.metric("Draft ready", int((campaigns["status"] == "Draft ready").sum()))
        col3.metric("Research simulated", int((campaigns["status"] == "Research simulated").sum()))

        display_columns = [
            "name", "industry", "company_country", "contact_country",
            "current_cms", "department", "seniority", "job_level",
            "total_companies", "total_contacts", "status", "created_at"
        ]
        campaign_display_labels = {
            "name": "Campaign Name",
            "industry": "Industry",
            "company_country": "Company Country",
            "contact_country": "Contact Country",
            "current_cms": "Current CMS",
            "department": "Department",
            "seniority": "Seniority",
            "job_level": "Job Level",
            "total_companies": "Total Companies",
            "total_contacts": "Total Contacts",
            "status": "Status",
            "created_at": "Created At",
        }
        st.dataframe(
            campaigns[display_columns].rename(columns=campaign_display_labels),
            use_container_width=True,
            hide_index=True,
        )

        selected_id = st.selectbox(
            "Select a campaign",
            campaigns["id"].tolist(),
            format_func=lambda campaign_id: campaign_label(campaign_id, campaigns),
            key="overview_campaign",
        )
        selected_row = campaigns[campaigns["id"] == selected_id].iloc[0]

        with st.expander("View selected campaign filters"):
            st.write(f"**Industry:** {selected_row['industry']}")
            st.write(f"**Company country:** {selected_row['company_country']}")
            st.write(f"**Contact country:** {selected_row['contact_country']}")
            st.write(f"**Current CMS:** {selected_row['current_cms'] or 'Any'}")
            st.write(f"**Department:** {selected_row['department'] or 'Any'}")
            st.write(f"**Seniority:** {selected_row['seniority']}")
            st.write(f"**Job level:** {selected_row['job_level']}")
            st.write(f"**Minimum ICP score:** {selected_row['min_score']}")
            st.write("**Email Sequence Instructions:**")
            st.write(
                selected_row.get("email_sequence_instructions", "")
                or "No custom instructions added."
            )

        action_col1, action_col2 = st.columns(2)
        with action_col1:
            if st.button("Duplicate selected campaign"):
                new_id = str(uuid.uuid4())
                conn.execute(
                    """
                    INSERT INTO campaigns
                    (id, name, industry, company_country, contact_country, target_titles,
                     min_score, status, created_at, current_cms, department, seniority, job_level,
                     email_sequence_instructions)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        new_id,
                        selected_row["name"] + " (Copy)",
                        selected_row["industry"],
                        selected_row["company_country"],
                        selected_row["contact_country"],
                        selected_row["target_titles"] or "",
                        int(selected_row["min_score"]),
                        "Draft",
                        datetime.now().isoformat(timespec="seconds"),
                        selected_row["current_cms"] or "",
                        selected_row["department"] or "",
                        selected_row["seniority"] or "Manager",
                        selected_row["job_level"] or "Above",
                        selected_row.get("email_sequence_instructions", "") or "",
                    ),
                )
                conn.commit()
                st.success("Campaign duplicated with all filters.")
                st.rerun()

        with action_col2:
            confirm_delete = st.checkbox(
                "I confirm I want to delete this campaign",
                key=f"confirm_delete_{selected_id}",
            )
            if st.button("Delete selected campaign", disabled=not confirm_delete):
                conn.execute("DELETE FROM leads WHERE campaign_id = ?", (selected_id,))
                conn.execute("DELETE FROM campaigns WHERE id = ?", (selected_id,))
                conn.commit()
                st.success("Campaign and its local mock leads have been deleted.")
                st.rerun()

with tabs[1]:
    st.subheader("Create campaign")
    st.caption(
        "Industry, countries, CMS and department are free-text fields. "
        "For fields that accept multiple values, separate them with commas."
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
            seniority = st.selectbox(
                "Seniority",
                SENIORITY_OPTIONS,
                index=SENIORITY_OPTIONS.index("Manager"),
            )
        with job_level_col:
            job_level = st.selectbox(
                "Job Level",
                JOB_LEVEL_OPTIONS,
                index=JOB_LEVEL_OPTIONS.index("Above"),
                help=(
                    "Above includes the selected seniority and every higher level. "
                    "Below includes the selected level and every lower level."
                ),
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
        else:
            campaign_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO campaigns
                (id, name, industry, company_country, contact_country, target_titles,
                 min_score, status, created_at, current_cms, department, seniority, job_level,
                 email_sequence_instructions)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    campaign_id,
                    campaign_name.strip(),
                    industry.strip(),
                    company_country.strip(),
                    contact_country.strip(),
                    "",
                    threshold,
                    "Draft",
                    datetime.now().isoformat(timespec="seconds"),
                    current_cms.strip(),
                    department.strip(),
                    seniority,
                    job_level,
                    email_sequence_instructions.strip(),
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
            conn.execute("DELETE FROM leads WHERE campaign_id = ?", (run_campaign_id,))
            records = run_mock_research(campaign)

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
                new_status = "Draft ready"
            else:
                new_status = "No matches"

            conn.execute(
                "UPDATE campaigns SET status = ? WHERE id = ?",
                (new_status, run_campaign_id),
            )
            conn.commit()
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

import streamlit as st
import pandas as pd
import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "ai_sdr.db"

st.set_page_config(page_title="AI SDR Dashboard", page_icon="🎯", layout="wide")

def db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""CREATE TABLE IF NOT EXISTS campaigns (
        id TEXT PRIMARY KEY, name TEXT, industry TEXT, company_country TEXT,
        contact_country TEXT, target_titles TEXT, min_score INTEGER,
        status TEXT, created_at TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS leads (
        id TEXT PRIMARY KEY, campaign_id TEXT, company TEXT, website TEXT,
        company_type TEXT, company_country TEXT, contact_name TEXT, title TEXT,
        contact_country TEXT, email TEXT, company_score INTEGER,
        contact_score INTEGER, qualification TEXT, reason TEXT,
        email1_subject TEXT, email1_body TEXT, email2_subject TEXT, email2_body TEXT,
        email3_subject TEXT, email3_body TEXT, review_status TEXT
    )""")
    conn.commit()
    return conn

conn = db()

def sample_records(campaign_id, threshold):
    # Synthetic records only. No Clay API calls or credit-consuming actions.
    rows = [
        ("Northbridge Pharma Group", "https://northbridge.example", "Manufacturer & distributor",
         "United Kingdom", "Amelia Carter", "Head of Marketing", "United Kingdom", "amelia.carter@northbridge.example", 94, 92,
         "Company operates across pharmaceutical manufacturing and distribution; contact leads marketing."),
        ("Westhaven Pharmaceutical Services", "https://westhaven.example", "Pharmaceutical services",
         "United Kingdom", "Oliver Bennett", "Marketing Director", "United Kingdom", "oliver.bennett@westhaven.example", 88, 89,
         "UK pharmaceutical services business; contact has a senior marketing leadership title."),
        ("Crownwell Pharma Distribution", "https://crownwell.example", "Wholesaler & distributor",
         "United Kingdom", "Sophie Williams", "Chief Marketing Officer", "United Kingdom", "sophie.williams@crownwell.example", 91, 96,
         "UK pharmaceutical distributor; contact is the executive marketing owner."),
        ("Meridian BioHealth", "https://meridianbio.example", "Biotechnology",
         "United Kingdom", "Noah Hughes", "Head of Marketing", "United Kingdom", "noah.hughes@meridianbio.example", 62, 88,
         "Biotechnology-only profile; included for review because broader life sciences may need separate treatment."),
        ("Harborview Pharma Ltd", "https://harborview.example", "Pharmaceutical manufacturer",
         "United Kingdom", "Isabella Reed", "Marketing Manager", "United Kingdom", "isabella.reed@harborview.example", 90, 58,
         "Company fits, but contact seniority is below the requested Head level."),
        ("Alpine Pharma Europe", "https://alpine.example", "Pharmaceutical manufacturer",
         "Germany", "Lucas Meyer", "VP Marketing", "Germany", "lucas.meyer@alpine.example", 86, 94,
         "Company and contact are outside the requested UK geography."),
    ]
    out = []
    for r in rows:
        cs, ps = r[8], r[9]
        qualification = "Qualified" if cs >= threshold and ps >= threshold and r[3] == "United Kingdom" and r[6] == "United Kingdom" else "Review / Exclude"
        out.append({
            "id": str(uuid.uuid4()), "campaign_id": campaign_id, "company": r[0], "website": r[1],
            "company_type": r[2], "company_country": r[3], "contact_name": r[4], "title": r[5],
            "contact_country": r[6], "email": r[7], "company_score": cs, "contact_score": ps,
            "qualification": qualification, "reason": r[10],
            "email1_subject": "A thought for {{company}}'s marketing team",
            "email1_body": f"Hi {r[4].split()[0]},\\n\\nI was looking at {{company}} and thought it could be worth comparing notes on how pharmaceutical businesses are approaching marketing.\\n\\nWould you be open to a brief conversation?",
            "email2_subject": "Re: marketing priorities at {{company}}",
            "email2_body": f"Hi {r[4].split()[0]},\\n\\nFollowing up in case this is relevant. We help teams review their current approach and identify practical opportunities to improve results.\\n\\nWould a short overview be useful?",
            "email3_subject": "Should I close the loop?",
            "email3_body": f"Hi {r[4].split()[0]},\\n\\nI appreciate you may have other priorities. Should I close the loop for now, or would a short conversation be worthwhile?",
            "review_status": "Needs review"
        })
    return out

st.title("AI SDR Dashboard")
st.caption("Phase I MVP · Mock Mode · No Clay API calls or Clay credits used")

with st.sidebar:
    st.header("Execution mode")
    st.success("MOCK MODE — ON")
    st.caption("This version uses synthetic sample data. Clay integration is not connected.")
    st.divider()
    st.caption("Phase I: campaign setup → simulated prospecting → scoring → email drafts → human review.")

tabs = st.tabs(["Campaigns", "Create campaign", "Leads & email review"])

with tabs[0]:
    st.subheader("Campaign overview")
    campaigns = pd.read_sql_query("SELECT * FROM campaigns ORDER BY created_at DESC", conn)
    if campaigns.empty:
        st.info("No campaigns yet. Create your first campaign in the next tab.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Campaigns", len(campaigns))
        c2.metric("Awaiting review", int((campaigns["status"] == "Draft ready").sum()))
        c3.metric("Completed research", int((campaigns["status"] == "Research simulated").sum()))
        st.dataframe(campaigns[["name","industry","company_country","status","created_at"]], use_container_width=True, hide_index=True)
        selected = st.selectbox("Select campaign to view", campaigns["id"].tolist(),
                                format_func=lambda x: campaigns.loc[campaigns.id == x, "name"].iloc[0])
        if st.button("Duplicate selected campaign"):
            source = campaigns[campaigns.id == selected].iloc[0]
            new_id = str(uuid.uuid4())
            conn.execute("INSERT INTO campaigns VALUES (?,?,?,?,?,?,?,?,?)",
                (new_id, source["name"] + " (Copy)", source["industry"], source["company_country"],
                 source["contact_country"], source["target_titles"], int(source["min_score"]),
                 "Draft", datetime.now().isoformat(timespec="seconds")))
            conn.commit()
            st.success("Campaign duplicated. Update its criteria in the campaign record or create a new campaign.")
            st.rerun()

with tabs[1]:
    st.subheader("Create campaign")
    with st.form("create_campaign"):
        name = st.text_input("Campaign name", "UK Pharmaceutical Marketing Decision Makers")
        industry = st.text_input("Industry", "All pharmaceuticals")
        company_country = st.text_input("Company country", "United Kingdom")
        contact_country = st.text_input("Contact country", "United Kingdom")
        titles = st.text_area("Target job titles", "Head of Marketing\nMarketing Director\nVP Marketing\nChief Marketing Officer")
        threshold = st.slider("Minimum company and contact ICP score", 0, 100, 75)
        submitted = st.form_submit_button("Create campaign")
    if submitted:
        cid = str(uuid.uuid4())
        conn.execute("INSERT INTO campaigns VALUES (?,?,?,?,?,?,?,?,?)",
            (cid, name, industry, company_country, contact_country, titles, threshold,
             "Draft", datetime.now().isoformat(timespec="seconds")))
        conn.commit()
        st.session_state["new_campaign_id"] = cid
        st.success("Campaign configuration saved.")
    if st.session_state.get("new_campaign_id"):
        cid = st.session_state["new_campaign_id"]
        st.info("Next: run the simulated research below. This does not connect to Clay.")
        if st.button("Start simulated research", type="primary"):
            camp = conn.execute("SELECT min_score FROM campaigns WHERE id=?", (cid,)).fetchone()
            records = sample_records(cid, int(camp[0]))
            conn.executemany("""INSERT INTO leads VALUES (
                :id,:campaign_id,:company,:website,:company_type,:company_country,:contact_name,:title,
                :contact_country,:email,:company_score,:contact_score,:qualification,:reason,
                :email1_subject,:email1_body,:email2_subject,:email2_body,:email3_subject,:email3_body,:review_status
            )""", records)
            conn.execute("UPDATE campaigns SET status='Draft ready' WHERE id=?", (cid,))
            conn.commit()
            st.success(f"Simulation complete. {sum(x['qualification']=='Qualified' for x in records)} sample contacts qualified. Synthetic data only.")
            st.rerun()

with tabs[2]:
    st.subheader("Qualified contacts & email review")
    camps = pd.read_sql_query("SELECT id, name FROM campaigns ORDER BY created_at DESC", conn)
    if camps.empty:
        st.info("Create a campaign and run simulated research first.")
    else:
        cid = st.selectbox("Campaign", camps.id.tolist(), format_func=lambda x: camps.loc[camps.id == x, "name"].iloc[0], key="lead_campaign")
        leads = pd.read_sql_query("SELECT * FROM leads WHERE campaign_id=?", conn, params=(cid,))
        if leads.empty:
            st.info("No results yet. Run simulated research from the Create campaign tab.")
        else:
            a,b,c = st.columns(3)
            a.metric("Contacts", len(leads))
            b.metric("Qualified", int((leads.qualification == "Qualified").sum()))
            c.metric("Needs review", int((leads.review_status == "Needs review").sum()))
            st.dataframe(leads[["company","company_type","contact_name","title","company_country","contact_country","company_score","contact_score","qualification"]], use_container_width=True, hide_index=True)
            contact_id = st.selectbox("Choose contact to review", leads.id.tolist(),
                format_func=lambda x: leads.loc[leads.id == x, "contact_name"].iloc[0] + " — " + leads.loc[leads.id == x, "company"].iloc[0])
            row = leads[leads.id == contact_id].iloc[0]
            st.markdown(f"**{row.contact_name} · {row.title} · {row.company}**")
            st.caption(f"Qualification: {row.qualification} | Company score: {row.company_score} | Contact score: {row.contact_score}")
            st.write("Reason:", row.reason)
            for n in (1,2,3):
                st.markdown(f"**Email {n}**")
                st.text_input(f"Subject {n}", row[f"email{n}_subject"], key=f"sub{n}_{contact_id}")
                st.text_area(f"Body {n}", row[f"email{n}_body"].replace("\\n", "\n"), height=130, key=f"body{n}_{contact_id}")
            if st.button("Mark contact approved for campaign review"):
                conn.execute("UPDATE leads SET review_status='Approved for campaign review' WHERE id=?", (contact_id,))
                conn.commit()
                st.success("Marked as approved for review. No email has been sent.")
            st.warning("This MVP does not send emails or launch campaigns. All records and email addresses are synthetic.")

# AI SDR Dashboard — Phase I Mock MVP

## What this build does
- Creates and stores campaign configurations locally.
- Includes a first example campaign for UK pharmaceutical marketing decision-makers.
- Simulates company/contact discovery using clearly synthetic sample records.
- Applies configurable company and contact score thresholds.
- Generates three sample email drafts per contact.
- Supports campaign duplication and contact review.

## Credit safety
This MVP does **not** connect to Clay, call any Clay API, enrich real records, or send emails.
It therefore uses zero Clay credits. All sample companies, contacts, and `.example` email addresses are synthetic.

## Run locally
1. Install Python 3.10 or newer.
2. Extract the ZIP.
3. Open a terminal in this folder.
4. Run:
   ```bash
   python -m venv .venv
   ```
5. Activate the environment:
   - Windows PowerShell: `.venv\Scripts\Activate.ps1`
   - macOS/Linux: `source .venv/bin/activate`
6. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
7. Start the dashboard:
   ```bash
   streamlit run app.py
   ```

Streamlit will display a local browser URL, usually http://localhost:8501.

## Current limitations
- Mock data only; no live Clay integration.
- Email copy uses deterministic sample templates, not a live LLM.
- Approval is recorded locally; no campaign is sent.
- SQLite database (`ai_sdr.db`) is created automatically in this folder.

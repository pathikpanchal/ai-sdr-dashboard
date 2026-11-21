# AI SDR Dashboard — Build Campaign Data fix

## What changed

- Build Campaign Data now runs a real Clay company search followed by a people search scoped to the companies returned by that search.
- Searches are paginated (up to 200 companies and 200 contacts per run) and deduplicated across pages.
- Job-title results are no longer rejected by a second strict local substring check after Clay has already applied the title search. Clay smart title matching is selected when supported by the live filter schema.
- Clay schema lookup, contact filter construction, and API calls are covered by stage-specific error logging.
- Campaign status is only set to `Ready for Review` after both searches complete and both result sets are delivered to the configured Clay tables.
- Search results are sent to pre-created Clay table webhook sources. Webhook requests use stable idempotency keys and retry transient failures.
- Campaigns store a Clay workbook URL, Companies table webhook URL, and Contacts table webhook URL.
- Changing search criteria requires re-approval and clears the previous local search results. The dashboard cannot delete rows already sent to Clay, so the existing Clay tables must be cleared or replaced before rebuilding with changed criteria.
- Current CMS and email enrichment are intentionally not automated. Sales should run these enrichments in Clay after reviewing the company/contact lists.

## Clay setup required for each campaign

The dashboard does not create Clay workbooks or tables through the Public API. Create these once in Clay for each campaign:

1. Create one workbook for the campaign.
2. Create a `Companies` table and a `Contacts` table in that workbook.
3. In each table, use `+ Add` → `Webhooks` → `Monitor webhook` and copy the webhook URL.
4. Optionally enable webhook authentication and copy the auth token at setup time.
5. In the dashboard campaign form or **Edit Campaign**, enter:
   - Clay Workbook Link
   - Companies Table Webhook URL
   - Contacts Table Webhook URL
   - Optional Companies and Contacts webhook auth tokens
6. Save the campaign settings. Destination-only changes do not reset criteria approval.

Clay webhook documentation: https://university.clay.com/docs/webhook-integration-guide

## Streamlit Secrets

Add the Clay Public API key in Streamlit Cloud → App settings → Secrets:

```toml
[clay]
api_key = "YOUR_CLAY_PUBLIC_API_KEY"
```

Do not commit API keys, webhook URLs, or webhook auth tokens to GitHub.

## Current sourcing scope

- Company Search: Industry and Company Country (headquarters).
- Contact Search: target company identifiers from the company search, Job Titles, Department, Seniority/Job Level, and Contact Country.
- Current CMS: stored as an enrichment target only; it is not applied as a search filter in this phase.
- Minimum ICP Score: shown as a review target; it is not a Clay Search API filter in this phase.
- Up to 200 companies and 200 contacts are collected per run. The dashboard warns when Clay indicates more results are available.

## Important deployment/security note

The dashboard still uses its existing mock identity selector and local SQLite database. That is not secure authentication or a shared production database. A Clay webhook URL can authorize writes to its destination table. Keep the Streamlit app private and do not use real campaign webhook URLs or confidential prospect data until real authentication and appropriate production storage/access controls are implemented.

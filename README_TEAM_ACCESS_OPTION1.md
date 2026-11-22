# AI SDR Dashboard — Team & Access (Option 1)

This update applies the approved compact Team & Access layout to the current dashboard baseline.

## What changed

- Replaced the previous invite form with a single-row **Email ID**, **Dashboard access (View / Edit)**, and **Share** form.
- Added a **Shared Users** list with email search, current access, invitation status, shared date, permission editing, and access removal.
- The UI uses the requested labels `View` and `Edit`; the existing database permission values remain `View Only` and `Can Edit` so the rest of the dashboard permission checks continue to work.
- The invitee display name is inferred from the email prefix because the requested share form only asks for Email ID and Dashboard access.
- Restored the SMTP invitation helpers and invitation acceptance handler referenced by the previous page but missing from this baseline.
- Invitations expire after 7 days. A recipient can click the emailed invitation link and accept it.
- The permission applies workspace-wide, to all campaigns.

## Streamlit Secrets for email invitations

Add an `[email]` section to Streamlit Cloud → App settings → Secrets. Example:

```toml
[email]
smtp_server = "smtp.gmail.com"
smtp_port = 587
sender_email = "your.account@gmail.com"
app_password = "your-google-app-password"
sender_name = "AI SDR Dashboard"
dashboard_url = "https://your-app-name.streamlit.app"
```

Use a Google App Password, not the normal Gmail password. Keep these settings in Streamlit Secrets; do not commit them to GitHub or share them in chat.

If email is not configured, the Share action will explain what needs to be configured rather than silently creating an invitation that cannot be delivered.

## Important security limitation

The dashboard is still in **Mock Mode**. The sidebar identity selector is a test identity switcher, not real authentication. The invitation link activates a simulated identity; it does not verify that the visitor controls the invited email address. The current SQLite database is also not a production-grade shared identity store.

Therefore, this update improves the invitation UI and test workflow, but it does **not** make the dashboard secure for real company-wide use. Before relying on View/Edit permissions for confidential data, implement real authentication (for example, an OIDC provider) and a shared persistent database, and remove the mock identity switcher.

## Files

- `app.py` — updated dashboard
- `requirements.txt` — unchanged dependencies

## Validation performed

- Python syntax/compile check passed.
- View/Edit permission mapping passed.
- SQLite invitation/access lifecycle smoke test passed.
- Team & Access UI contract checks passed.
- Live SMTP delivery and live Streamlit browser rendering were not tested in this environment.

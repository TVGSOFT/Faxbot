
# Getting Started

Welcome to Faxbot! This section will help you get up and running quickly.

[:material-wrench: Setup Wizard](admin-console/setup-wizard.md){ .md-button .md-button--primary }
[:material-monitor-dashboard: Admin Console](admin-console.md){ .md-button }
[:material-cloud-lock: Deployment](deployment.md){ .md-button }

<div class="grid cards" markdown>

- :material-rocket-launch: **Launch Faxbot**  
  Start the API and open the Admin Console.  
  [Follow the guide](#launch-faxbot)

- :material-wrench: **Complete the Setup Wizard**  
  Pick a backend, paste creds, apply.  
  [See steps](#complete-the-setup-wizard)

- :material-cog: **What to do next**  
  Provider playbooks, keys, storage, diagnostics.  
  [Next steps](#what-to-do-next)

</div>

## What is Faxbot?

Faxbot is the first and only open‑source, self‑hostable fax API that combines:

- Simple REST API for sending faxes
- Multiple backend options (cloud and self‑hosted)
- AI assistant integration via MCP
- HIPAA‑aligned defaults with relaxed profiles for non‑PHI
- Developer SDKs for Node.js and Python

## Launch Faxbot

1. Copy `.env.example` to `.env` (you can adjust later in the UI).
2. Start the API: `docker compose up -d --build api`
3. Open the Admin Console at `http://localhost:8080/admin/ui/`.

??? tip "Console not found?"
    Add `ENABLE_LOCAL_ADMIN=true` to `.env`, then restart the API.

## Complete the Setup Wizard

1. In the console, open **Setup Wizard**.
2. Choose your outbound provider (Phaxio, Sinch, SIP/Asterisk, SignalWire, or Test Mode).
3. Enter credentials and security preferences (helper text and “Learn more” links guide each field).
4. Apply settings. The API reloads, and your backend is ready.

## What to do next

- Follow provider guides under [Backends](setup/index.md) for credentials, networking, and HIPAA notes.
- Manage keys, storage, inbound receiving, and diagnostics from the Admin Console tabs (each screen links to matching docs).
- Integrate your app using the [Node](sdks/node.md) or [Python](sdks/python.md) SDK once outbound faxing is verified.

## Need Help?

See our [Contributing guide](getting-started/contributing.md) for support options. Mention which backend you’re using so we can point you to the right playbook.

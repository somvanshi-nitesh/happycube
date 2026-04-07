# Grafana → ITSM → Jira Automation Agent

This folder contains a lightweight Python agent that:

1. Queries Grafana Loki logs for error entries.
2. Creates an ITSM incident for new issues.
3. Monitors resolved ITSM incidents and creates Jira defects.
4. Assigns each Jira defect to the configured development team account.

## File

- `itsm_jira_agent.py` - end-to-end automation workflow.

## Environment variables

Required:

- `GRAFANA_BASE_URL` (e.g. `https://grafana.example.com`)
- `GRAFANA_TOKEN`
- `GRAFANA_QUERY` (Loki query, e.g. `{app="payments"}`)
- `ITSM_BASE_URL`
- `ITSM_TOKEN`
- `ITSM_SERVICE`
- `ITSM_ASSIGNMENT_GROUP`
- `JIRA_BASE_URL` (e.g. `https://company.atlassian.net`)
- `JIRA_EMAIL`
- `JIRA_API_TOKEN`
- `JIRA_PROJECT_KEY`
- `JIRA_ISSUE_TYPE` (typically `Bug`)
- `JIRA_DEV_TEAM_ACCOUNT_ID` (Jira account ID for assignee)

Optional:

- `POLL_INTERVAL_SECONDS` (default `60`)
- `GRAFANA_LOOKBACK_SECONDS` (default `300`)
- `AGENT_MODE` = `once` (default) or `forever`

## Usage

```bash
python3 agents/itsm_jira_agent.py
```

Daemon mode:

```bash
AGENT_MODE=forever python3 agents/itsm_jira_agent.py
```

## Notes

- API paths are intentionally generic (`/api/incidents`, Jira `/rest/api/3/issue`).
- Adapt request/response payloads to your ITSM provider (ServiceNow, BMC, etc.).
- The script avoids duplicate incident creation during runtime using event fingerprints.

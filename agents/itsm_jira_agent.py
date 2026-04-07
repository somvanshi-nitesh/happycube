#!/usr/bin/env python3
"""Grafana -> ITSM -> Jira incident/defect automation agent.

Flow:
1) Poll Grafana Loki logs for error patterns.
2) Open ITSM incident tickets for matched alerts.
3) Poll open incidents and create Jira defects from enriched ITSM details.
4) Assign defects to the configured development team.

This script is intentionally vendor-neutral and API-driven.
Set credentials/endpoints through environment variables.
"""

from __future__ import annotations

import base64
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class Config:
    grafana_base_url: str
    grafana_token: str
    grafana_query: str
    grafana_lookback_seconds: int

    itsm_base_url: str
    itsm_token: str
    itsm_service: str
    itsm_assignment_group: str

    jira_base_url: str
    jira_email: str
    jira_api_token: str
    jira_project_key: str
    jira_issue_type: str
    jira_dev_team_account_id: str

    poll_interval_seconds: int = 60

    @staticmethod
    def from_env() -> "Config":
        required = {
            "GRAFANA_BASE_URL",
            "GRAFANA_TOKEN",
            "GRAFANA_QUERY",
            "ITSM_BASE_URL",
            "ITSM_TOKEN",
            "ITSM_SERVICE",
            "ITSM_ASSIGNMENT_GROUP",
            "JIRA_BASE_URL",
            "JIRA_EMAIL",
            "JIRA_API_TOKEN",
            "JIRA_PROJECT_KEY",
            "JIRA_ISSUE_TYPE",
            "JIRA_DEV_TEAM_ACCOUNT_ID",
        }
        missing = [k for k in required if not os.getenv(k)]
        if missing:
            raise ValueError(f"Missing required env vars: {', '.join(sorted(missing))}")

        return Config(
            grafana_base_url=os.environ["GRAFANA_BASE_URL"].rstrip("/"),
            grafana_token=os.environ["GRAFANA_TOKEN"],
            grafana_query=os.environ["GRAFANA_QUERY"],
            grafana_lookback_seconds=int(os.getenv("GRAFANA_LOOKBACK_SECONDS", "300")),
            itsm_base_url=os.environ["ITSM_BASE_URL"].rstrip("/"),
            itsm_token=os.environ["ITSM_TOKEN"],
            itsm_service=os.environ["ITSM_SERVICE"],
            itsm_assignment_group=os.environ["ITSM_ASSIGNMENT_GROUP"],
            jira_base_url=os.environ["JIRA_BASE_URL"].rstrip("/"),
            jira_email=os.environ["JIRA_EMAIL"],
            jira_api_token=os.environ["JIRA_API_TOKEN"],
            jira_project_key=os.environ["JIRA_PROJECT_KEY"],
            jira_issue_type=os.environ["JIRA_ISSUE_TYPE"],
            jira_dev_team_account_id=os.environ["JIRA_DEV_TEAM_ACCOUNT_ID"],
            poll_interval_seconds=int(os.getenv("POLL_INTERVAL_SECONDS", "60")),
        )


class AgentHttpClient:
    def request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        for key, value in headers.items():
            req.add_header(key, value)
        if body is not None:
            req.add_header("Content-Type", "application/json")

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                content = response.read().decode("utf-8")
                return json.loads(content) if content else {}
        except urllib.error.HTTPError as err:
            detail = err.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {err.code} for {url}: {detail}") from err


class OpsAutomationAgent:
    def __init__(self, cfg: Config, http: Optional[AgentHttpClient] = None) -> None:
        self.cfg = cfg
        self.http = http or AgentHttpClient()
        self._seen_fingerprints: set[str] = set()

    def _now_ns(self) -> int:
        return int(datetime.now(tz=timezone.utc).timestamp() * 1_000_000_000)

    def _build_grafana_query_url(self) -> str:
        end_ns = self._now_ns()
        start_ns = end_ns - self.cfg.grafana_lookback_seconds * 1_000_000_000
        qs = urllib.parse.urlencode(
            {
                "query": self.cfg.grafana_query,
                "start": str(start_ns),
                "end": str(end_ns),
                "direction": "backward",
                "limit": "100",
            }
        )
        return f"{self.cfg.grafana_base_url}/loki/api/v1/query_range?{qs}"

    def fetch_error_events(self) -> List[Dict[str, Any]]:
        url = self._build_grafana_query_url()
        payload = self.http.request(
            "GET",
            url,
            headers={"Authorization": f"Bearer {self.cfg.grafana_token}"},
        )
        results = payload.get("data", {}).get("result", [])
        events: List[Dict[str, Any]] = []
        for stream in results:
            labels = stream.get("stream", {})
            for ts_ns, line in stream.get("values", []):
                if self._is_error_log(line):
                    events.append(
                        {
                            "timestamp_ns": ts_ns,
                            "message": line,
                            "labels": labels,
                            "fingerprint": self._fingerprint(ts_ns, line, labels),
                        }
                    )
        return events

    def _is_error_log(self, line: str) -> bool:
        return bool(re.search(r"\b(error|exception|fatal|panic)\b", line, flags=re.IGNORECASE))

    def _fingerprint(self, ts_ns: str, line: str, labels: Dict[str, Any]) -> str:
        app = labels.get("app", "unknown")
        return f"{app}:{ts_ns}:{hash(line) % 10_000_000}"

    def create_itsm_incident(self, event: Dict[str, Any]) -> Dict[str, Any]:
        body = {
            "short_description": f"Grafana alert: {event['labels'].get('app', 'unknown')} error detected",
            "description": (
                "Log-derived incident created by OpsAutomationAgent.\n"
                f"Timestamp (ns): {event['timestamp_ns']}\n"
                f"Labels: {json.dumps(event['labels'])}\n"
                f"Log line: {event['message']}"
            ),
            "service": self.cfg.itsm_service,
            "assignment_group": self.cfg.itsm_assignment_group,
            "source": "grafana-loki",
            "external_correlation_id": event["fingerprint"],
        }
        return self.http.request(
            "POST",
            f"{self.cfg.itsm_base_url}/api/incidents",
            headers={"Authorization": f"Bearer {self.cfg.itsm_token}"},
            body=body,
        )

    def fetch_itsm_incidents_ready_for_defect(self) -> Iterable[Dict[str, Any]]:
        payload = self.http.request(
            "GET",
            f"{self.cfg.itsm_base_url}/api/incidents?state=resolved&defect_created=false",
            headers={"Authorization": f"Bearer {self.cfg.itsm_token}"},
        )
        return payload.get("results", [])

    def create_jira_defect(self, incident: Dict[str, Any]) -> Dict[str, Any]:
        body = {
            "fields": {
                "project": {"key": self.cfg.jira_project_key},
                "issuetype": {"name": self.cfg.jira_issue_type},
                "summary": f"Defect from ITSM incident {incident.get('number', 'UNKNOWN')}",
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": (
                                        f"ITSM Incident: {incident.get('number')}\n"
                                        f"Priority: {incident.get('priority')}\n"
                                        f"Service: {incident.get('service')}\n\n"
                                        f"Symptoms:\n{incident.get('description', '')}"
                                    ),
                                }
                            ],
                        }
                    ],
                },
                "assignee": {"id": self.cfg.jira_dev_team_account_id},
                "labels": ["itsm", "auto-generated", "defect"],
            }
        }
        auth = f"{self.cfg.jira_email}:{self.cfg.jira_api_token}".encode("utf-8")
        basic = base64.b64encode(auth).decode("ascii")
        return self.http.request(
            "POST",
            f"{self.cfg.jira_base_url}/rest/api/3/issue",
            headers={"Authorization": f"Basic {basic}"},
            body=body,
        )

    def mark_incident_defect_created(self, incident_id: str, jira_key: str) -> Dict[str, Any]:
        return self.http.request(
            "PATCH",
            f"{self.cfg.itsm_base_url}/api/incidents/{incident_id}",
            headers={"Authorization": f"Bearer {self.cfg.itsm_token}"},
            body={"defect_created": True, "defect_key": jira_key},
        )

    def run_once(self) -> None:
        events = self.fetch_error_events()
        for event in events:
            if event["fingerprint"] in self._seen_fingerprints:
                continue
            incident = self.create_itsm_incident(event)
            self._seen_fingerprints.add(event["fingerprint"])
            print(f"Created ITSM incident: {incident.get('number', incident)}")

        for incident in self.fetch_itsm_incidents_ready_for_defect():
            jira_issue = self.create_jira_defect(incident)
            jira_key = jira_issue.get("key", "UNKNOWN")
            self.mark_incident_defect_created(str(incident.get("id")), jira_key)
            print(f"Created Jira defect {jira_key} for incident {incident.get('number')}")

    def run_forever(self) -> None:
        while True:
            try:
                self.run_once()
            except Exception as exc:  # noqa: BLE001 - top-level safety guard for daemon mode
                print(f"Agent cycle failed: {exc}")
            time.sleep(self.cfg.poll_interval_seconds)


def main() -> None:
    cfg = Config.from_env()
    agent = OpsAutomationAgent(cfg)
    mode = os.getenv("AGENT_MODE", "once").lower()
    if mode == "forever":
        agent.run_forever()
    else:
        agent.run_once()


if __name__ == "__main__":
    main()

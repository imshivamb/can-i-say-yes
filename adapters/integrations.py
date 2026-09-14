"""Small live adapters with deterministic, dependency-free HTTP fallbacks.

The domain and tools remain provider-agnostic. Credentials are optional locally:
when absent, callers use the existing file-backed world and outbox.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

import boto3

from domain.models import CalendarEvent, EmailMessage


class InboundMailProvider(Protocol):
    def poll(self, query: str) -> list[EmailMessage]:
        ...


class CalendarProvider(Protocol):
    def events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        ...


class OutboundMailProvider(Protocol):
    def send(self, *, to: str, subject: str, body: str) -> DeliveryResult:
        ...


@dataclass(frozen=True)
class DeliveryResult:
    provider: str
    message_id: str
    status: str


def live_integrations_enabled() -> bool:
    return os.getenv("CISAY_LIVE_INTEGRATIONS", "").lower() in {"1", "true", "yes"}


def live_outbound_enabled() -> bool:
    return live_integrations_enabled() and bool(os.getenv("SES_FROM_ADDRESS"))


class GmailAdapter:
    """Read Gmail using a pre-authorized OAuth access token.

    Token acquisition is deliberately outside this project; use a short-lived
    token or workload identity in deployment. The adapter never sends mail.
    """

    base_url = "https://gmail.googleapis.com/gmail/v1/users/me"

    def __init__(self, access_token: str | None = None) -> None:
        self.access_token = access_token or os.getenv("GMAIL_ACCESS_TOKEN")
        if not self.access_token:
            raise ValueError("GMAIL_ACCESS_TOKEN is required for the live Gmail adapter")

    def _get(self, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        query = f"?{urllib.parse.urlencode(params)}" if params else ""
        request = urllib.request.Request(
            f"{self.base_url}/{path}{query}",
            headers={"Authorization": f"Bearer {self.access_token}"},
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read())

    def poll(self, query: str) -> list[EmailMessage]:
        listing = self._get("messages", {"q": query, "maxResults": "25"})
        messages: list[EmailMessage] = []
        for item in listing.get("messages", []):
            raw = self._get(f"messages/{item['id']}", {"format": "full"})
            headers = {
                header["name"].lower(): header["value"]
                for header in raw.get("payload", {}).get("headers", [])
            }
            timestamp = datetime.fromtimestamp(
                int(raw.get("internalDate", "0")) / 1000
            ).astimezone()
            messages.append(
                EmailMessage(
                    id=f"eml_gmail_{raw['id']}",
                    sent_at=timestamp,
                    from_addr=headers.get("from", ""),
                    to_addr=[headers.get("to", "")],
                    subject=headers.get("subject", ""),
                    body=_gmail_body(raw.get("payload", {})),
                    labels=raw.get("labelIds", []),
                )
            )
        return messages


class GoogleCalendarAdapter:
    """Read a Google Calendar using a pre-authorized OAuth access token."""

    base_url = "https://www.googleapis.com/calendar/v3/calendars"

    def __init__(
        self,
        access_token: str | None = None,
        calendar_id: str | None = None,
    ) -> None:
        self.access_token = access_token or os.getenv("GOOGLE_ACCESS_TOKEN")
        self.calendar_id = calendar_id or os.getenv("GOOGLE_CALENDAR_ID", "primary")
        if not self.access_token:
            raise ValueError("GOOGLE_ACCESS_TOKEN is required for the live Calendar adapter")

    def events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        params = {
            "timeMin": start.isoformat(),
            "timeMax": end.isoformat(),
            "singleEvents": "true",
            "orderBy": "startTime",
        }
        query = urllib.parse.urlencode(params)
        request = urllib.request.Request(
            f"{self.base_url}/{urllib.parse.quote(self.calendar_id, safe='')}/events?{query}",
            headers={"Authorization": f"Bearer {self.access_token}"},
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read())
        return [_calendar_event(item) for item in payload.get("items", []) if _has_datetime(item)]


class SESAdapter:
    def __init__(self, *, region: str | None = None, sender: str | None = None) -> None:
        self.sender = sender or os.getenv("SES_FROM_ADDRESS")
        if not self.sender:
            raise ValueError("SES_FROM_ADDRESS is required for live outbound email")
        self.client = boto3.client(
            "ses",
            region_name=region or os.getenv("AWS_REGION", "us-east-1"),
        )

    def send(self, *, to: str, subject: str, body: str) -> DeliveryResult:
        response = self.client.send_email(
            Source=self.sender,
            Destination={"ToAddresses": [to]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Text": {"Data": body, "Charset": "UTF-8"}},
            },
        )
        return DeliveryResult(
            provider="ses",
            message_id=response["MessageId"],
            status="sent",
        )


def _gmail_body(payload: dict[str, Any]) -> str:
    data = payload.get("body", {}).get("data")
    if data:
        return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
    for part in payload.get("parts", []):
        body = _gmail_body(part)
        if body:
            return body
    return ""


def _has_datetime(item: dict[str, Any]) -> bool:
    return bool(item.get("start", {}).get("dateTime") and item.get("end", {}).get("dateTime"))


def _calendar_event(item: dict[str, Any]) -> CalendarEvent:
    start = datetime.fromisoformat(item["start"]["dateTime"].replace("Z", "+00:00"))
    end = datetime.fromisoformat(item["end"]["dateTime"].replace("Z", "+00:00"))
    return CalendarEvent(
        id=f"cal_google_{item['id']}",
        person_id=item.get("extendedProperties", {}).get("private", {}).get("person_id", "unknown"),
        title=item.get("summary", "Google Calendar event"),
        start=start,
        end=end,
        kind="meeting",
    )


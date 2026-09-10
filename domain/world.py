from __future__ import annotations

from dataclasses import dataclass, field

from domain.models import (
    CalendarEvent,
    Client,
    Commitment,
    CustomerAsset,
    Document,
    EmailMessage,
    Person,
    Project,
    SimulationClock,
    Supplier,
    WorldEvent,
)


@dataclass
class World:
    clock: SimulationClock
    people: list[Person] = field(default_factory=list)
    clients: list[Client] = field(default_factory=list)
    projects: list[Project] = field(default_factory=list)
    suppliers: list[Supplier] = field(default_factory=list)
    emails: list[EmailMessage] = field(default_factory=list)
    documents: list[Document] = field(default_factory=list)
    calendar: list[CalendarEvent] = field(default_factory=list)
    assets: list[CustomerAsset] = field(default_factory=list)
    commitments: list[Commitment] = field(default_factory=list)
    events: list[WorldEvent] = field(default_factory=list)

    def person(self, person_id: str) -> Person:
        return next(p for p in self.people if p.id == person_id)

    def client(self, client_id: str) -> Client:
        return next(c for c in self.clients if c.id == client_id)

    def project(self, project_id: str) -> Project:
        return next(p for p in self.projects if p.id == project_id)

    def supplier(self, supplier_id: str) -> Supplier:
        return next(s for s in self.suppliers if s.id == supplier_id)

    def asset(self, asset_id: str) -> CustomerAsset:
        return next(a for a in self.assets if a.id == asset_id)

    def people_with_skill(self, skill: str) -> list[Person]:
        return [p for p in self.people if skill in p.skills]

    def suppliers_of_kind(self, kind: str) -> list[Supplier]:
        return [s for s in self.suppliers if s.kind == kind]

    def assets_for_client(self, client_id: str) -> list[CustomerAsset]:
        return [a for a in self.assets if a.client_id == client_id]

    def active_projects(self) -> list[Project]:
        return [p for p in self.projects if p.status == "active"]

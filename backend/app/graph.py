"""Scam network: link risky cases that share infrastructure."""

from collections import defaultdict
from itertools import combinations

from .api_models import Case, EdgeType, Graph, GraphEdge, GraphNode, RelatedDomain
from .contracts import Label
from .urls import hostname

# A group bigger than this is probably shared hosting or a CDN, not one campaign.
MAX_GROUP = 25


def build_graph(cases: list[Case]) -> Graph:
    risky = [c for c in cases if c.verdict.verdict != Label.LEGIT]
    nodes = [
        GraphNode(
            id=c.id,
            domain=c.domain,
            verdict=c.verdict.verdict,
            score=c.verdict.score,
            brand_target=c.verdict.brand_target,
        )
        for c in risky
    ]

    groups: dict[tuple[EdgeType, str], list[str]] = defaultdict(list)
    for case in risky:
        ev = case.evidence
        if ev is None:
            continue
        # A parked, for-sale or blocked page belongs to the registrar or marketplace: its IP, final
        # host and fingerprints would link every domain parked there. Registration day still counts.
        placeholder = ev.page_kind not in (None, "content", "empty")
        # On a shared platform the IP and WHOIS belong to the platform, so they
        # would link unrelated sites. Only the final host still says something.
        if ev.ip and not ev.shared_hosting and not placeholder:
            groups[("same_ip", f"Same IP address {ev.ip}")].append(case.id)
        if ev.rdap and ev.rdap.created and ev.rdap.registrar and not ev.shared_hosting:
            day = ev.rdap.created.date().isoformat()
            detail = f"Registered on {day} at {ev.rdap.registrar}"
            groups[("same_registration_day", detail)].append(case.id)
        if ev.final_url and not placeholder:
            groups[("same_final_host", f"Same final host {hostname(ev.final_url)}")].append(
                case.id
            )
        fp = ev.fingerprints
        if fp is None or placeholder:
            continue
        # Fingerprints from Simon's fetcher: the same favicon, page template, tracker account
        # or contact across domains points to one operator (a hypothesis, not proof).
        if fp.favicon_mmh3 is not None:
            groups[("same_favicon", f"Same favicon (Shodan hash {fp.favicon_mmh3})")].append(case.id)
        if fp.dom_hash:
            groups[("same_template", f"Same page template {fp.dom_hash}")].append(case.id)
        for tracker in fp.tracking_ids:
            groups[("same_tracker", f"Same tracking ID {tracker}")].append(case.id)
        for handle in fp.contacts.whatsapp + fp.contacts.telegram:
            groups[("same_contact", f"Same contact {handle}")].append(case.id)

    edges = [
        GraphEdge(source=a, target=b, type=edge_type, detail=detail)
        for (edge_type, detail), ids in groups.items()
        if 2 <= len(ids) <= MAX_GROUP
        for a, b in combinations(sorted(set(ids)), 2)
    ]
    return Graph(nodes=nodes, edges=edges)


def related_domains(case_id: str, cases: list[Case]) -> list[RelatedDomain]:
    """Graph edges that touch one case, seen from that case (the other end of each edge)."""
    by_id = {c.id: c for c in cases}
    related = []
    for edge in build_graph(cases).edges:
        if case_id not in (edge.source, edge.target):
            continue
        other = by_id[edge.target if edge.source == case_id else edge.source]
        related.append(
            RelatedDomain(
                case_id=other.id,
                domain=other.domain,
                verdict=other.verdict.verdict,
                score=other.verdict.score,
                type=edge.type,
                detail=edge.detail,
            )
        )
    return sorted(related, key=lambda r: (-r.score, r.domain, r.type))

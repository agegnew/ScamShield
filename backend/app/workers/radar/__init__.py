"""Radar sources. The runner schedules every enabled source on its interval."""

from .base import RadarSource
from .ct import CertTransparency
from .lookalikes import Lookalikes
from .maps import GoogleMaps
from .nrd import NewDomains
from .search import GoogleSearch

SOURCES: dict[str, RadarSource] = {
    source.name: source
    for source in (Lookalikes(), CertTransparency(), NewDomains(), GoogleSearch(), GoogleMaps())
}

__all__ = ["SOURCES", "RadarSource"]

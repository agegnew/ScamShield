import os
from abc import ABC, abstractmethod

from ...contracts import Brand, Candidate, Source


class RadarSource(ABC):
    """One way of finding new suspicious URLs.

    discover() returns Candidates; the pipeline stores new ones as cases and
    queues a fetch for each. Return only URLs (http/https), never raise for a
    single bad result — skip it.
    """

    name: str
    source: Source
    interval_minutes: int = 15
    required_env: tuple[str, ...] = ()

    def enabled(self) -> bool:
        return all(os.getenv(var) for var in self.required_env)

    @abstractmethod
    def discover(self, brands: list[Brand]) -> list[Candidate]: ...

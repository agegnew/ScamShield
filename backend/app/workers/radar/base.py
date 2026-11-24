import os
from abc import ABC, abstractmethod
from collections.abc import Callable

from ...contracts import Brand, Candidate, Source

# progress(checked, total): total is None while unknown.
Progress = Callable[[int, int | None], None]


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
    # Env var that makes the source live (SerpApi). Radar runs skip the source without it.
    needs_key: str | None = None
    # Set by a radar run while discover() runs, so the Radar page can show progress.
    progress: Progress | None = None

    def enabled(self) -> bool:
        return all(os.getenv(var) for var in self.required_env)

    def has_key(self) -> bool:
        return not self.needs_key or bool(os.getenv(self.needs_key))

    def report(self, checked: int, total: int | None) -> None:
        if self.progress:
            self.progress(checked, total)

    @abstractmethod
    def discover(self, brands: list[Brand]) -> list[Candidate]: ...

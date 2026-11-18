from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Flight:
    flight_id: str
    airline: str
    origin: str
    destination: str
    runway: str
    start: datetime
    end: datetime
    priority: int
    status: str = "SCHEDULED"
    orig_start: datetime = field(init=False)
    orig_end: datetime = field(init=False)

    def __post_init__(self):
        self.orig_start = self.start
        self.orig_end = self.end

    @property
    def duration(self):
        return self.end - self.start
from enum import Enum


class IncidentStatus(Enum):
    Resolved = 0
    Down = 1
    Investigating = 2
    Monitoring = 3
    Maintenance = 4

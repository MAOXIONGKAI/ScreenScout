from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Cinema:
    id: int
    name: str
    branch: str
    postal_code: str
    address: Optional[str]
    created_at: datetime
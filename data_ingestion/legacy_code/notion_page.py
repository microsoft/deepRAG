import json

from dataclasses import dataclass, asdict


@dataclass
class NotionPage:
    id: str
    url: str
    html: str
    title: str
    last_edited_time: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

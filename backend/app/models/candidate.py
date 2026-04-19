from typing import Optional

from pydantic import BaseModel, Field


class Candidate(BaseModel):
    candidate_id: str
    image_url: str
    source_page: str
    source_domain: str
    observed_text: str = ""
    image_quality_score: float = 0.0
    source_trust_score: float = 0.0
    resolved_image_url: Optional[str] = None
    local_image_path: Optional[str] = None
    local_source_path: Optional[str] = None
    downloaded: bool = False
    notes: list[str] = Field(default_factory=list)
    fixture_expected_match: Optional[bool] = None

from typing import Optional

from pydantic import BaseModel, Field

from backend.app.core.constants import AnalyzerMode


class AnalyzeRequest(BaseModel):
    wine_name: str = Field(min_length=1)
    vintage: str = Field(min_length=1)
    format: str = Field(default="750ml", min_length=1)
    region: str = Field(default="", min_length=0)
    analyzer_mode: AnalyzerMode = AnalyzerMode.STRICT


class ParsedIdentity(BaseModel):
    producer: Optional[str] = None
    appellation: Optional[str] = None
    vineyard_or_cuvee: Optional[str] = None
    classification: Optional[str] = None
    vintage: Optional[str] = None
    format: Optional[str] = None
    region: Optional[str] = None
    raw_wine_name: str
    normalized_wine_name: str


class BatchAnalyzeRequest(BaseModel):
    items: list[AnalyzeRequest] = Field(default_factory=list)

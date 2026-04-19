from pydantic import BaseModel, Field


class OcrRequest(BaseModel):
    image_path: str = Field(min_length=1)


class OcrResponse(BaseModel):
    engine: str
    available: bool
    text: str
    snippets: list[str] = Field(default_factory=list)
    boxes: list = Field(default_factory=list)

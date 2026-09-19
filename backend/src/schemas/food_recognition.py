"""Provider-neutral food-recognition contracts."""
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictRecognitionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class NormalizedPoint(StrictRecognitionModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)


class NormalizedBoundingBox(StrictRecognitionModel):
    xmin: float = Field(ge=0, le=1)
    ymin: float = Field(ge=0, le=1)
    xmax: float = Field(ge=0, le=1)
    ymax: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_extents(self):
        if self.xmax <= self.xmin or self.ymax <= self.ymin:
            raise ValueError("bbox maximums must be greater than minimums")
        return self


class FoodRecognition(StrictRecognitionModel):
    """Coordinates are normalized to the original upload dimensions."""

    name: str = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)
    polygons: list[list[NormalizedPoint]] | None = Field(default=None, min_length=1)
    bbox: NormalizedBoundingBox | None = None
    processed_width: int | None = Field(default=None, gt=0)
    processed_height: int | None = Field(default=None, gt=0)
    provider_item_id: str | None = Field(default=None, min_length=1, max_length=100)

    @model_validator(mode="after")
    def require_spatial_result(self):
        if self.polygons is None and self.bbox is None:
            raise ValueError("a polygon or bbox is required")
        return self

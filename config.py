from typing import List, Optional
from datetime import datetime
from zoneinfo import available_timezones
from pydantic import (
    AnyHttpUrl,
    BaseModel,
    Field,
    IPvAnyAddress,
    PositiveInt,
    confloat,
    conint,
    constr,
    validator,
)


class CropConfig(BaseModel):
    left_edge: confloat(ge=0.0, le=1.0)
    right_edge: confloat(ge=0.0, le=1.0)
    top_edge: confloat(ge=0.0, le=1.0)
    bottom_edge: confloat(ge=0.0, le=1.0)


class PdfConfig(BaseModel):
    newspaper: str
    crop: Optional[CropConfig]


class WebConfig(BaseModel):
    host: IPvAnyAddress
    port: PositiveInt

    @validator("port")
    def port_must_be_valid(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError("Port must be in range 1 to 65535")
        return v


class ImageConfig(BaseModel):
    dpi: PositiveInt
    max_width: PositiveInt
    max_height: PositiveInt


class RefreshSchedulerConfig(BaseModel):
    time: str
    timezone: str

    @validator("time")
    def validate_time_format(cls, v):
        try:
            datetime.strptime(v, "%H:%M")
        except ValueError:
            raise ValueError("Time must be in format '%H:%M'")
        return v

    @validator("timezone")
    def validate_timezone(cls, v):
        if v not in available_timezones():
            raise ValueError(
                "Invalid timezone string. Please consult the IANA timezone list for examples."
            )
        return v


class Config(BaseModel):
    pdfs: List[PdfConfig]
    web: WebConfig
    image: ImageConfig
    refresh_scheduler: RefreshSchedulerConfig

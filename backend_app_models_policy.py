from pydantic import BaseModel, Field


class TenantPolicy(BaseModel):
    min_length: int = 8
    max_length: int = 128
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digit: bool = True
    require_symbol: bool = False
    zxcvbn_min: int = Field(default=2, ge=0, le=4)
    hibp_check: bool = True
    custom_blocklist: list[str] = []

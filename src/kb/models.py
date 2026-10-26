from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Category(str, Enum):
    program_info = "program_info"
    icat_test = "icat_test"
    enrolment = "enrolment"
    fees_payments = "fees_payments"
    refunds = "refunds"
    certificates_offer_letter = "certificates_offer_letter"
    placement_hiring = "placement_hiring"
    projects_assignments = "projects_assignments"
    extension = "extension"
    referral_campus = "referral_campus"
    payments_refunds = "payments_refunds"
    certificates = "certificates"
    technical_access = "technical_access"
    trust_verification = "trust_verification"
    placement_support = "placement_support"


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class KBRow(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: str = Field(pattern=r"^CAT-\d{3}$")
    category: Category
    question: str = Field(min_length=3)
    answer: str = Field(min_length=1)
    answer_hinglish: str | None = None
    hinglish_variants: str
    keywords: str
    risk_level: RiskLevel
    handoff_offer: bool
    escalate_if_unmatched: bool
    owner: str = Field(min_length=1)
    last_reviewed: date

    @field_validator("handoff_offer", "escalate_if_unmatched", mode="before")
    @classmethod
    def parse_bool(cls, value: object) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized == "true":
                return True
            if normalized == "false":
                return False
        raise ValueError("must be true or false")


class BuiltEntry(BaseModel):
    id: str
    category: Category
    question: str
    answer_template: str
    answer_rendered: str
    answer_hinglish: str | None = None
    hinglish_variants: list[str]
    keywords: list[str]
    risk_level: RiskLevel
    handoff_offer: bool
    escalate_if_unmatched: bool
    owner: str
    last_reviewed: date
    facts_required: list[str]
    facts_verified: list[str]
    facts_mock: list[str]
    is_mock: bool
    source_status: str = "verified"
    help_link: str = ""

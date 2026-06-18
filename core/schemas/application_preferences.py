"""Application preference schemas (eligibility, logistics, EEO)."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class WorkEligibility(BaseModel):
    """Decision-relevant eligibility answers; must be truthful user-provided values."""

    authorized_to_work: bool | None = None
    requires_sponsorship: bool | None = None
    over_18: bool | None = None
    willing_to_relocate: bool | None = None

    model_config = ConfigDict(extra="forbid")


class LogisticsPreferences(BaseModel):
    """Non-sensitive application logistics."""

    desired_salary: str | None = None
    earliest_start_date: str | None = None
    notice_period: str | None = None
    referral_source: str | None = None

    model_config = ConfigDict(extra="forbid")


class GenderIdentity(StrEnum):
    DECLINE = "decline_to_answer"
    MALE = "male"
    FEMALE = "female"
    NONBINARY = "nonbinary"


class VeteranStatus(StrEnum):
    DECLINE = "decline_to_answer"
    NOT_VETERAN = "not_a_veteran"
    VETERAN = "veteran"


class DisabilityStatus(StrEnum):
    DECLINE = "decline_to_answer"
    NO = "no"
    YES = "yes"


class Demographics(BaseModel):
    """EEO self-identification. Defaults to decline; never inferred by the system."""

    gender: GenderIdentity = GenderIdentity.DECLINE
    race_ethnicity: list[str] = []
    veteran_status: VeteranStatus = VeteranStatus.DECLINE
    disability_status: DisabilityStatus = DisabilityStatus.DECLINE

    model_config = ConfigDict(extra="forbid")


class DemographicConsent(BaseModel):
    """Explicit consent before storing encrypted demographics."""

    consented: bool = False
    consented_at: datetime | None = None

    model_config = ConfigDict(extra="forbid")


class ApplicationPreferences(BaseModel):
    """Plaintext application preferences embedded on Profile."""

    work_eligibility: WorkEligibility = WorkEligibility()
    logistics: LogisticsPreferences = LogisticsPreferences()
    demographic_consent: DemographicConsent = DemographicConsent()

    model_config = ConfigDict(extra="forbid")

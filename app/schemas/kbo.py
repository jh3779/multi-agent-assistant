from pydantic import BaseModel, Field


class KBORequest(BaseModel):
    query: str


class KBOResponse(BaseModel):
    answer: str


class ValidationResult(BaseModel):
    """Validation result for a generated answer."""

    is_valid: bool = Field(
        description="Whether the answer is factually correct and supported."
    )
    reason: str = Field(description="Reason for the validation result.")
    correction: str | None = Field(
        default=None, description="Correction instructions if the answer is invalid."
    )

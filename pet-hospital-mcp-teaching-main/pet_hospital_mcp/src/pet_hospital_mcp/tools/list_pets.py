from __future__ import annotations

import math
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from pet_hospital_mcp.errors import ErrorCode, ToolFailure


Species = Literal["犬", "猫", "兔", "鸟", "仓鼠", "爬宠", "其他"]
Status = Literal["待就诊", "就诊中", "住院中", "已康复", "慢性病随访"]
SortBy = Literal[
    "id",
    "name",
    "ownerName",
    "species",
    "doctor",
    "disease",
    "status",
    "totalCost",
    "visitCount",
    "createdAt",
    "updatedAt",
]
Order = Literal["asc", "desc"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class ListPetsInput(StrictModel):
    """Input accepted by the list_pets MCP tool."""

    q: str | None = Field(default=None, description="Full-text search keyword across pet, owner and medical fields.")
    name: str | None = Field(default=None, description="Filter by pet name substring.")
    ownerName: str | None = Field(default=None, description="Filter by owner name substring.")
    ownerPhone: str | None = Field(default=None, description="Filter by owner phone substring.")
    species: Species | None = Field(default=None, description="Exact species filter.")
    doctor: str | None = Field(default=None, description="Filter by doctor name substring.")
    disease: str | None = Field(default=None, description="Filter by disease/diagnosis substring.")
    status: Status | None = Field(default=None, description="Exact visit status filter.")
    min: float | None = Field(default=None, ge=0, description="Minimum total cost.")
    max: float | None = Field(default=None, ge=0, description="Maximum total cost.")
    sortBy: SortBy | None = Field(default=None, description="Backend sort field.")
    order: Order | None = Field(default=None, description="Sort order: asc or desc.")
    page: int = Field(default=1, ge=1, description="Page number, starting at 1.")
    pageSize: int = Field(default=20, ge=1, le=500, description="Page size, from 1 to 500.")

    @field_validator("q", "name", "ownerName", "ownerPhone", "doctor", "disease", mode="before")
    @classmethod
    def validate_optional_string(cls, value: Any) -> Any:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("must be a string")
        return value

    @field_validator("page", "pageSize", mode="before")
    @classmethod
    def validate_integer(cls, value: Any) -> Any:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("must be an integer")
        return value

    @field_validator("min", "max", mode="before")
    @classmethod
    def validate_finite_number(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError("must be a number")
        if not math.isfinite(float(value)):
            raise ValueError("must be finite")
        return float(value)

    @model_validator(mode="after")
    def validate_range(self) -> "ListPetsInput":
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("min must be less than or equal to max")
        return self

    def query_params(self) -> dict[str, str]:
        data = self.model_dump(exclude_none=True)
        return {key: str(value) for key, value in data.items()}


class MedicalRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    visitDate: str
    doctor: str
    diagnosis: str
    symptoms: str | None = None
    treatment: str | None = None
    prescription: list[str] | None = None
    weightKg: float | None = None
    temperature: float | None = None
    followUp: str | None = None
    charge: float
    createdAt: str


class Treatment(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    item: str
    category: str
    amount: float
    doctor: str | None = None
    date: str
    note: str | None = None


class Pet(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    species: str
    breed: str | None = None
    gender: str | None = None
    ageMonths: int | None = None
    color: str | None = None
    chipNo: str | None = None
    ownerName: str
    ownerPhone: str
    ownerAddr: str | None = None
    doctor: str
    disease: str
    status: str
    allergy: str | None = None
    note: str | None = None
    records: list[MedicalRecord] | None = None
    charges: list[Treatment] | None = None
    totalCost: float
    visitCount: int
    createdAt: str
    updatedAt: str


class ListPetsOutput(StrictModel):
    """Successful output matching Go GET /api/v1/pets response data."""

    items: list[Pet]
    total: int
    page: int
    pageSize: int
    totalPages: int
    totalCost: float


def parse_list_pets_input(arguments: dict[str, Any] | None) -> ListPetsInput:
    try:
        return ListPetsInput.model_validate(arguments or {})
    except ValidationError as exc:
        fields = []
        for err in exc.errors(include_url=False):
            loc = ".".join(str(part) for part in err.get("loc", ())) or "input"
            fields.append({"field": loc, "message": err.get("msg", "invalid value")})
        raise ToolFailure(
            ErrorCode.VALIDATION_ERROR,
            "Invalid list_pets input.",
            {"fields": fields},
        ) from exc


LIST_PETS_DESCRIPTION = """
List pet hospital records from the existing Go REST API.

Use this tool when an agent needs to inspect, search, filter, sort, or paginate pet records.
It forwards exactly these query parameters to GET /api/v1/pets: q, name, ownerName,
ownerPhone, species, doctor, disease, status, min, max, sortBy, order, page, pageSize.
It returns the Go API data object: items, total, page, pageSize, totalPages, and totalCost.
records and charges in each item may be null or arrays, matching the backend JSON.
""".strip()


async def registered_list_pets(
    q: str | None = None,
    name: str | None = None,
    ownerName: str | None = None,
    ownerPhone: str | None = None,
    species: Species | None = None,
    doctor: str | None = None,
    disease: str | None = None,
    status: Status | None = None,
    min: float | None = None,
    max: float | None = None,
    sortBy: SortBy | None = None,
    order: Order | None = None,
    page: int = 1,
    pageSize: int = 20,
) -> Annotated[ListPetsOutput, Field(description="Go GET /api/v1/pets data object.")]:
    """Schema-only registration target; server.py overrides runtime execution."""
    raise RuntimeError("list_pets is executed by PetHospitalMCPServer._handle_call_tool")

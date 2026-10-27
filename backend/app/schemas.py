"""Request and response shapes, with validation."""

from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from .security import MAX_PASSWORD_BYTES

Priority = Literal["low", "medium", "high"]
Status = Literal["pending", "in_progress", "completed"]

# The task form offers Normal / High / Low; the database stores low / medium / high.
_PRIORITY_ALIASES = {"low": "low", "normal": "medium", "medium": "medium", "high": "high"}


def _as_utc(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


# --------------------------------------------------------------------------- auth


class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=6)

    @field_validator("name")
    @classmethod
    def _clean_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty.")
        return v

    @field_validator("email")
    @classmethod
    def _lower_email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("password")
    @classmethod
    def _password_size(cls, v: str) -> str:
        if len(v.encode("utf-8")) > MAX_PASSWORD_BYTES:
            raise ValueError(f"Password must be at most {MAX_PASSWORD_BYTES} bytes long.")
        return v


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)

    @field_validator("email")
    @classmethod
    def _lower_email(cls, v: str) -> str:
        return v.strip().lower()


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def _utc(cls, v: datetime) -> datetime:
        return _as_utc(v)


class TokenOut(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserOut


# --------------------------------------------------------------------------- tasks


class _TaskFields(BaseModel):
    """Validation shared by create and update."""

    @field_validator("title", check_fields=False)
    @classmethod
    def _clean_title(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Task name cannot be empty.")
        return v

    @field_validator("priority", mode="before", check_fields=False)
    @classmethod
    def _priority_alias(cls, v):
        if isinstance(v, str):
            return _PRIORITY_ALIASES.get(v.strip().lower(), v)
        return v

    @field_validator("category", check_fields=False)
    @classmethod
    def _clean_category(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return v.strip() or "Other"

    @field_validator("due_date", mode="before", check_fields=False)
    @classmethod
    def _parse_due_date(cls, v):
        # The date input sends "YYYY-MM-DD", or "" when left blank.
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return None
            try:
                return datetime.combine(date.fromisoformat(v), datetime.min.time(), timezone.utc)
            except ValueError:
                return v  # let pydantic try it as a full datetime
        if isinstance(v, date) and not isinstance(v, datetime):
            return datetime.combine(v, datetime.min.time(), timezone.utc)
        return v

    @field_validator("due_date", check_fields=False)
    @classmethod
    def _due_utc(cls, v: datetime | None) -> datetime | None:
        return _as_utc(v)


class TaskCreate(_TaskFields):
    title: str = Field(max_length=200)
    description: str = Field(default="", max_length=10_000)
    priority: Priority = "medium"
    status: Status = "pending"
    category: str = Field(default="Other", max_length=50)
    due_date: datetime | None = None


class TaskUpdate(_TaskFields):
    """Partial update: only the fields that are sent are changed."""

    title: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=10_000)
    priority: Priority | None = None
    status: Status | None = None
    category: str | None = Field(default=None, max_length=50)
    due_date: datetime | None = None  # send null (or "") to clear the due date

    @model_validator(mode="after")
    def _no_nulls_on_required_fields(self):
        for name in ("title", "description", "priority", "status", "category"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null.")
        return self


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    priority: Priority
    status: Status
    category: str
    due_date: datetime | None
    created_at: datetime
    updated_at: datetime

    @field_validator("due_date", "created_at", "updated_at")
    @classmethod
    def _utc(cls, v):
        return _as_utc(v)


class TaskStats(BaseModel):
    total: int
    pending: int  # everything not completed, matching the "To Do" counter in the UI
    in_progress: int
    completed: int
    overdue: int


class ReorderIn(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=5000)

    @field_validator("ids")
    @classmethod
    def _unique(cls, v: list[int]) -> list[int]:
        if len(set(v)) != len(v):
            raise ValueError("ids must not contain duplicates.")
        return v


# --------------------------------------------------------------------------- contact


class ContactIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    subject: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=5000)

    @field_validator("name", "subject", "message")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("This field cannot be empty.")
        return v


class ContactOut(BaseModel):
    detail: str = "Thanks! Your message has been received."

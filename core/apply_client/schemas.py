"""Pydantic models for the browser apply agent."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class BrowserAction(BaseModel):
    """One browser action the agent wants to perform."""

    action: Literal[
        "fill", "click", "select", "upload", "wait", "done", "fail", "need_human"
    ]
    selector: str | None = None
    value: str | None = None
    reason: str = ""

    model_config = ConfigDict(extra="forbid")


class AgentStepResponse(BaseModel):
    """Structured LLM response for one agent iteration."""

    thought: str
    actions: list[BrowserAction] = Field(default_factory=list)
    submit_ready: bool = False

    model_config = ConfigDict(extra="forbid")


class FormFieldSnapshot(BaseModel):
    index: int
    tag: str
    input_type: str | None = None
    name: str | None = None
    field_id: str | None = None
    label: str | None = None
    placeholder: str | None = None
    value: str | None = None
    required: bool = False
    selector: str

    model_config = ConfigDict(extra="forbid")


class PageSnapshot(BaseModel):
    url: str
    title: str
    fields: list[FormFieldSnapshot]

    model_config = ConfigDict(extra="forbid")

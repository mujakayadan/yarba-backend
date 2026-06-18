"""Tests for auth autofill submit selection."""

from core.apply_client.auth_autofill import pick_auth_submit_field, resolve_auth_mode
from core.apply_client.schemas import FormFieldSnapshot, PageSnapshot


def _button(**kwargs: object) -> FormFieldSnapshot:
    defaults = {
        "index": 0,
        "tag": "button",
        "input_type": "button",
        "name": None,
        "field_id": None,
        "label": None,
        "placeholder": None,
        "value": None,
        "required": False,
        "selector": "#btn",
    }
    defaults.update(kwargs)
    return FormFieldSnapshot.model_validate(defaults)


def test_resolve_auth_mode_create_when_verify_password_visible() -> None:
    snapshot = PageSnapshot(
        url="https://workday.example/apply",
        title="Create Account",
        fields=[
            FormFieldSnapshot.model_validate(
                {
                    "index": 0,
                    "tag": "input",
                    "input_type": "password",
                    "name": None,
                    "field_id": None,
                    "label": "Verify New Password",
                    "placeholder": None,
                    "value": "secret",
                    "required": True,
                    "selector": '[data-automation-id="verifyPassword"]',
                }
            ),
        ],
    )
    assert resolve_auth_mode(snapshot, prefer_sign_in=False) == "create"


def test_pick_auth_submit_create_mode_ignores_sign_in_button() -> None:
    snapshot = PageSnapshot(
        url="https://workday.example/apply",
        title="Create Account",
        fields=[
            FormFieldSnapshot.model_validate(
                {
                    "index": 0,
                    "tag": "input",
                    "input_type": "password",
                    "name": None,
                    "field_id": None,
                    "label": "Verify New Password",
                    "placeholder": None,
                    "value": "secret",
                    "required": True,
                    "selector": '[data-automation-id="verifyPassword"]',
                }
            ),
            _button(
                label="Sign In",
                selector='[data-automation-id="signInSubmitButton"]',
            ),
            _button(
                label="Create Account",
                selector='[data-automation-id="createAccountSubmitButton"]',
            ),
        ],
    )
    picked = pick_auth_submit_field(snapshot, auth_mode="create")
    assert picked is not None
    assert "createAccountSubmitButton" in picked.selector


def test_pick_auth_submit_sign_in_mode_ignores_create_account_button() -> None:
    snapshot = PageSnapshot(
        url="https://workday.example/apply",
        title="Sign In",
        fields=[
            _button(
                label="Create Account",
                selector='[data-automation-id="createAccountSubmitButton"]',
            ),
            _button(
                label="Sign In",
                selector='[data-automation-id="signInSubmitButton"]',
            ),
        ],
    )
    picked = pick_auth_submit_field(snapshot, auth_mode="sign_in")
    assert picked is not None
    assert "signInSubmitButton" in picked.selector

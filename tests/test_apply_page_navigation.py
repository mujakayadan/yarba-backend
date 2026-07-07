"""Tests for apply page navigation helpers."""

from core.apply_client.page_navigation import (
    auth_indicates_existing_account,
    auth_submit_progressed,
    can_finish_application,
    count_action_buttons,
    count_interactive_fields,
    is_auth_form_ready,
    is_create_account_form,
    is_email_verification_page,
    is_likely_login_form,
)
from core.apply_client.schemas import FormFieldSnapshot, PageSnapshot


def _field(**kwargs: object) -> FormFieldSnapshot:
    defaults = {
        "index": 0,
        "tag": "input",
        "input_type": "text",
        "name": None,
        "field_id": None,
        "label": None,
        "placeholder": None,
        "value": None,
        "required": False,
        "selector": "#x",
    }
    defaults.update(kwargs)
    return FormFieldSnapshot.model_validate(defaults)


def test_count_interactive_fields_skips_buttons_and_hidden() -> None:
    snapshot = PageSnapshot(
        url="https://example.com",
        title="Apply",
        fields=[
            _field(tag="button", input_type="button", selector="#apply"),
            _field(input_type="hidden", selector="#hidden"),
            _field(input_type="email", selector="#email"),
            _field(tag="textarea", input_type=None, selector="#summary"),
        ],
    )
    assert count_interactive_fields(snapshot) == 2
    assert count_action_buttons(snapshot) == 1


def test_is_likely_login_form_detects_password_field() -> None:
    snapshot = PageSnapshot(
        url="https://example.com",
        title="Sign in",
        fields=[
            _field(input_type="email", label="Email", selector="#email"),
            _field(input_type="password", label="Password", selector="#pw"),
        ],
    )
    assert is_likely_login_form(snapshot) is True


def test_can_finish_application_rejects_auth_pages() -> None:
    auth = PageSnapshot(
        url="https://example.com",
        title="Create Account",
        fields=[
            _field(input_type="email", label="Email", selector="#email"),
            _field(input_type="password", label="Password", selector="#pw"),
        ],
    )
    assert can_finish_application(auth) is False

    application = PageSnapshot(
        url="https://example.com",
        title="Apply",
        fields=[_field(selector=f"#f{i}") for i in range(6)],
    )
    assert can_finish_application(application) is True


def test_is_create_account_form_detects_verify_password() -> None:
    snapshot = PageSnapshot(
        url="https://example.com",
        title="Create Account",
        fields=[
            _field(input_type="email", label="Email", selector="#email"),
            _field(input_type="password", label="Password", selector="#pw"),
            _field(
                input_type="password",
                label="Verify New Password",
                selector="#verify",
            ),
        ],
    )
    assert is_create_account_form(snapshot) is True


def test_is_auth_form_ready_requires_filled_password_fields() -> None:
    incomplete = PageSnapshot(
        url="https://example.com",
        title="Create Account",
        fields=[
            _field(
                input_type="email", label="Email", value="a@b.com", selector="#email"
            ),
            _field(
                input_type="password", label="Password", value="secret", selector="#pw"
            ),
            _field(
                input_type="password",
                label="Verify New Password",
                value="",
                selector="#verify",
            ),
        ],
    )
    assert is_auth_form_ready(incomplete, email="a@b.com", password="secret") is False

    complete = PageSnapshot(
        url="https://example.com",
        title="Create Account",
        fields=[
            _field(
                input_type="email", label="Email", value="a@b.com", selector="#email"
            ),
            _field(
                input_type="password", label="Password", value="secret", selector="#pw"
            ),
            _field(
                input_type="password",
                label="Verify New Password",
                value="secret",
                selector="#verify",
            ),
        ],
    )
    assert is_auth_form_ready(complete, email="a@b.com", password="secret") is True


def test_auth_submit_progressed_when_verification_page_appears() -> None:
    before = PageSnapshot(
        url="https://example.com/apply",
        title="Create Account",
        fields=[
            _field(
                input_type="email", label="Email", value="a@b.com", selector="#email"
            ),
        ],
    )
    after = PageSnapshot(
        url="https://example.com/apply",
        title="Verify your email",
        fields=[
            _field(
                label="Enter the verification code sent to your email", selector="#code"
            ),
        ],
    )
    assert is_email_verification_page(after) is True
    assert auth_submit_progressed(before, after) is True


def test_auth_submit_not_progressed_when_still_on_login_form() -> None:
    before = PageSnapshot(
        url="https://example.com/apply",
        title="Create Account",
        fields=[
            _field(
                input_type="email", label="Email", value="a@b.com", selector="#email"
            ),
        ],
    )
    after = PageSnapshot(
        url="https://example.com/apply",
        title="Sign In",
        fields=[
            _field(
                input_type="email", label="Email", value="a@b.com", selector="#email"
            ),
            _field(input_type="password", label="Password", value="", selector="#pw"),
        ],
    )
    assert is_likely_login_form(after) is True
    assert auth_submit_progressed(before, after) is False


def test_auth_indicates_existing_account() -> None:
    snapshot = PageSnapshot(
        url="https://example.com/apply",
        title="Create Account",
        fields=[
            _field(
                label="An account with this email already exists. Please sign in.",
                selector="#error",
            ),
        ],
    )
    assert auth_indicates_existing_account(snapshot) is True

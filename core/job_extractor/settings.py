from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class ExtractorSettings(BaseSettings):
    # General timeouts
    navigation_timeout_ms: int = 30000  # Initial page navigation
    network_idle_timeout_ms: int = 4000  # Wait for network to be idle (reduced)
    element_timeout_ms: int = 5000  # General element visibility/interaction

    # LinkedIn specific settings
    li_show_more_attempts: int = 2  # Reduced from 3
    li_show_more_click_timeout_ms: int = 3000  # Timeout for the click itself (reduced)
    li_show_more_post_click_wait_ms: int = (
        1000  # Wait after click for content to load (reduced)
    )

    # Modal handling
    modal_check_timeout_ms: int = (
        1000  # Short timeout for checking if a modal is visible
    )
    modal_dismiss_timeout_ms: int = 2000  # Timeout for clicking a dismiss button

    # Cookie consent selectors (can be expanded)
    cookie_consent_selectors: List[str] = [
        "button[data-tracking-control-name='ga-cookie.consent.accept.v3']",
        "button#onetrust-accept-btn-handler",
        "button[aria-label*='accept' i], button[aria-label*='Accept' i]",
        "button:text-matches('Accept all', 'i')",
        "button:text-matches('Accept', 'i')",
    ]

    # LinkedIn sign-in modal dismiss button selectors
    li_signin_dismiss_selectors: List[str] = [
        "#base-contextual-sign-in-modal > div > section > button",
        "button.modal__dismiss.contextual-sign-in-modal__modal-dismiss",
        "button[aria-label='Dismiss'][data-tracking-control-name='public_jobs_contextual-sign-in-modal_modal_dismiss']",
        "button[data-tracking-control-name='public_jobs_contextual-sign-in-modal_modal_dismiss']",
    ]
    li_signin_modal_overlay_selector: str = "div.modal__overlay"

    # If you have a .env file, settings can be overridden from there
    # model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')
    model_config = SettingsConfigDict(
        extra="ignore"
    )  # extra='ignore' allows defining other vars in .env


# Instantiate the settings so they can be imported
settings = ExtractorSettings()

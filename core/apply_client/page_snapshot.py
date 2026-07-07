"""Capture visible form controls from the current page."""

from __future__ import annotations

import json
from typing import Any

from playwright.async_api import Page

from core.apply_client.schemas import FormFieldSnapshot, PageSnapshot

FIELD_SNAPSHOT_SCRIPT = """
() => {
  const visible = (el) => {
    const style = window.getComputedStyle(el);
    if (style.display === "none" || style.visibility === "hidden") return false;
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  };

  const labelFor = (el) => {
    const labelledBy = el.getAttribute("aria-labelledby");
    if (labelledBy) {
      const text = labelledBy
        .split(/\\s+/)
        .map((id) => document.getElementById(id)?.innerText?.trim())
        .filter(Boolean)
        .join(" ");
      if (text) return text;
    }
    if (el.id) {
      const byFor = document.querySelector(`label[for="${el.id}"]`);
      if (byFor) return byFor.innerText.trim();
    }
    const wrapped = el.closest("label");
    if (wrapped) return wrapped.innerText.trim();
    const aria = el.getAttribute("aria-label");
    if (aria) return aria.trim();
    const parentLabel = el.closest("[data-automation-id]")?.querySelector("label");
    if (parentLabel) return parentLabel.innerText.trim();
    return "";
  };

  const buttonText = (el) => {
    const text = (el.innerText || el.textContent || "").replace(/\\s+/g, " ").trim();
    return text.slice(0, 120) || null;
  };

  const selectorFor = (el, index) => {
    const automationId = el.getAttribute("data-automation-id");
    if (automationId) {
      const escaped = automationId.replace(/"/g, '\\"');
      const attrSel = `[data-automation-id="${escaped}"]`;
      const matches = document.querySelectorAll(attrSel);
      if (matches.length === 1) return attrSel;
      const nth = Array.from(matches).indexOf(el);
      return `${attrSel} >> nth=${nth}`;
    }
    const testId = el.getAttribute("data-testid");
    if (testId) {
      const escaped = testId.replace(/"/g, '\\"');
      const attrSel = `[data-testid="${escaped}"]`;
      const matches = document.querySelectorAll(attrSel);
      if (matches.length === 1) return attrSel;
      const nth = Array.from(matches).indexOf(el);
      return `${attrSel} >> nth=${nth}`;
    }
    const tracking = el.getAttribute("data-tracking-control-name");
    if (tracking) {
      return `[data-tracking-control-name="${tracking.replace(/"/g, '\\"')}"]`;
    }
    if (el.id) return `#${CSS.escape(el.id)}`;
    if (el.name) {
      return `${el.tagName.toLowerCase()}[name="${el.name.replace(/"/g, '\\"')}"]`;
    }
    el.setAttribute("data-yarba-snap", String(index));
    return `[data-yarba-snap="${index}"]`;
  };

  const fields = [];
  const seen = new Set();
  const elements = document.querySelectorAll(
    "input, textarea, select, button, a, [role='button'], [role='link']"
  );
  elements.forEach((el, index) => {
    if (!visible(el)) return;
    if (el.getAttribute("aria-hidden") === "true") return;
    if (el.getAttribute("tabindex") === "-2") return;
    const tag = el.tagName.toLowerCase();
    const type = el.getAttribute("type") || "";
    if (tag === "input" && type === "hidden") return;
    const label = labelFor(el) || buttonText(el);
    if (tag === "a" && !label) return;
    const selector = selectorFor(el, index);
    if (seen.has(selector)) return;
    seen.add(selector);
    fields.push({
      index,
      tag,
      input_type: type || null,
      name: el.getAttribute("name"),
      field_id: el.id || null,
      label,
      placeholder: el.getAttribute("placeholder"),
      value: el.value || null,
      required: Boolean(el.required),
      selector,
    });
  });

  return {
    url: location.href,
    title: document.title,
    fields,
  };
}
"""


async def snapshot_page(page: Page) -> PageSnapshot:
    merged_fields: list[dict[str, Any]] = []
    seen_selectors: set[str] = set()
    url = page.url
    title = await page.title()

    for frame in page.frames:
        try:
            raw: dict[str, Any] = await frame.evaluate(FIELD_SNAPSHOT_SCRIPT)
        except Exception:
            continue
        if frame.url and frame.url != "about:blank":
            url = frame.url
        for item in raw.get("fields", []):
            selector = item.get("selector")
            if not selector or selector in seen_selectors:
                continue
            seen_selectors.add(selector)
            merged_fields.append(item)

    fields = [FormFieldSnapshot.model_validate(item) for item in merged_fields]
    return PageSnapshot(url=url, title=title, fields=fields)


def profile_payload_for_prompt(profile: dict[str, Any]) -> str:
    """Serialize autofill data for the LLM prompt."""
    return json.dumps(profile, indent=2, default=str)


def snapshot_signature(
    snapshot: PageSnapshot,
) -> tuple[str, tuple[tuple[str, str | None], ...]]:
    """Fingerprint page state to detect agent stalls."""
    inputs = tuple(
        (field.selector, field.value)
        for field in snapshot.fields
        if field.tag in {"input", "textarea", "select"}
    )
    return snapshot.url, inputs

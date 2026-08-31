"""Shared presentation for YARBA transactional emails."""

from html import escape

BRAND_PRIMARY = "#3F72AF"
BRAND_DARK = "#112D4E"
PAGE_BACKGROUND = "#F7FAFC"
TEXT_PRIMARY = "#2D3748"
TEXT_SECONDARY = "#718096"
YARBA_URL = "https://yarba.app"


def append_email_footer(text: str) -> str:
    """Add the plain-text footer shared by all outbound emails."""
    return (
        f"{text.rstrip()}\n\n"
        "—\n"
        "YARBA | Your career, tailored.\n"
        f"{YARBA_URL}\n"
        "This service email was sent because of activity on your YARBA account "
        "or an email you sent to YARBA."
    )


def plaintext_to_html(text: str) -> str:
    """Convert plain text into safe HTML paragraphs."""
    paragraphs = [
        escape(paragraph).replace("\n", "<br>")
        for paragraph in text.strip().split("\n\n")
        if paragraph.strip()
    ]
    return "".join(f"<p>{paragraph}</p>" for paragraph in paragraphs)


def render_email_html(*, subject: str, content_html: str) -> str:
    """Wrap email content in the shared YARBA card and footer."""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(subject)}</title>
</head>
<body style="margin:0;background:{PAGE_BACKGROUND};color:{TEXT_PRIMARY};font-family:Arial,sans-serif;">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;">{escape(subject)}</div>
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:{PAGE_BACKGROUND};padding:32px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:600px;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 18px rgba(17,45,78,0.10);">
          <tr>
            <td style="padding:24px 32px;background:{BRAND_DARK};">
              <a href="{YARBA_URL}" style="color:#ffffff;font-size:24px;font-weight:700;letter-spacing:1px;text-decoration:none;">YARBA</a>
            </td>
          </tr>
          <tr>
            <td style="padding:32px;font-size:16px;line-height:1.6;">
              {content_html}
            </td>
          </tr>
          <tr>
            <td style="padding:22px 32px;background:{PAGE_BACKGROUND};color:{TEXT_SECONDARY};font-size:12px;line-height:1.6;text-align:center;">
              <strong style="color:{TEXT_PRIMARY};">YARBA</strong> &nbsp;|&nbsp; Your career, tailored.<br>
              <a href="{YARBA_URL}" style="color:{BRAND_PRIMARY};text-decoration:none;">yarba.app</a><br>
              This service email was sent because of activity on your YARBA account or an email you sent to YARBA.
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def render_action_button(*, label: str, url: str) -> str:
    """Render an email-safe primary action button."""
    safe_url = escape(url, quote=True)
    return (
        '<p style="margin:28px 0;">'
        f'<a href="{safe_url}" '
        f'style="display:inline-block;background:{BRAND_PRIMARY};color:#ffffff;'
        'font-weight:700;text-decoration:none;padding:12px 22px;border-radius:8px;">'
        f"{escape(label)}</a></p>"
    )

"""Approved Yarba legal-document seed content."""

LEGAL_VERSION = "2026-08-19"

APPROVED_LEGAL_DOCUMENTS: dict[str, tuple[str, str]] = {
    "terms": (
        "Terms of Service",
        """Yarba Terms of Service

These terms govern Yarba accounts, APIs, AI-assisted career tools, application
automation, document services, and public portfolio hosting. Users must be at
least 13. Users aged 13 through 17 may use all features, subject to any consent
required by applicable law. Users retain their content and grant Yarba the
limited rights needed to operate the service. AI output must be reviewed and
does not guarantee employment or accuracy. Public portfolio content may be
indexed and copied. Illegal and sexually explicit content are prohibited.
Yarba may review, restrict, suspend, or remove content to enforce its policies.
The service is provided as available, subject to rights that cannot lawfully be
excluded. Applicable mandatory law and any forum with lawful jurisdiction
govern disputes. Contact admin@yarba.app.""",
    ),
    "privacy": (
        "Privacy Policy",
        """Yarba Privacy Policy

Yarba operates the account, document, application, public-site, visitor-chat,
reporting, and support services. Yarba processes account, profile, professional,
document, application, public-site, visitor, technical, security, and rights-
request information to provide and secure those services, comply with law, and
respond to requests. Requested AI features may send necessary context to
configured providers through LiteLLM. Public portfolio information is public.
Stored visitor chats are retained for 90 days; export archives for up to 7
days; closed moderation records generally for 3 years; and security records
generally for 12 months, subject to legal holds and operational needs. Users
may access, correct, export, or delete information. The service is not for
children under 13. Contact admin@yarba.app.""",
    ),
    "acceptable_use": (
        "Acceptable Use Policy",
        """Yarba Acceptable Use Policy

This policy applies to accounts, uploads, generated output, automation, public
sites, chat, APIs, and infrastructure. Prohibited uses include illegal activity;
sexually explicit content; sexual content involving minors; exploitation;
non-consensual intimate imagery; threats, harassment, and doxxing; fraud,
impersonation, fabricated credentials, phishing, spam, malware, credential
theft, safeguards evasion, infringement, and unauthorized personal-data use.
Users must review AI output and must not automate legally significant answers.
Yarba may reject processing, place content under review, suspend publication,
preserve evidence, revoke tokens, or terminate accounts. Reports may be made
through Yarba's public reporting form or admin@yarba.app.""",
    ),
    "copyright_dmca": (
        "Copyright and Takedown Policy",
        """Yarba Copyright and Takedown Policy

Users must have permission to publish protected material. A copyright notice
must identify the work and exact Yarba location, provide contact information,
good-faith and accuracy statements, authority, and a signature. A counter-
notice must identify removed material and provide the statements and consent
required by applicable law. Yarba may restore content after any required
waiting period and maintains a repeat-infringer policy. Send notices to
admin@yarba.app. Yarba's designated-agent registration remains an external
operator obligation where required.""",
    ),
    "ai_data_use": (
        "AI Data Use Notice",
        """Yarba AI Data Use Notice

Generation, parsing, tailoring, public chat, and safety classification may send
the prompt and relevant profile, portfolio, document, job, or chat context to
service-configured AI providers through LiteLLM. Yarba does not train its own
general-purpose foundation model on private documents. Provider retention and
model-improvement practices depend on provider arrangements. Do not submit
passwords, tokens, unnecessary identifiers, or data you lack authority to use.
AI output is a draft and safety systems may reject content or place publication
under review. Contact admin@yarba.app.""",
    ),
    "site_visitor_privacy": (
        "Public Site Visitor Privacy Notice",
        """Yarba Public Site Visitor Privacy Notice

Portfolio owners select public professional information and Yarba hosts the
site, chat, security, and reporting infrastructure. Chat messages and limited
context may be sent to an AI provider. If storage is enabled, chat messages,
conversation identifiers, user agent, referrer, and scheduling signals may be
retained for 90 days and shown to the portfolio owner. Yarba may process IP
addresses and request metadata for security, rate limiting, and abuse review.
Visitors may avoid interactive features or contact admin@yarba.app.""",
    ),
}

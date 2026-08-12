"""Website generator service for creating static portfolio websites."""

import json
import os
from io import BytesIO
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from PIL import Image, ImageDraw, ImageFont

from config.logging_config import get_logger
from config.settings import Settings
from utils.storage import get_storage_provider

from ..models.portfolio import Portfolio, sort_work_experience
from ..models.portfolio_website import WebsiteConfig
from ..models.profile import Profile
from ..models.user import User


class WebsiteGeneratorService:
    """Service for generating static website files from portfolio data."""

    def __init__(self):
        """Initialize the website generator service."""
        self.logger = get_logger(self.__class__.__name__)
        self.settings = Settings()
        self.templates_dir = Path("templates/websites")
        self._ensure_templates_dir()

        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def _ensure_templates_dir(self):
        """Ensure the templates directory exists."""
        self.templates_dir.mkdir(parents=True, exist_ok=True)

    async def generate_website(
        self,
        portfolio: Portfolio,
        subdomain: str,
        user: User | None = None,
        profile: Profile | None = None,
        config: WebsiteConfig | None = None,
    ) -> dict[str, Any]:
        """Generate website files from portfolio data.

        Args:
            portfolio: Portfolio data
            subdomain: The subdomain for the website (used for generating full URLs)
            user: User data (optional)
            profile: Profile data (optional)
            config: Website configuration (optional)

        Returns:
            Dict[str, str]: Dictionary mapping file paths to file content
        """
        if not config:
            config = WebsiteConfig()

        # Prepare context data
        context = self._prepare_context(portfolio, subdomain, user, profile, config)

        # Generate files
        files: dict[str, Any] = {}

        # Generate HTML files
        files.update(await self._generate_html_files(context, config))

        # Generate CSS files
        files.update(await self._generate_css_files(context, config))

        # Generate JavaScript files
        files.update(await self._generate_js_files(context, config))

        # Generate manifest and other metadata files
        files.update(await self._generate_metadata_files(context, config))

        # Copy all static assets from the theme directory (excluding processed templates)
        files.update(await self._copy_theme_assets(config))

        files.update(await self._generate_favicon_files(profile, config))

        if config.chatbot_enabled:
            files.update(self._copy_chatbot_assets())

        self.logger.info(f"Generated {len(files)} files for portfolio website")
        return files

    def _prepare_context(
        self,
        portfolio: Portfolio,
        subdomain: str,
        user: User | None,
        profile: Profile | None,
        config: WebsiteConfig,
    ) -> dict[str, Any]:
        """Prepare template context from portfolio data.

        Args:
            portfolio: Portfolio data
            subdomain: The subdomain for the website
            user: User data
            profile: Profile data
            config: Website configuration

        Returns:
            Dict: Template context
        """
        # Extract basic info
        personal_info = None
        if profile and profile.personal_information:
            profile_picture_url = None
            if profile.profile_picture_key:
                if self.settings.storage.cloudfront_domain:
                    profile_picture_url = f"https://{self.settings.storage.cloudfront_domain}/{profile.profile_picture_key}"
                else:
                    # Fallback or alternative logic if CloudFront is not configured
                    profile_picture_url = profile.profile_picture_key

            personal_info = {
                "full_name": profile.personal_information.full_name,
                "email": profile.personal_information.email,
                "phone": profile.personal_information.phone,
                "address": profile.personal_information.address,
                "linkedin": profile.personal_information.linkedin,
                "github": profile.personal_information.github,
                "website": profile.personal_information.website,
                "profile_picture_key": profile_picture_url,
            }

        # Prepare sections based on enabled sections
        sections: dict[str, Any] = {}

        if "about" in config.enabled_sections:
            sections["about"] = {
                "career_summary": (
                    portfolio.career_summary.default_summary
                    if portfolio.career_summary
                    else ""
                ),
                "job_title": (
                    portfolio.career_summary.default_job_title
                    if portfolio.career_summary
                    else "Professional"
                ),
                "job_titles": (
                    portfolio.career_summary.job_titles
                    if portfolio.career_summary
                    else []
                ),
                "years_experience": (
                    portfolio.career_summary.years_of_experience
                    if portfolio.career_summary
                    else ""
                ),
            }

        if "experience" in config.enabled_sections:
            sections["experience"] = [
                {
                    "job_title": exp.job_title,
                    "company": exp.company,
                    "location": exp.location,
                    "time": exp.time,
                    "start_date": exp.start_date,
                    "end_date": exp.end_date,
                    "current": exp.current,
                    "responsibilities": exp.responsibilities,
                }
                for exp in sort_work_experience(portfolio.work_experience)
            ]

        if "education" in config.enabled_sections:
            sections["education"] = [
                {
                    "degree_type": edu.degree_type,
                    "degree": edu.degree,
                    "university_name": edu.university_name,
                    "time": edu.time,
                    "location": edu.location,
                    "gpa": edu.GPA,
                    "transcript": edu.transcript,
                }
                for edu in portfolio.education
            ]

        if "skills" in config.enabled_sections:
            sections["skills"] = [
                {
                    "category": skill.category,
                    "skills": skill.skills,
                }
                for skill in portfolio.skills
            ]

        if "projects" in config.enabled_sections:
            sections["projects"] = [
                {
                    "name": proj.name,
                    "bullet_points": proj.bullet_points,
                    "date": proj.date,
                    "link": str(proj.link) if proj.link else None,
                }
                for proj in portfolio.projects
            ]

        # Awards and publications if enabled
        if "awards" in config.enabled_sections:
            sections["awards"] = [
                {"name": award.name, "explanation": award.explanation}
                for award in portfolio.awards
            ]

        if "publications" in config.enabled_sections:
            sections["publications"] = [
                {
                    "name": pub.name,
                    "publisher": pub.publisher,
                    "link": pub.link,
                    "time": pub.time,
                }
                for pub in portfolio.publications
            ]

        return {
            "personal_info": personal_info,
            "sections": sections,
            "config": {
                "theme": config.theme,
                "primary_color": config.primary_color,
                "secondary_color": config.secondary_color,
                "enabled_sections": config.enabled_sections,
                "section_order": config.section_order,
                "social_media_enabled": config.social_media_enabled,
                "contact_form_enabled": config.contact_form_enabled,
                "chatbot_enabled": config.chatbot_enabled,
                "meta_title": config.meta_title,
                "meta_description": config.meta_description,
                "meta_keywords": config.meta_keywords,
            },
            "chat": self._build_chat_context(config, personal_info, subdomain),
            "site_info": {
                "title": config.meta_title
                or (
                    personal_info.get("full_name", "Portfolio")
                    if personal_info
                    else "Portfolio"
                ),
                "description": config.meta_description
                or "Professional portfolio website",
                "keywords": config.meta_keywords,
                "url": f"https://{subdomain}.{os.getenv('VERCEL_DOMAIN_NAME', 'yarba.app')}",
                "subdomain": subdomain,
                "owner_id": str(user.id) if user and user.id else None,
            },
        }

    def _build_chat_context(
        self,
        config: WebsiteConfig,
        personal_info: dict[str, Any] | None,
        subdomain: str,
    ) -> dict[str, Any]:
        """Build chatbot widget configuration for templates."""
        full_name = (
            personal_info.get("full_name", "Portfolio Owner")
            if personal_info
            else "Portfolio Owner"
        )
        default_welcome = (
            f"Hi! I'm {full_name}'s AI assistant. "
            "Feel free to ask me anything about my experience, skills, or projects!"
        )
        api_base = self.settings.public_api_base_url
        return {
            "enabled": config.chatbot_enabled,
            "api_url": f"{api_base}/api/v1/public/portfolio/chat",
            "subdomain": subdomain,
            "full_name": full_name,
            "avatar_url": personal_info.get("profile_picture_key")
            if personal_info
            else None,
            "welcome_message": config.chatbot_welcome_message or default_welcome,
            "primary_color": config.primary_color,
            "secondary_color": config.secondary_color,
            "store_conversations": config.chatbot_store_conversations,
        }

    def _copy_chatbot_assets(self) -> dict[str, str]:
        """Copy shared chatbot static assets into the deploy bundle."""
        assets: dict[str, str] = {}
        shared_dir = self.templates_dir / "shared"

        for filename in ("chatbot.css", "chatbot.js"):
            file_path = shared_dir / filename
            if file_path.exists():
                assets[filename] = file_path.read_text(encoding="utf-8")

        return assets

    async def _generate_html_files(
        self, context: dict, config: WebsiteConfig
    ) -> dict[str, str]:
        """Generate HTML files."""
        files = {}

        try:
            # Main index.html
            template = self.env.get_template(f"themes/{config.theme}/index.html")
            files["index.html"] = template.render(**context)

            # Generate individual section pages if needed
            for section in config.enabled_sections:
                if section == "contact" and config.contact_form_enabled:
                    try:
                        contact_template = self.env.get_template(
                            f"themes/{config.theme}/contact.html"
                        )
                        files["contact.html"] = contact_template.render(**context)
                    except Exception:
                        # Contact page template not found, skip
                        pass

        except Exception as e:
            self.logger.warning(
                f"Template not found for theme {config.theme}, using default: {e}"
            )
            # Fallback to default template
            files["index.html"] = self._generate_default_html(context)

        return files

    async def _generate_css_files(
        self, context: dict, config: WebsiteConfig
    ) -> dict[str, str]:
        """Generate CSS files."""
        files = {}

        try:
            # Main stylesheet
            css_template = self.env.get_template(f"themes/{config.theme}/style.css")
            files["style.css"] = css_template.render(**context)

        except Exception as e:
            self.logger.warning(
                f"CSS template not found for theme {config.theme}, using default: {e}"
            )
            # Generate default CSS
            files["style.css"] = self._generate_default_css(config)

        return files

    async def _generate_js_files(
        self, context: dict, config: WebsiteConfig
    ) -> dict[str, str]:
        """Generate JavaScript files."""
        files = {}

        try:
            # Main JavaScript file
            js_template = self.env.get_template(f"themes/{config.theme}/script.js")
            files["script.js"] = js_template.render(**context)

        except Exception:
            # Generate minimal default JavaScript
            files["script.js"] = self._generate_default_js(config)

        return files

    async def _generate_metadata_files(
        self, context: dict, config: WebsiteConfig
    ) -> dict[str, str]:
        """Generate metadata files like manifest, robots.txt, etc."""
        files = {}

        # robots.txt
        if context["site_info"].get("url"):
            files["robots.txt"] = f"""User-agent: *
Allow: /

Sitemap: {context["site_info"]["url"]}/sitemap.xml
"""
        else:
            files["robots.txt"] = """User-agent: *
Allow: /
"""

        # sitemap.xml
        files["sitemap.xml"] = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>{context["site_info"].get("url", "")}</loc>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>
"""

        # manifest.json for PWA
        files["manifest.json"] = json.dumps(
            {
                "name": context["site_info"]["title"],
                "short_name": context["site_info"]["title"],
                "description": context["site_info"]["description"],
                "start_url": "/",
                "display": "standalone",
                "theme_color": config.primary_color,
                "background_color": "#ffffff",
                "icons": [
                    {
                        "src": "/favicon.webp",
                        "sizes": "32x32",
                        "type": "image/webp",
                    },
                    {
                        "src": "/apple-touch-icon.webp",
                        "sizes": "180x180",
                        "type": "image/webp",
                    },
                ],
            },
            indent=2,
        )

        return files

    async def _generate_favicon_files(
        self,
        profile: Profile | None,
        config: WebsiteConfig,
    ) -> dict[str, Any]:
        """Build favicon assets from the profile picture or a themed initial."""
        full_name = (
            profile.personal_information.full_name
            if profile
            and profile.personal_information
            and profile.personal_information.full_name
            else "Portfolio"
        )
        initial = full_name.strip()[:1].upper() or "P"
        background = self._parse_hex_color(config.primary_color)

        source_image: Image.Image | None = None
        if profile and profile.profile_picture_key:
            try:
                storage = get_storage_provider()
                image_bytes = await storage.get_file(profile.profile_picture_key)
                source_image = Image.open(BytesIO(image_bytes))
                source_image.load()
            except Exception as exc:
                self.logger.warning(
                    "Failed to load profile picture for favicon generation: %s",
                    exc,
                )

        favicon_bytes = self._build_favicon_image(
            source_image,
            initial=initial,
            background=background,
            size=32,
        )
        apple_touch_bytes = self._build_favicon_image(
            source_image,
            initial=initial,
            background=background,
            size=180,
        )

        return {
            "favicon.webp": {"content": favicon_bytes, "binary": True},
            "apple-touch-icon.webp": {"content": apple_touch_bytes, "binary": True},
        }

    @staticmethod
    def _parse_hex_color(color: str) -> tuple[int, int, int]:
        """Parse a hex color string into an RGB tuple."""
        normalized = color.strip().lstrip("#")
        if len(normalized) == 3:
            normalized = "".join(ch * 2 for ch in normalized)
        if len(normalized) != 6:
            return (145, 94, 255)
        try:
            return (
                int(normalized[0:2], 16),
                int(normalized[2:4], 16),
                int(normalized[4:6], 16),
            )
        except ValueError:
            return (145, 94, 255)

    @staticmethod
    def _square_crop(image: Image.Image) -> Image.Image:
        """Crop an image to a centered square."""
        width, height = image.size
        side = min(width, height)
        left = (width - side) // 2
        top = (height - side) // 2
        return image.crop((left, top, left + side, top + side))

    def _build_favicon_image(
        self,
        source_image: Image.Image | None,
        *,
        initial: str,
        background: tuple[int, int, int],
        size: int,
    ) -> bytes:
        """Create a square favicon image as WebP bytes."""
        if source_image is not None:
            image = source_image.convert("RGBA")
            image = self._square_crop(image)
            image = image.resize((size, size), Image.Resampling.LANCZOS)
        else:
            image = Image.new("RGBA", (size, size), (*background, 255))
            draw = ImageDraw.Draw(image)
            font_size = max(size // 2, 12)
            font: ImageFont.FreeTypeFont | ImageFont.ImageFont
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except OSError:
                font = ImageFont.load_default()
            bbox = draw.textbbox((0, 0), initial, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            draw.text(
                ((size - text_width) / 2 - bbox[0], (size - text_height) / 2 - bbox[1]),
                initial,
                fill=(255, 255, 255, 255),
                font=font,
            )

        buffer = BytesIO()
        image.save(buffer, format="WEBP", quality=85)
        return buffer.getvalue()

    async def _copy_theme_assets(self, config: WebsiteConfig) -> dict[str, Any]:
        """Copy all static assets from the theme directory, excluding processed template files."""
        files: dict[str, Any] = {}

        theme_dir = self.templates_dir / f"themes/{config.theme}"

        if not theme_dir.exists():
            self.logger.warning(f"Theme directory not found: {theme_dir}")
            return files

        # Files that are processed as templates and should not be copied as static assets
        template_files = {"index.html", "style.css", "script.js", "contact.html"}

        # Copy all files from theme directory except template files
        for file_path in theme_dir.rglob("*"):
            if file_path.is_file():
                # Skip template files that are processed by Jinja2
                if file_path.name in template_files:
                    continue

                # Create relative path for the deployed website
                relative_path = file_path.relative_to(theme_dir)

                try:
                    # Determine if file is text or binary
                    file_extension = file_path.suffix.lower()
                    text_extensions = {
                        ".txt",
                        ".json",
                        ".xml",
                        ".md",
                        ".svg",
                        ".css",
                        ".js",
                        ".html",
                        ".htm",
                    }

                    if file_extension in text_extensions:
                        # Text files
                        with open(file_path, encoding="utf-8") as f:
                            files[str(relative_path)] = f.read()
                    else:
                        # Binary files (images, models, etc.)
                        with open(file_path, "rb") as f:
                            file_content = f.read()
                        # Mark as binary for the deployment service
                        files[str(relative_path)] = {
                            "content": file_content,
                            "binary": True,
                        }

                    self.logger.debug(f"Copied theme asset: {relative_path}")

                except Exception as e:
                    self.logger.warning(f"Failed to copy asset {file_path}: {e}")

        self.logger.info(
            f"Copied {len(files)} static assets from theme '{config.theme}'"
        )
        return files

    def _generate_default_html(self, context: dict) -> str:
        """Generate a default HTML template when theme template is not found."""
        personal_info = context.get("personal_info", {})
        sections = context.get("sections", {})
        config = context.get("config", {})
        site_info = context.get("site_info", {})

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{site_info.get("title", "Portfolio")}</title>
    <meta name="description" content="{site_info.get("description", "")}">
    <meta name="keywords" content="{", ".join(site_info.get("keywords", []))}">
    <link rel="icon" type="image/webp" href="favicon.webp">
    <link rel="apple-touch-icon" type="image/webp" href="apple-touch-icon.webp">
    <link rel="stylesheet" href="style.css">
    <link rel="manifest" href="manifest.json">
</head>
<body>
    <header>
        <h1>{personal_info.get("full_name", "Portfolio")}</h1>
        <p class="job-title">{sections.get("about", {}).get("job_title", "Professional")}</p>
    </header>

    <main>
"""

        # Add sections based on enabled sections and order
        for section_name in config.get("section_order", []):
            if section_name not in config.get("enabled_sections", []):
                continue

            if section_name == "about" and "about" in sections:
                about = sections["about"]
                html += f"""
        <section id="about">
            <h2>About</h2>
            <p>{about.get("career_summary", "")}</p>
            {f"<p>Experience: {about.get('years_experience', '')}</p>" if about.get("years_experience") else ""}
        </section>
"""

            elif section_name == "experience" and "experience" in sections:
                html += """
        <section id="experience">
            <h2>Work Experience</h2>
"""
                for exp in sections["experience"]:
                    html += f"""
            <div class="experience-item">
                <h3>{exp.get("job_title", "")}</h3>
                <p class="company">{exp.get("company", "")} | {exp.get("location", "")} | {exp.get("time", "")}</p>
                <ul>
"""
                    for resp in exp.get("responsibilities", []):
                        html += f"                    <li>{resp}</li>\n"
                    html += """                </ul>
            </div>
"""
                html += "        </section>\n"

            elif section_name == "education" and "education" in sections:
                html += """
        <section id="education">
            <h2>Education</h2>
"""
                for edu in sections["education"]:
                    html += f"""
            <div class="education-item">
                <h3>{edu.get("degree", "")} in {edu.get("degree_type", "")}</h3>
                <p>{edu.get("university_name", "")} | {edu.get("location", "")} | {edu.get("time", "")}</p>
                {f"<p>GPA: {edu.get('gpa', '')}</p>" if edu.get("gpa") else ""}
            </div>
"""
                html += "        </section>\n"

            elif section_name == "skills" and "skills" in sections:
                html += """
        <section id="skills">
            <h2>Skills</h2>
"""
                for skill_category in sections["skills"]:
                    html += f"""
            <div class="skill-category">
                <h3>{skill_category.get("category", "")}</h3>
                <p>{", ".join(skill_category.get("skills", []))}</p>
            </div>
"""
                html += "        </section>\n"

            elif section_name == "projects" and "projects" in sections:
                html += """
        <section id="projects">
            <h2>Projects</h2>
"""
                for project in sections["projects"]:
                    html += f"""
            <div class="project-item">
                <h3>{project.get("name", "")}</h3>
                <p class="project-date">{project.get("date", "")}</p>
                <ul>
"""
                    for bullet in project.get("bullet_points", []):
                        html += f"                    <li>{bullet}</li>\n"
                    html += "                </ul>\n"
                    if project.get("link"):
                        html += f'                <a href="{project["link"]}" target="_blank">View Project</a>\n'
                    html += "            </div>\n"
                html += "        </section>\n"

            elif section_name == "contact" and personal_info:
                html += """
        <section id="contact">
            <h2>Contact</h2>
            <div class="contact-info">
"""
                if personal_info.get("email"):
                    html += f'                <p>Email: <a href="mailto:{personal_info["email"]}">{personal_info["email"]}</a></p>\n'
                if personal_info.get("phone"):
                    html += f"                <p>Phone: {personal_info['phone']}</p>\n"
                if personal_info.get("linkedin"):
                    html += f'                <p>LinkedIn: <a href="{personal_info["linkedin"]}" target="_blank">Profile</a></p>\n'
                if personal_info.get("github"):
                    html += f'                <p>GitHub: <a href="{personal_info["github"]}" target="_blank">Profile</a></p>\n'

                html += """            </div>
        </section>
"""

        html += """    </main>

    <footer>
        <p>&copy; 2024 Portfolio Website. Built with Yarba.</p>
    </footer>

    <script src="script.js"></script>
</body>
</html>"""

        return html

    def _generate_default_css(self, config: WebsiteConfig) -> str:
        """Generate default CSS when theme CSS is not found."""
        return f"""
/* Default Portfolio CSS */
* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

body {{
    font-family: 'Arial', sans-serif;
    line-height: 1.6;
    color: #333;
    background-color: #fff;
}}

header {{
    background: linear-gradient(135deg, {config.primary_color}, {config.secondary_color});
    color: white;
    text-align: center;
    padding: 2rem 0;
}}

header h1 {{
    font-size: 2.5rem;
    margin-bottom: 0.5rem;
}}

.job-title {{
    font-size: 1.2rem;
    opacity: 0.9;
}}

main {{
    max-width: 1000px;
    margin: 0 auto;
    padding: 2rem;
}}

section {{
    margin-bottom: 3rem;
    padding: 1.5rem;
    background: #f8f9fa;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}}

section h2 {{
    color: {config.primary_color};
    border-bottom: 2px solid {config.primary_color};
    padding-bottom: 0.5rem;
    margin-bottom: 1.5rem;
}}

.experience-item, .education-item, .project-item, .skill-category {{
    margin-bottom: 1.5rem;
    padding: 1rem;
    background: white;
    border-radius: 6px;
    border-left: 4px solid {config.primary_color};
}}

.experience-item h3, .education-item h3, .project-item h3 {{
    color: {config.secondary_color};
    margin-bottom: 0.5rem;
}}

.company, .project-date {{
    color: #666;
    font-style: italic;
    margin-bottom: 0.5rem;
}}

ul {{
    margin-left: 1.5rem;
}}

li {{
    margin-bottom: 0.3rem;
}}

a {{
    color: {config.primary_color};
    text-decoration: none;
}}

a:hover {{
    text-decoration: underline;
}}

.contact-info p {{
    margin-bottom: 0.5rem;
}}

footer {{
    text-align: center;
    padding: 2rem;
    background: #f8f9fa;
    border-top: 1px solid #dee2e6;
    margin-top: 3rem;
}}

/* Responsive Design */
@media (max-width: 768px) {{
    main {{
        padding: 1rem;
    }}

    header h1 {{
        font-size: 2rem;
    }}

    section {{
        padding: 1rem;
    }}
}}
"""

    def _generate_default_js(self, config: WebsiteConfig) -> str:
        """Generate default JavaScript when theme JS is not found."""
        header = f"// Default Portfolio JavaScript (theme: {config.theme})\n"
        return (
            header
            + """
// Default Portfolio JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Smooth scrolling for anchor links
    const links = document.querySelectorAll('a[href^="#"]');

    links.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();

            const targetId = this.getAttribute('href');
            const targetSection = document.querySelector(targetId);

            if (targetSection) {
                targetSection.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });

    // Add fade-in animation to sections
    const sections = document.querySelectorAll('section');
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    });

    sections.forEach(section => {
        section.style.opacity = '0';
        section.style.transform = 'translateY(20px)';
        section.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(section);
    });
});
"""
        )

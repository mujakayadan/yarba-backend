"""Generator service for resume and cover letter generation."""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..exceptions.base import InternalServerException, NotFoundException
from ..models.resume import Resume
from ..repositories.resume import ResumeRepository
from ..repositories.user import UserRepository
from .config import settings
from .latex import LaTeXService
from .llm import LLMService
from .portfolio import PortfolioService
from .prompt import PromptService

logger = logging.getLogger(__name__)


class GeneratorService:
    """Service for generating resumes and cover letters."""

    def __init__(
        self,
        llm_service: LLMService,
        prompt_service: PromptService,
        latex_service: LaTeXService,
        portfolio_service: PortfolioService,
        resume_repository: ResumeRepository,
        user_repository: UserRepository,
    ):
        """
        Initialize the generator service.

        Args:
            llm_service: LLM service instance
            prompt_service: Prompt service instance
            latex_service: LaTeX service instance
            portfolio_service: Portfolio service instance
            resume_repository: Resume repository instance
            user_repository: User repository instance
        """
        self.llm_service = llm_service
        self.prompt_service = prompt_service
        self.latex_service = latex_service
        self.portfolio_service = portfolio_service
        self.resume_repository = resume_repository
        self.user_repository = user_repository
        self.logger = logging.getLogger(self.__class__.__name__)

    async def generate_resume(
        self,
        user_id: str,
        job_description: str,
        selected_sections: Dict[str, str],
        title: Optional[str] = None,
        template_id: str = "default",
    ) -> Resume:
        """
        Generate a resume based on the provided job description and settings.

        Args:
            user_id: User ID
            job_description: Job description
            selected_sections: Dictionary of section names and their generation method ('ai' or 'hardcode')
            title: Optional resume title
            template_id: Template ID

        Returns:
            Resume: Generated resume

        Raises:
            NotFoundException: If user not found
            InternalServerException: If generation fails
        """
        self.logger.info(f"Starting resume generation for user {user_id}")

        # Verify user exists
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            self.logger.error(f"User not found: {user_id}")
            raise NotFoundException("User not found")

        try:
            # Generate title if not provided
            if not title:
                company_name, job_title = (
                    await self.llm_service.create_company_name_and_job_title(
                        job_description, user_id
                    )
                )
                title = f"{company_name} - {job_title}"

            # Initialize content dictionary
            content_dict = {section: "" for section in selected_sections}

            # Process each section
            for section, process_type in selected_sections.items():
                self.logger.debug(
                    f"Processing section {section} with method {process_type}"
                )

                if process_type == "ai":
                    content = await self._process_ai_section(
                        section, job_description, user_id
                    )
                elif process_type == "hardcode":
                    content = await self._process_hardcode_section(section, user_id)
                else:
                    self.logger.warning(
                        f"Unknown process type: {process_type}, defaulting to AI"
                    )
                    content = await self._process_ai_section(
                        section, job_description, user_id
                    )

                content_dict[section] = content

            # Create resume in database
            resume = Resume(
                user=user,
                title=title,
                template_id=template_id,
                job_description=job_description,
                **content_dict,
            )

            created_resume = await self.resume_repository.create(resume)
            self.logger.info(f"Resume created: {created_resume.id}")

            return created_resume

        except Exception as e:
            self.logger.error(f"Error generating resume: {str(e)}")
            raise InternalServerException(f"Error generating resume: {str(e)}")

    async def _process_hardcode_section(self, section: str, user_id: str) -> str:
        """
        Process a hardcoded section.

        Args:
            section: Section name
            user_id: User ID

        Returns:
            str: Section content

        Raises:
            NotFoundException: If section data not found
        """
        try:
            # Get section data from portfolio
            portfolio = await self.portfolio_service.get_portfolio(user_id)

            # Extract section data
            if section == "personal_information":
                data = {
                    "name": portfolio.full_name,
                    "email": portfolio.email,
                    "phone": portfolio.phone,
                    "address": portfolio.address,
                    "linkedin": portfolio.linkedin,
                    "website": portfolio.website,
                }
                return self._format_personal_information(data)

            elif hasattr(portfolio, section):
                section_data = getattr(portfolio, section)
                if section_data:
                    return self._format_section(section, section_data)

            self.logger.warning(f"Section {section} not found in portfolio")
            return ""

        except Exception as e:
            self.logger.error(f"Error processing hardcode section {section}: {str(e)}")
            return ""

    async def _process_ai_section(
        self, section: str, job_description: str, user_id: str
    ) -> str:
        """
        Process an AI-generated section.

        Args:
            section: Section name
            job_description: Job description
            user_id: User ID

        Returns:
            str: Section content

        Raises:
            InternalServerException: If generation fails
        """
        try:
            # Get section data from portfolio
            portfolio = await self.portfolio_service.get_portfolio(user_id)

            # Extract section data
            if section == "personal_information":
                data = {
                    "name": portfolio.full_name,
                    "email": portfolio.email,
                    "phone": portfolio.phone,
                    "address": portfolio.address,
                    "linkedin": portfolio.linkedin,
                    "website": portfolio.website,
                }
                section_data = str(data)
            elif hasattr(portfolio, section):
                section_data = str(getattr(portfolio, section))
            else:
                self.logger.warning(f"Section {section} not found in portfolio")
                section_data = "{}"

            # Get section prompt
            prompt = await self.prompt_service.get_section_prompt(section, user_id)

            # Generate content
            content = await self.llm_service.generate_content(
                prompt, section_data, job_description
            )

            return content

        except Exception as e:
            self.logger.error(f"Error processing AI section {section}: {str(e)}")
            raise InternalServerException(
                f"Error processing AI section {section}: {str(e)}"
            )

    def _format_section(self, section: str, data: any) -> str:
        """
        Format section data as LaTeX.

        Args:
            section: Section name
            data: Section data

        Returns:
            str: Formatted LaTeX content
        """
        # This is a simplified version - in a real implementation,
        # you would have more sophisticated formatting logic
        if section == "skills":
            return self._format_skills(data)
        elif section == "work_experience":
            return self._format_work_experience(data)
        elif section == "education":
            return self._format_education(data)
        elif section == "projects":
            return self._format_projects(data)
        elif section == "awards":
            return self._format_awards(data)
        elif section == "publications":
            return self._format_publications(data)
        elif section == "career_summary":
            return data
        else:
            return str(data)

    def _format_personal_information(self, data: Dict[str, str]) -> str:
        """
        Format personal information as LaTeX.

        Args:
            data: Personal information

        Returns:
            str: Formatted LaTeX content
        """
        latex = "\\begin{center}\n"

        if "name" in data and data["name"]:
            latex += f"\\textbf{{\\Large {data['name']}}}\\\\\n"

        address_parts = []
        if "address" in data and data["address"]:
            address_parts.append(data["address"])

        if address_parts:
            latex += f"{' '.join(address_parts)}\\\\\n"

        contact_parts = []
        if "phone" in data and data["phone"]:
            contact_parts.append(data["phone"])
        if "email" in data and data["email"]:
            contact_parts.append(data["email"])
        if "linkedin" in data and data["linkedin"]:
            contact_parts.append(data["linkedin"])

        if contact_parts:
            latex += f"{' | '.join(contact_parts)}\n"

        latex += "\\end{center}\n\n"

        return latex

    def _format_skills(self, skills: Dict[str, List[str]]) -> str:
        """
        Format skills as LaTeX.

        Args:
            skills: Skills

        Returns:
            str: Formatted LaTeX content
        """
        latex = "\\section*{Skills}\n"

        for category, skill_list in skills.items():
            latex += f"\\textbf{{{category}}}: {', '.join(skill_list)}\\\\\n"

        latex += "\n"

        return latex

    def _format_work_experience(self, work_experience: List[Dict]) -> str:
        """
        Format work experience as LaTeX.

        Args:
            work_experience: Work experience

        Returns:
            str: Formatted LaTeX content
        """
        latex = "\\section*{Work Experience}\n"
        latex += "\\begin{itemize}[leftmargin=*]\n"

        for job in work_experience:
            company = job.get("company", "")
            position = job.get("position", "")
            start_date = job.get("start_date", "")
            end_date = job.get(
                "end_date", "Present" if job.get("current", False) else ""
            )

            latex += (
                f"\\item \\textbf{{{company}}} \\hfill {start_date} -- {end_date}\\\\\n"
            )
            latex += f"\\textit{{{position}}}\n"

            if "responsibilities" in job and job["responsibilities"]:
                latex += "\\begin{itemize}\n"
                for responsibility in job["responsibilities"]:
                    latex += f"\\item {responsibility}\n"
                latex += "\\end{itemize}\n"

        latex += "\\end{itemize}\n\n"

        return latex

    def _format_education(self, education: List[Dict]) -> str:
        """
        Format education as LaTeX.

        Args:
            education: Education

        Returns:
            str: Formatted LaTeX content
        """
        latex = "\\section*{Education}\n"
        latex += "\\begin{itemize}[leftmargin=*]\n"

        for edu in education:
            institution = edu.get("institution", "")
            degree = edu.get("degree", "")
            field = edu.get("field_of_study", "")
            start_date = edu.get("start_date", "")
            end_date = edu.get(
                "end_date", "Present" if edu.get("current", False) else ""
            )
            gpa = edu.get("gpa", "")

            latex += f"\\item \\textbf{{{institution}}} \\hfill {start_date} -- {end_date}\\\\\n"
            latex += f"{degree} in {field}"

            if gpa:
                latex += f" \\hfill \\textit{{GPA: {gpa}}}"

            latex += "\n"

            if "courses" in edu and edu["courses"]:
                latex += f"\\textit{{Relevant Courses:}} {', '.join(edu['courses'])}\n"

        latex += "\\end{itemize}\n\n"

        return latex

    def _format_projects(self, projects: List[Dict]) -> str:
        """
        Format projects as LaTeX.

        Args:
            projects: Projects

        Returns:
            str: Formatted LaTeX content
        """
        latex = "\\section*{Projects}\n"
        latex += "\\begin{itemize}[leftmargin=*]\n"

        for project in projects:
            name = project.get("name", "")
            description = project.get("description", "")

            latex += f"\\item \\textbf{{{name}}}\\\\\n"
            latex += f"{description}\n"

            if "technologies" in project and project["technologies"]:
                latex += (
                    f"\\textit{{Technologies:}} {', '.join(project['technologies'])}\n"
                )

        latex += "\\end{itemize}\n\n"

        return latex

    def _format_awards(self, awards: List[Dict]) -> str:
        """
        Format awards as LaTeX.

        Args:
            awards: Awards

        Returns:
            str: Formatted LaTeX content
        """
        latex = "\\section*{Awards}\n"
        latex += "\\begin{itemize}[leftmargin=*]\n"

        for award in awards:
            title = award.get("title", "")
            issuer = award.get("issuer", "")
            date = award.get("date", "")

            latex += f"\\item \\textbf{{{title}}}"

            if issuer:
                latex += f", {issuer}"

            if date:
                latex += f" \\hfill {date}"

            latex += "\n"

        latex += "\\end{itemize}\n\n"

        return latex

    def _format_publications(self, publications: List[Dict]) -> str:
        """
        Format publications as LaTeX.

        Args:
            publications: Publications

        Returns:
            str: Formatted LaTeX content
        """
        latex = "\\section*{Publications}\n"
        latex += "\\begin{itemize}[leftmargin=*]\n"

        for publication in publications:
            title = publication.get("title", "")
            authors = publication.get("authors", "")
            journal = publication.get("journal", "")
            date = publication.get("date", "")

            latex += f"\\item \\textbf{{{title}}}"

            if authors:
                latex += f"\\\\\n{authors}"

            if journal:
                latex += f", {journal}"

            if date:
                latex += f" ({date})"

            latex += "\n"

        latex += "\\end{itemize}\n\n"

        return latex

    async def generate_cover_letter(
        self,
        user_id: str,
        job_description: str,
        title: Optional[str] = None,
        template_id: str = "default",
    ) -> Resume:
        """
        Generate a cover letter based on the provided job description.

        Args:
            user_id: User ID
            job_description: Job description
            title: Optional cover letter title
            template_id: Template ID

        Returns:
            Resume: Generated cover letter

        Raises:
            NotFoundException: If user not found
            InternalServerException: If generation fails
        """
        self.logger.info(f"Starting cover letter generation for user {user_id}")

        # Verify user exists
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            self.logger.error(f"User not found: {user_id}")
            raise NotFoundException("User not found")

        try:
            # Generate title if not provided
            if not title:
                company_name, job_title = (
                    await self.llm_service.create_company_name_and_job_title(
                        job_description, user_id
                    )
                )
                title = f"{company_name} - Cover Letter"

            # Get portfolio data
            portfolio = await self.portfolio_service.get_portfolio(user_id)

            # Get cover letter prompt
            prompt = await self.prompt_service.get_cover_letter_prompt(user_id)

            # Generate content
            portfolio_data = {
                "name": portfolio.full_name,
                "email": portfolio.email,
                "phone": portfolio.phone,
                "address": portfolio.address,
                "linkedin": portfolio.linkedin,
                "website": portfolio.website,
                "skills": portfolio.skills,
                "work_experience": portfolio.work_experience,
                "education": portfolio.education,
            }

            content = await self.llm_service.generate_content(
                prompt, str(portfolio_data), job_description
            )

            # Create cover letter in database (using Resume model for simplicity)
            resume = Resume(
                user=user,
                title=title,
                template_id=template_id,
                job_description=job_description,
                is_cover_letter=True,
                cover_letter_content=content,
            )

            created_resume = await self.resume_repository.create(resume)
            self.logger.info(f"Cover letter created: {created_resume.id}")

            return created_resume

        except Exception as e:
            self.logger.error(f"Error generating cover letter: {str(e)}")
            raise InternalServerException(f"Error generating cover letter: {str(e)}")

    async def generate_pdf(self, resume_id: str, user_id: str) -> bytes:
        """
        Generate a PDF from a resume.

        Args:
            resume_id: Resume ID
            user_id: User ID

        Returns:
            bytes: PDF content

        Raises:
            NotFoundException: If resume not found
            InternalServerException: If PDF generation fails
        """
        # Get resume
        resume = await self.resume_repository.get_by_id(resume_id)
        if not resume or str(resume.user.id) != user_id:
            self.logger.error(f"Resume not found or access denied: {resume_id}")
            raise NotFoundException("Resume not found")

        try:
            # Generate PDF
            pdf = self.latex_service.generate_pdf_from_resume(resume)
            self.logger.info(f"PDF generated for resume: {resume_id}")

            return pdf

        except Exception as e:
            self.logger.error(f"Error generating PDF: {str(e)}")
            raise InternalServerException(f"Error generating PDF: {str(e)}")

    async def save_pdf(
        self, resume_id: str, user_id: str, output_dir: Optional[Path] = None
    ) -> Path:
        """
        Save a PDF to disk.

        Args:
            resume_id: Resume ID
            user_id: User ID
            output_dir: Optional output directory

        Returns:
            Path: Path to saved PDF

        Raises:
            NotFoundException: If resume not found
            InternalServerException: If PDF generation fails
        """
        # Generate PDF
        pdf_content = await self.generate_pdf(resume_id, user_id)

        # Get resume
        resume = await self.resume_repository.get_by_id(resume_id)

        # Determine output directory
        if not output_dir:
            output_dir = Path(settings.paths.output_dir)

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Determine filename
        filename = f"{resume.title.replace(' ', '_')}.pdf"
        pdf_path = output_dir / filename

        # Save PDF
        with open(pdf_path, "wb") as f:
            f.write(pdf_content)

        self.logger.info(f"PDF saved to {pdf_path}")

        return pdf_path

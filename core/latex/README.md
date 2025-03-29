# LaTeX Module

This module provides the LaTeX compilation functionality for the resume builder application. It handles the generation of LaTeX documents from templates and data, and the compilation of those documents to PDF.

## Components

- `base.py`: Base classes for LaTeX compilation
- `compilers/`: Specific compilers for different document types
  - `resume.py`: Compiler for resume documents
  - `cover_letter.py`: Compiler for cover letter documents
- `utils/`: Utility functions for LaTeX processing
  - `placeholder.py`: Manage placeholder substitution in templates
  - `sanitizer.py`: Sanitize text for LaTeX compatibility
  - `latex_escaper.py`: Escape LaTeX special characters
  - `json_to_latex.py`: Convert JSON schema data to LaTeX format

## JSON Schema Integration

The LaTeX module now supports integrating with JSON schema data from LLM responses. This provides a more structured approach to generating LaTeX documents:

1. **Structured Data Processing**: JSON schemas from LLM responses are parsed and validated
2. **Section-Specific Processing**: Each resume section has a dedicated processor function
3. **LaTeX Command Generation**: Converts structured data to appropriate LaTeX commands
4. **Fallback Support**: Gracefully handles cases where JSON parsing fails

### Example Usage

```python
from core.latex.utils import process_content_by_section

# Process a work experience section from JSON
work_exp_latex = process_content_by_section("work_experience", json_data)

# Process skills section from JSON
skills_latex = process_content_by_section("skills", json_data)
```

See the [JSON to LaTeX documentation](utils/README.md) for more details.

## Usage

The module is primarily used through the `LatexService` in `core/services/latex_service.py`, which provides high-level methods for generating LaTeX documents and compiling them to PDF.

```python
from core.services.latex_service import get_latex_service

latex_service = get_latex_service()
latex_content = await latex_service.generate_resume_latex(resume, profile)
pdf_content = await latex_service.compile_latex_to_pdf(latex_content)
```

## Customization

The LaTeX templates, headers, and preambles are stored in the database and can be customized by the user. The module provides functionality to retrieve and use these custom templates.

## Architecture

The LaTeX module consists of several components:

1. **Base Compiler (`base.py`)**:
   - Provides abstract base class `LatexCompiler` for LaTeX compilation
   - Handles the compilation process, file management, and cleanup

2. **Specialized Compilers**:
   - `ResumeCompiler`: Generates and compiles resume documents
   - `CoverLetterCompiler`: Generates and compiles cover letter documents

3. **Utility Functions**:
   - `placeholder.py`: Manages placeholders in LaTeX templates
   - `sanitizer.py`: Sanitizes user input for LaTeX
   - `latex_escaper.py`: Escapes special LaTeX characters

## Usage

The LaTeX module should be used through the unified `LatexService` in `core/services/latex_service.py`.

### Example Usage

```python
from core.services.latex_service import LatexService
from core.repositories.preamble_repository import get_preamble_repository
from core.repositories.tex_header_repository import get_tex_header_repository
from core.repositories.tex_template_repository import get_tex_template_repository

# Initialize repositories
preamble_repo = get_preamble_repository()
header_repo = get_tex_header_repository()
template_repo = get_tex_template_repository()

# Create LaTeX service
latex_service = LatexService(
    preamble_repository=preamble_repo,
    header_repository=header_repo,
    template_repository=template_repo
)

# Generate LaTeX for a resume
resume_latex = await latex_service.generate_resume_latex(resume, profile)

# Compile LaTeX to PDF
pdf_bytes = await latex_service.compile_latex_to_pdf(resume_latex, is_cover_letter=False)
```

## Templates and Headers

The LaTeX service uses templates and headers stored in the database:

- **Templates**: Define the overall document structure
- **Headers**: Define the document header section
- **Preambles**: Define the LaTeX preamble (packages, etc.)

Access these through the service methods:

```python
# Get a template
template = await latex_service.get_template("resume")

# Get a header
header = await latex_service.get_header("modern")

# Get a preamble
preamble = await latex_service.get_preamble(preamble_id)
```

## Extending

To add a new document type:

1. Create a new compiler class in `compilers/` inheriting from `LatexCompiler`
2. Implement the `generate_tex_content` method
3. Add appropriate methods to `LatexService` for the new document type

## Notes

- The `TexService` is deprecated and will be removed in a future version. Use `LatexService` instead.
- All LaTeX generation should go through the `LatexService` for consistency.

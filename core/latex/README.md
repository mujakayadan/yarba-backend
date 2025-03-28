# LaTeX Module

This module provides LaTeX document generation and compilation functionality for the Resume Builder application.

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

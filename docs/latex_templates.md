# LaTeX Templates Documentation

## Overview

This document provides comprehensive documentation for the LaTeX templates used in the Yarba resume generation system. The templates are defined in `core/latex/templates.py` and provide the foundation for generating professional resumes and cover letters.

## Available Templates

### 1. Default Resume Template (`DEFAULT_RESUME_PREAMBLE`)

The default template provides a clean, professional black and white resume layout that is ATS-friendly and widely compatible.

**Key Features:**
- Clean, traditional design
- Black and white color scheme
- ATS-optimized formatting
- Standard margins and spacing
- Professional typography

**Best for:**
- Traditional industries (Finance, Legal, Healthcare)
- ATS-heavy application processes
- Conservative professional environments

### 2. Modern Resume Template (`MODERN_RESUME_PREAMBLE`)

The modern template offers a contemporary design with color accents and enhanced visual hierarchy.

**Key Features:**
- Professional color scheme:
  - Primary: Dark Blue (RGB: 0, 51, 102)
  - Accent: Green (RGB: 46, 125, 50)
  - Text: Dark Gray (RGB: 33, 37, 41)
- Enhanced typography and spacing
- Color-coded sections
- Modern visual hierarchy

**Best for:**
- Tech industry
- Creative fields
- Modern corporations
- Startups

## Template Structure

### Preamble Components

Each template includes the following components:

1. **Document Class and Packages**
   - Base document setup
   - Required LaTeX packages
   - Font and encoding settings

2. **Page Layout**
   - Margin adjustments
   - Header/footer configuration
   - Page styling

3. **Section Formatting**
   - Title formatting
   - Color schemes (for modern template)
   - Spacing rules

4. **Custom Commands**
   - Resume-specific LaTeX commands
   - Formatting utilities

## Available LaTeX Commands

### Personal Information

```latex
\personalInformation{Name}{Phone}{Email}{LinkedIn}{GitHub}{Website}{Location}
```

**Parameters:**
- `Name`: Full name
- `Phone`: Phone number
- `Email`: Email address
- `LinkedIn`: LinkedIn profile URL
- `GitHub`: GitHub profile URL
- `Website`: Personal website URL
- `Location`: Current location

### Career Summary

```latex
\careerSummary{summary_text}
```

**Parameters:**
- `summary_text`: Professional summary paragraph

### Work Experience

```latex
\resumeSubheading{Position}{Company}{Employment Type}{Date Range}
\resumeWorkHeading{Position}{Company}{Employment Type}{Date Range}{Description}
```

**Parameters:**
- `Position`: Job title
- `Company`: Company name
- `Employment Type`: Full-time, Part-time, Contract, etc.
- `Date Range`: Employment period
- `Description`: Job responsibilities and achievements

### Education

```latex
\resumeEducationHeading{Institution}{Location}{Degree}{Date}{Additional Info}
```

**Parameters:**
- `Institution`: School/University name
- `Location`: Institution location
- `Degree`: Degree type and major
- `Date`: Graduation date
- `Additional Info`: GPA, honors, etc.

### Projects

```latex
\resumeProjectHeading{Project Name}{Date}
```

**Parameters:**
- `Project Name`: Name of the project
- `Date`: Project completion date or duration

### Skills

```latex
\resumeSkillHeading{Skill Category}{Skills List}
```

**Parameters:**
- `Skill Category`: Category name (e.g., "Programming Languages")
- `Skills List`: Comma-separated list of skills

### Awards and Certifications

```latex
\resumeAwardHeading{Award Name}{Description}
```

**Parameters:**
- `Award Name`: Name of award or certification
- `Description`: Award description or issuing organization

### Volunteering

```latex
\resumeVolunteeringHeading{Organization}{Location}{Role}{Date Range}
```

**Parameters:**
- `Organization`: Organization name
- `Location`: Organization location
- `Role`: Volunteer role/position
- `Date Range`: Volunteer period

### List Management

```latex
\resumeSubHeadingListStart
\resumeSubHeadingListEnd

\resumeItemListStart
\resumeItemListEnd
```

**Usage:**
- Use `\resumeSubHeadingListStart` and `\resumeSubHeadingListEnd` to wrap section items
- Use `\resumeItemListStart` and `\resumeItemListEnd` to wrap bullet points

### Individual Items

```latex
\resumeItem{item_text}
\resumeSubItem{item_text}
```

**Parameters:**
- `item_text`: Individual bullet point or item text

## Template Differences

| Feature | Default Template | Modern Template |
|---------|------------------|-----------------|
| Color Scheme | Black & White | Blue/Green/Gray |
| Typography | Standard | Enhanced |
| Spacing | Standard | Tighter |
| Visual Hierarchy | Traditional | Modern |
| ATS Compatibility | Excellent | Good |
| Industries | Traditional | Tech/Creative |

## Usage Examples

### Basic Resume Structure

```latex
\documentclass[letterpaper,11pt]{article}
% ... preamble content ...

\begin{document}

% Personal Information
\personalInformation{John Doe}{+1-555-123-4567}{john.doe@email.com}{https://linkedin.com/in/johndoe}{https://github.com/johndoe}{https://johndoe.com}{New York, NY}

% Career Summary
\section{Career Summary}
\careerSummary{Experienced software engineer with 5+ years of experience in full-stack development...}

% Work Experience
\section{Experience}
\resumeSubHeadingListStart
  \resumeSubheading{Senior Software Engineer}{Tech Company}{Full-time}{Jan 2020 -- Present}
  \resumeItemListStart
    \resumeItem{Led development of microservices architecture serving 1M+ users}
    \resumeItem{Implemented CI/CD pipeline reducing deployment time by 60\%}
  \resumeItemListEnd
\resumeSubHeadingListEnd

% Education
\section{Education}
\resumeSubHeadingListStart
  \resumeEducationHeading{University of Technology}{Boston, MA}{Bachelor of Science in Computer Science}{May 2018}{GPA: 3.8/4.0}
\resumeSubHeadingListEnd

% Skills
\section{Technical Skills}
\resumeSubHeadingListStart
  \resumeSkillHeading{Programming Languages}{Python, JavaScript, Java, C++}
  \resumeSkillHeading{Frameworks}{React, Node.js, Django, Spring Boot}
  \resumeSkillHeading{Tools}{Git, Docker, AWS, Jenkins}
\resumeSubHeadingListEnd

\end{document}
```

## Adding New Templates

To add a new template:

1. **Add a `.tex` file** under `templates/latex/resume/` or `templates/latex/cover_letter/`
2. **Register it** in `core/latex/template_registry.py` (`RESUME_TEMPLATE_METADATA` or `COVER_LETTER_TEMPLATE_METADATA`)
3. **Include required commands**: Ensure all standard LaTeX commands used by processors are defined in the preamble
4. **Test compatibility**: Verify PDF generation with existing section processors

### Template Requirements

Every template must include:
- All standard LaTeX commands listed above
- ATS-compatible formatting
- Consistent command signatures
- Proper spacing and margins
- UTF-8 encoding support

## Best Practices

### For Template Development

1. **Maintain Compatibility**: Keep command signatures consistent across templates
2. **Test Thoroughly**: Verify with different content types and lengths
3. **Consider ATS**: Ensure machine readability
4. **Document Changes**: Update this documentation when adding features

### For Template Selection

1. **Consider Industry**: Choose appropriate style for target industry
2. **ATS Priority**: Use default template for ATS-heavy processes
3. **Visual Impact**: Use modern template for visual-focused roles
4. **Content Length**: Consider how template handles varying content amounts

### For Processors

1. **Template Agnostic**: Write processors that work with any template
2. **Use Standard Commands**: Stick to documented command set
3. **Handle Edge Cases**: Account for missing or optional content
4. **Test Multiple Templates**: Verify compatibility across all templates

## Troubleshooting

### Common Issues

1. **Missing Commands**: Ensure all required commands are defined in template
2. **Spacing Issues**: Check margin and spacing settings
3. **Color Problems**: Verify color package imports for modern template
4. **Font Issues**: Ensure proper font packages are loaded

### Performance Considerations

1. **Package Loading**: Only include necessary packages
2. **Color Usage**: Minimize color operations for faster compilation
3. **Image Handling**: Optimize image processing if used
4. **Memory Usage**: Consider template complexity impact

## Integration

### With Processors

Templates work with the following processors:
- `personal_information.py`
- `career_summary.py`
- `work_experience.py`
- `education.py`
- `projects.py`
- `skills.py`
- `awards.py`
- `certifications.py`
- `publications.py`

### With Template Registry

Templates are registered in `template_registry.py` and can be selected during resume generation.

### With Compilation

Templates are compiled using the LaTeX service (`latex_service.py`) which handles:
- Template selection
- Content injection
- PDF generation
- Error handling

## Future Enhancements

Potential improvements for the template system:

1. **Dynamic Theming**: Runtime color customization
2. **Layout Variants**: Different section arrangements
3. **Industry-Specific Templates**: Templates optimized for specific fields
4. **Accessibility Features**: Enhanced screen reader compatibility
5. **Multi-language Support**: Internationalization features

## Contributing

When contributing to templates:

1. Follow existing code style
2. Test with sample data
3. Update documentation
4. Consider backward compatibility
5. Validate ATS compatibility

---

*Last Updated: [Current Date]*
*Version: 1.0*

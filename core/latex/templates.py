"""LaTeX templates for resume and cover letter generation.

This module contains hardcoded LaTeX templates for resume and cover letter generation.
All templates are stored directly in code for easier maintenance.
"""

# Resume section templates
RESUME_SECTION_TEMPLATES = {
    "personal_information": "\\personalInformation{{{full_name}}}{{{phone}}}{{{email}}}{{{linkedIn}}}{{{gitHub}}}{{{website}}}{{{address}}}\n",
    "career_summary": "\\section{Career Summary}\n\\careerSummary{{{job_title}}}{{{years_of_experience}}}{{{career_summary}}}\n\n",
    "skills": "\\section{Skills}\n\\resumeSubHeadingListStart\n{skills_content}\n\\resumeSubHeadingListEnd\n",
    "work_experience": "\\section{Work Experience}\n\\vspace{3pt}\n\\resumeSubHeadingListStart\n{experience_content}\n\\resumeSubHeadingListEnd\n",
    "education": "\\section{Education}\n\\vspace{3pt}\n{education_content}\n",
    "projects": "\\section{Projects}\n{projects_content}\n",
    "awards": "\\section{Awards \\& Achievements}\n\\resumeSubHeadingListStart\n{awards_content}\n\\resumeSubHeadingListEnd\n",
    "publications": "\\section{Publications}\n\\vspace{3pt}\n\\resumeSubHeadingListStart\n{publications_content}\n\\resumeSubHeadingListEnd\n",
    "certifications": "\\section{Certifications}\n\\resumeSubHeadingListStart\n{certifications_content}\n\\resumeSubHeadingListEnd\n",
}

# Resume item templates
RESUME_ITEM_TEMPLATES = {
    "skill_item": "\\resumeSkillHeading{{{category}}}{{{skills_list}}}\n",
    "work_experience_item": "\\resumeSubheading\n    {{{job_title}}}{{{time}}}\n    {{{company}}}{{{location}}}\n    \\resumeItemListStart\n{responsibilities}\n    \\resumeItemListEnd\n",
    "education_item": "\\resumeEducationHeading\n{{{university}}}\n{{{location}}}\n{{{degree}}}\n{{{time}}}\n{{{key_courses}}}\n",
    "project_item": "\\resumeProjectHeading\n{{{name_and_tech}}}\n{{{date}}}\n\\resumeItemListStart\n{bullet_points}\n\\resumeItemListEnd\n",
    "award_item": "\\resumeAwardHeading{{{name}}}{{{explanation}}}\n",
    "publication_item": "\\resumeProjectHeading\n{{\\textbf{{{name}}}}}{{{time}}}\n\\resumeItem{{\\href{{{link}}}{{\\color{{blue}}{publisher}}}}}\n",
    "certification_item": "\\resumeItem{{{name}}} - {{{authority}}} ({{{date}}})\n",
    "bullet_point": "\\resumeItem{{{content}}}\n",
}


# Get a resume section template
def get_resume_section_template(section_name: str) -> str:
    """
    Get a resume section template by name.

    Args:
        section_name: Name of the section

    Returns:
        Section template content or empty string if not found
    """
    return RESUME_SECTION_TEMPLATES.get(section_name, "")


# Get a resume item template
def get_resume_item_template(item_name: str) -> str:
    """
    Get a resume item template by name.

    Args:
        item_name: Name of the item

    Returns:
        Item template content or empty string if not found
    """
    return RESUME_ITEM_TEMPLATES.get(item_name, "")


# Default resume preamble
DEFAULT_RESUME_PREAMBLE = """\\documentclass[letterpaper,11pt]{article}
\\usepackage{latexsym}
\\usepackage[empty]{fullpage}
\\usepackage{titlesec}
\\usepackage{marvosym}
\\usepackage[usenames,dvipsnames]{color}
\\usepackage{verbatim}
\\usepackage{enumitem}
\\usepackage[hidelinks]{hyperref}
\\usepackage{fancyhdr}
\\usepackage[english]{babel}
\\usepackage{tabularx}
\\usepackage{hyphenat}
\\usepackage{fontawesome}
\\usepackage{seqsplit}
\\usepackage[T1]{fontenc}
\\usepackage[utf8x]{inputenc}
\\usepackage{lmodern,textcomp}
\\usepackage{bookmark}

\\pagestyle{fancy}
\\fancyhf{} % clear all header and footer fields
\\fancyfoot{}
\\renewcommand{\\headrulewidth}{0pt}
\\renewcommand{\\footrulewidth}{0pt}

% Adjust margins
\\addtolength{\\oddsidemargin}{-0.5in}
\\addtolength{\\evensidemargin}{-0.5in}
\\addtolength{\\textwidth}{1in}
\\addtolength{\\topmargin}{-.5in}
\\addtolength{\\textheight}{1.0in}

\\urlstyle{same}

\\raggedbottom
\\raggedright
\\setlength{\\tabcolsep}{0in}
\\setlength{\\footskip}{4.08003pt}


% Sections formatting
\\titleformat{\\section}{
  \\vspace{-4pt}\\scshape\\raggedright\\large
}{}{0em}{}[\\color{black}\\titlerule \\vspace{-5pt}]

% Ensure that generated pdf is machine readable/ATS parsable
\\pdfgentounicode=1

%-------------------------
% Custom commands

\\newcommand{\\resumeItem}[1]{
  \\item\\small{
    {#1 \\vspace{-2pt}}
  }
}


\\newcommand{\\resumeSubheading}[4]{
  \\vspace{-2pt}\\item
    \\begin{tabular*}{0.97\\textwidth}[t]{l@{\\extracolsep{\\fill}}r}
      \\textbf{#1} & #2 \\\\
      \\textit{\\small#3} & \\textit{\\small #4} \\\\
    \\end{tabular*}\\vspace{-7pt}
}

\\newcommand{\\resumeVolunteeringHeading}[4]{
  \\vspace{-2pt}\\item
    \\begin{tabular*}{0.97\\textwidth}[t]{l@{\\extracolsep{\\fill}}r}
      \\textbf{#1} & #2 \\\\
      \\textit{\\small#3} & \\textit{\\small #4} \\\\
    \\end{tabular*}\\vspace{-7pt}
}

\\newcommand{\\resumeSubSubheading}[2]{
    \\vspace{-2pt}\\item
    \\begin{tabular*}{0.97\\textwidth}{l@{\\extracolsep{\\fill}}r}
      \\textit{\\small#1} & \\textit{\\small #2} \\\\
    \\end{tabular*}\\vspace{-7pt}
}


\\newcommand{\\resumeEducationHeading}[5]{
  \\vspace{-2pt}\\item
    \\begin{tabular*}{0.97\\textwidth}[t]{l@{\\extracolsep{\\fill}}r}
      \\textbf{#1} & #2 \\\\
      \\textit{\\small#3} & \\textit{\\small #4} \\\\
    \\end{tabular*}\\vspace{1pt} \\\\
    \\textit{\\small#5} \\\\
}


\\newcommand{\\resumeProjectHeading}[2]{
    \\vspace{-2pt}\\item
    \\begin{tabular*}{0.97\\textwidth}{l@{\\extracolsep{\\fill}}r}
      \\small\\textbf{#1} & #2 \\\\
    \\end{tabular*}\\vspace{-7pt}
}

\\newcommand{\\resumeSkillHeading}[2]{
    \\itemsep -0.5em % Reduces the space between items
    \\parsep 0em     % Removes paragraph spacing between items
    \\item{\\textbf{\\small#1 }}{\\small#2}
}

\\newcommand{\\resumeWorkHeading}[5]{
    \\resumeSubHeadingListStart
        \\resumeSubheading{#1}{#2}{#3}{#4}
        #5
    \\resumeSubHeadingListEnd
}

\\newcommand{\\resumeOrganizationHeading}[4]{
  \\vspace{-2pt}\\item
    \\begin{tabular*}{0.97\\textwidth}[t]{l@{\\extracolsep{\\fill}}r}
      \\textbf{#1} & \\textit{\\small #2} \\\\
      \\textit{\\small#3}
    \\end{tabular*}\\vspace{-7pt}
}

\\newcommand{\\resumeAwardHeading}[2]{
    \\itemsep -0.5em % Reduces the space between items
    \\parsep 0em     % Removes paragraph spacing between items
    \\small{\\item{\\textbf{#1: }#2 }}
}

\\newcommand{\\resumeSubItem}[1]{\\resumeItem{#1}\\vspace{-4pt}}
\\renewcommand\\labelitemii{$\\vcenter{\\hbox{\\tiny$\\bullet$}}$}
\\newcommand{\\resumeSubHeadingListStart}{\\begin{itemize}[leftmargin=0.15in, label={}]}
\\newcommand{\\resumeSubHeadingListEnd}{\\end{itemize}}
\\newcommand{\\resumeItemListStart}{
    \\begin{itemize}
%    \\setlength{\\itemsep}{0pt}
%    \\setlength{\\parskip}{0pt}
    \\setlength{\\leftskip}{-10pt} % Adjust this value to reduce indent
}
\\newcommand{\\resumeItemListEnd}{\\end{itemize}\\vspace{-5pt}}

% New command for personal information
\\newcommand{\\personalInformation}[7]{
    \\begin{center}
        \\textbf{\\Huge \\MakeUppercase{\\scshape #1}} \\\\ \\vspace{3pt}
        \\small
        \\faMobile \\hspace{.5pt} \\href{mobile:#2}{#2}
        $|$
        \\faAt \\hspace{.5pt} \\href{mailto:#3}{#3}
        $|$
        \\faLinkedin \\hspace{.5pt} \\href{#4}{LinkedIn}
        $|$
        \\faGithub \\hspace{.5pt} \\href{#5}{GitHub}
        $|$
\t\\faGlobe \\hspace{.5pt} \\href{#6}{Website}
\t$|$
        \\faMapMarker \\hspace{.5pt} \\href{#7}{#7}
    \\end{center}
}

% Custom command for career summary
\\newcommand{\\careerSummary}[3]{%
  {A {#1} with {#2} years of experience {#3} }
}
"""

# Default cover letter preamble
DEFAULT_COVER_LETTER_PREAMBLE = """\\documentclass[12pt, letterpaper]{letter}
\\usepackage[utf8]{inputenc}
\\usepackage[T1]{fontenc}
\\usepackage{geometry}
\\usepackage{hyperref}
\\usepackage{xcolor}
\\usepackage{graphicx}
\\graphicspath{{.}}
\\usepackage{fontawesome5}
\\usepackage{lmodern}
\\pagenumbering{gobble}

% Hyperref setup
\\hypersetup{
    colorlinks=true,
    linkcolor=black,
    filecolor=black,
    urlcolor=black,
    citecolor=black,
    pdfborder={0 0 0}
}

% Geometry setup
\\geometry{
    top=0.8in,
    bottom=1in,
    left=1in,
    right=1in
}

% Font setup
\\renewcommand{\\familydefault}{\\rmdefault}
\\renewcommand{\\seriesdefault}{\\mddefault}
\\renewcommand{\\shapedefault}{\\updefault}

% Define personal details with FontAwesome icons
\\newcommand{\\personalinfo}[7]{
    \\begin{center}
        \\textbf{\\Huge \\MakeUppercase{\\scshape #1}} \\\\ \\vspace{2pt}
        {\\small\\raggedright  % Add raggedright to prevent line breaks
        \\makebox[\\textwidth][c]{%  Force content into a single line
        \\faMobile \\hspace{.5pt} \\href{mobile:#2}{#2}%
        \\hspace{1pt}$|$\\hspace{1pt}%
        \\faAt \\hspace{.5pt} \\href{mailto:#3}{#3}%
        \\hspace{1pt}$|$\\hspace{1pt}%
        \\faLinkedin \\hspace{.5pt} \\href{#4}{LinkedIn}%
        \\hspace{1pt}$|$\\hspace{1pt}%
        \\faGithub \\hspace{.5pt} \\href{#5}{GitHub}%
        \\hspace{1pt}$|$\\hspace{1pt}%
        \\faGlobe \\hspace{.5pt} \\href{#6}{Website}%
        \\hspace{1pt}$|$\\hspace{1pt}%
        \\faMapMarker \\hspace{.5pt} #7%
        }}
    \\end{center}
}

% Document spacing and alignment
\\setlength{\\parskip}{1em}
\\setlength{\\parindent}{0pt}
\\sloppy

% Justify paragraphs
\\newcommand{\\justifying}{\\leftskip=0pt \\rightskip=0pt}

\\begin{document}
\\begin{letter}{{{COMPANY_NAME}} \\\\ {{JOB_TITLE}}}

\\personalinfo{{{NAME}}}{{{PHONE}}}{{{EMAIL}}}{{{LINKEDIN}}}{{{GITHUB}}}{{{WEBSITE}}}{{{ADDRESS}}}

\\vspace{0.3cm}
\\justifying  % Enable justification for the letter content

{{COVER_LETTER_CONTENT}}

\\vspace{0.3cm}
\\includegraphics[width=1in]{signature.jpg}
\\newline
\\vspace{0.1cm}
\\today
\\end{letter}
\\end{document}"""

# Default resume template structure
DEFAULT_RESUME_TEMPLATE = """\\begin{document}

{personal_information}
{career_summary}
{skills}
{work_experience}
{education}
{projects}
{awards}
{publications}
{certifications}

\\end{document}"""

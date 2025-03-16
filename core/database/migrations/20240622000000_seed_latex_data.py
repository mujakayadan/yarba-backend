"""
Seed LaTeX Preambles and TexHeaders

Migration created at: 2024-06-22T00:00:00
"""

from datetime import datetime

from pymongo.database import Database

from core.database.migrations.migration_manager import Migration


class SeedLatexDataMigration(Migration):
    """
    Seed the Preamble and TexHeader collections with initial data.
    """

    def upgrade(self) -> None:
        """Apply the migration."""
        # Seed Preambles
        preambles = [
            {
                "name": "default",
                "type": "resume_preamble",
                "content": "\\documentclass[letterpaper,11pt]{article}\n\\usepackage{latexsym}\n\\usepackage[empty]{fullpage}\n\\usepackage{titlesec}\n\\usepackage{marvosym}\n\\usepackage[usenames,dvipsnames]{color}\n\\usepackage{verbatim}\n\\usepackage{enumitem}\n\\usepackage[hidelinks]{hyperref}\n\\usepackage{fancyhdr}\n\\usepackage[english]{babel}\n\\usepackage{tabularx}\n\\usepackage{hyphenat}\n\\usepackage{fontawesome}\n\\usepackage{seqsplit}\n\\usepackage[T1]{fontenc}\n\\usepackage[utf8x]{inputenc}\n\\usepackage{lmodern,textcomp}\n\\usepackage{bookmark}\n\n\\pagestyle{fancy}\n\\fancyhf{} % clear all header and footer fields\n\\fancyfoot{}\n\\renewcommand{\\headrulewidth}{0pt}\n\\renewcommand{\\footrulewidth}{0pt}\n\n% Adjust margins\n\\addtolength{\\oddsidemargin}{-0.5in}\n\\addtolength{\\evensidemargin}{-0.5in}\n\\addtolength{\\textwidth}{1in}\n\\addtolength{\\topmargin}{-.5in}\n\\addtolength{\\textheight}{1.0in}\n\n\\urlstyle{same}\n\n\\raggedbottom\n\\raggedright\n\\setlength{\\tabcolsep}{0in}\n\\setlength{\\footskip}{4.08003pt}\n\n\n% Sections formatting\n\\titleformat{\\section}{\n  \\vspace{-4pt}\\scshape\\raggedright\\large\n}{}{0em}{}[\\color{black}\\titlerule \\vspace{-5pt}]\n\n% Ensure that generated pdf is machine readable/ATS parsable\n\\pdfgentounicode=1\n\n%-------------------------\n% Custom commands\n\n\\newcommand{\\resumeItem}[1]{\n  \\item\\small{\n    {#1 \\vspace{-2pt}}\n  }\n}\n\n\n\\newcommand{\\resumeSubheading}[4]{\n  \\vspace{-2pt}\\item\n    \\begin{tabular*}{0.97\\textwidth}[t]{l@{\\extracolsep{\\fill}}r}\n      \\textbf{#1} & #2 \\\\\n      \\textit{\\small#3} & \\textit{\\small #4} \\\\\n    \\end{tabular*}\\vspace{-7pt}\n}\n\n\\newcommand{\\resumeVolunteeringHeading}[4]{\n  \\vspace{-2pt}\\item\n    \\begin{tabular*}{0.97\\textwidth}[t]{l@{\\extracolsep{\\fill}}r}\n      \\textbf{#1} & #2 \\\\\n      \\textit{\\small#3} & \\textit{\\small #4} \\\\\n    \\end{tabular*}\\vspace{-7pt}\n}\n\n\\newcommand{\\resumeSubSubheading}[2]{\n    \\vspace{-2pt}\\item\n    \\begin{tabular*}{0.97\\textwidth}{l@{\\extracolsep{\\fill}}r}\n      \\textit{\\small#1} & \\textit{\\small #2} \\\\\n    \\end{tabular*}\\vspace{-7pt}\n}\n\n\n\\newcommand{\\resumeEducationHeading}[5]{\n  \\vspace{-2pt}\\item\n    \\begin{tabular*}{0.97\\textwidth}[t]{l@{\\extracolsep{\\fill}}r}\n      \\textbf{#1} & #2 \\\\\n      \\textit{\\small#3} & \\textit{\\small #4} \\\\\n    \\end{tabular*}\\vspace{1pt} \\\\\n    \\textit{\\small#5} \\\\\n}\n\n\n\\newcommand{\\resumeProjectHeading}[2]{\n    \\vspace{-2pt}\\item\n    \\begin{tabular*}{0.97\\textwidth}{l@{\\extracolsep{\\fill}}r}\n      \\small\\textbf{#1} & #2 \\\\\n    \\end{tabular*}\\vspace{-7pt}\n}\n\n\\newcommand{\\resumeSkillHeading}[2]{\n    \\itemsep -0.5em % Reduces the space between items\n    \\parsep 0em     % Removes paragraph spacing between items\n    \\item{\\textbf{\\small#1 }}{\\small#2}\n}\n\n\\newcommand{\\resumeWorkHeading}[5]{\n    \\resumeSubHeadingListStart\n        \\resumeSubheading{#1}{#2}{#3}{#4}\n        #5\n    \\resumeSubHeadingListEnd\n}\n\n\\newcommand{\\resumeOrganizationHeading}[4]{\n  \\vspace{-2pt}\\item\n    \\begin{tabular*}{0.97\\textwidth}[t]{l@{\\extracolsep{\\fill}}r}\n      \\textbf{#1} & \\textit{\\small #2} \\\\\n      \\textit{\\small#3}\n    \\end{tabular*}\\vspace{-7pt}\n}\n\n\\newcommand{\\resumeAwardHeading}[2]{\n    \\itemsep -0.5em % Reduces the space between items\n    \\parsep 0em     % Removes paragraph spacing between items\n    \\small{\\item{\\textbf{#1: }#2 }}\n}\n\n\\newcommand{\\resumeSubItem}[1]{\\resumeItem{#1}\\vspace{-4pt}}\n\\renewcommand\\labelitemii{$\\vcenter{\\hbox{\\tiny$\\bullet$}}$}\n\\newcommand{\\resumeSubHeadingListStart}{\\begin{itemize}[leftmargin=0.15in, label={}]}\n\\newcommand{\\resumeSubHeadingListEnd}{\\end{itemize}}\n\\newcommand{\\resumeItemListStart}{\n    \\begin{itemize}\n%    \\setlength{\\itemsep}{0pt}\n%    \\setlength{\\parskip}{0pt}\n    \\setlength{\\leftskip}{-10pt} % Adjust this value to reduce indent\n}\n\\newcommand{\\resumeItemListEnd}{\\end{itemize}\\vspace{-5pt}}\n\n% New command for personal information\n\\newcommand{\\personalinfo}[7]{\n    \\begin{center}\n        \\textbf{\\Huge \\MakeUppercase{\\scshape #1}} \\\\ \\vspace{3pt}\n        \\small\n        \\faMobile \\hspace{.5pt} \\href{mobile:#2}{#2}\n        $|$\n        \\faAt \\hspace{.5pt} \\href{mailto:#3}{#3}\n        $|$\n        \\faLinkedin \\hspace{.5pt} \\href{#4}{LinkedIn}\n        $|$\n        \\faGithub \\hspace{.5pt} \\href{#5}{GitHub}\n        $|$\n\t\\faGlobe \\hspace{.5pt} \\href{#6}{Website}\n\t$|$\n        \\faMapMarker \\hspace{.5pt} \\href{#7}{#7}\n    \\end{center}\n}\n\n% Custom command for career summary\n\\newcommand{\\careerSummary}[3]{%\n  {A {#1} with {#2} years of experience {#3} }\n}",
                "is_default": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
            {
                "name": "default",
                "type": "cover_letter_preamble",
                "content": "\\documentclass[12pt, letterpaper]{letter}\n\\usepackage[utf8]{inputenc}\n\\usepackage[T1]{fontenc}\n\\usepackage{geometry}\n\\usepackage{hyperref}\n\\usepackage{xcolor}\n\\usepackage{graphicx}\n\\graphicspath{{.}}\n\\usepackage{fontawesome5} \n\\usepackage{lmodern}\n\\pagenumbering{gobble}\n\n% Hyperref setup\n\\hypersetup{\n    colorlinks=true,\n    linkcolor=black,\n    filecolor=black,\n    urlcolor=black,\n    citecolor=black,\n    pdfborder={0 0 0}\n}\n\n% Geometry setup\n\\geometry{\n    top=0.8in,\n    bottom=1in,\n    left=1in,\n    right=1in\n}\n\n% Font setup\n\\renewcommand{\\familydefault}{\\rmdefault}\n\\renewcommand{\\seriesdefault}{\\mddefault}\n\\renewcommand{\\shapedefault}{\\updefault}\n\n% Define personal details with FontAwesome icons\n\\newcommand{\\personalinfo}[7]{\n    \\begin{center}\n        \\textbf{\\Huge \\MakeUppercase{\\scshape #1}} \\\\ \\vspace{2pt}\n        {\\small\\raggedright  % Add raggedright to prevent line breaks\n        \\makebox[\\textwidth][c]{%  Force content into a single line\n        \\faMobile \\hspace{.5pt} \\href{mobile:#2}{#2}%\n        \\hspace{1pt}$|$\\hspace{1pt}%\n        \\faAt \\hspace{.5pt} \\href{mailto:#3}{#3}%\n        \\hspace{1pt}$|$\\hspace{1pt}%\n        \\faLinkedin \\hspace{.5pt} \\href{#4}{LinkedIn}%\n        \\hspace{1pt}$|$\\hspace{1pt}%\n        \\faGithub \\hspace{.5pt} \\href{#5}{GitHub}%\n        \\hspace{1pt}$|$\\hspace{1pt}%\n        \\faGlobe \\hspace{.5pt} \\href{#6}{Website}%\n        \\hspace{1pt}$|$\\hspace{1pt}%\n        \\faMapMarker \\hspace{.5pt} #7%\n        }}\n    \\end{center}\n}\n\n% Document spacing and alignment\n\\setlength{\\parskip}{1em}\n\\setlength{\\parindent}{0pt}\n\\sloppy\n\n% Justify paragraphs\n\\newcommand{\\justifying}{\\leftskip=0pt \\rightskip=0pt}\n\n\\begin{document}\n\\begin{letter}{{{COMPANY_NAME}} \\\\ {{JOB_TITLE}}}\n\n\\personalinfo{{{NAME}}}{{{PHONE}}}{{{EMAIL}}}{{{LINKEDIN}}}{{{GITHUB}}}{{{WEBSITE}}}{{{ADDRESS}}}\n\n\\vspace{0.3cm}\n\\justifying  % Enable justification for the letter content\n\n{{COVER_LETTER_CONTENT}}\n\n\\vspace{0.3cm}\n\\includegraphics[width=1in]{signature.jpg}\n\\newline\n\\vspace{0.1cm}\n\\today\n\\end{letter}\n\\end{document}",
                "is_default": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
        ]

        # Insert preambles if they don't exist
        for preamble in preambles:
            existing = self.db.preambles.find_one(
                {"name": preamble["name"], "type": preamble["type"]}
            )
            if not existing:
                self.db.preambles.insert_one(preamble)

        # Seed TexHeaders
        tex_headers = [
            {
                "name": "awards",
                "content": "\\section{{Awards \\& Achievements}}\n\\resumeSubHeadingListStart\n{awards_content}\n\\resumeSubHeadingListEnd\n",
                "category": "resume",
                "is_default": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
            {
                "name": "award_item",
                "content": "\\resumeAwardHeading{{{name}}}{{{explanation}}}\n",
                "category": "resume",
                "is_default": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
            {
                "name": "career_summary",
                "content": "\\section{{Career Summary}}\n\\careerSummary{{{job_title}}}{{{years_of_experience}}}{{{summary}}}\n\n\n\n",
                "category": "resume",
                "is_default": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
            {
                "name": "education",
                "content": "\\section{{Education}}\n\\vspace{{3pt}}\n{education_content}\n",
                "category": "resume",
                "is_default": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
            {
                "name": "education_item",
                "content": "\\resumeEducationHeading\n{{{university}}}\n{{{location}}}\n{{{degree}}}\n{{{time}}}\n{{{key_courses}}}\n",
                "category": "resume",
                "is_default": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
            {
                "name": "muja_kayadan_resume",
                "content": "%-------------------------\n% Resume in Latex\n% Author: Muja Kayadan\n% License: MIT\n%------------------------\n\n\\documentclass[letterpaper,11pt]{article}\n%\\documentclass{article}\n\\input{preamble}\n\n\\begin{document}\n\n\\input{personal_information}\n\\input{career_summary}\n\\input{skills}\n\\input{work_experience}\n\\input{education}\n\\input{projects}\n\\input{awards}\n\\input{publications}\n\n\\end{document}\n",
                "category": "resume",
                "is_default": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
            {
                "name": "personal_information",
                "content": "\\personalinfo{{{name}}}{{{phone}}}{{{email}}}{{{LinkedIn}}}{{{GitHub}}}{{{website}}}{{{address}}}\n",
                "category": "resume",
                "is_default": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
            {
                "name": "projects",
                "content": "\\section{{Projects}}\n{projects_content}\n",
                "category": "resume",
                "is_default": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
            {
                "name": "project_item",
                "content": "\\resumeProjectHeading\n{{{name_and_tech}}}\n{{{date}}}\n\\resumeItemListStart\n{bullet_points}\n\\resumeItemListEnd\n",
                "category": "resume",
                "is_default": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
            {
                "name": "publications",
                "content": "\\section{{Publications}}\n\\vspace{{3pt}}\n\\resumeSubHeadingListStart\n{publications_content}\n\\resumeSubHeadingListEnd\n",
                "category": "resume",
                "is_default": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
            {
                "name": "publication_item",
                "content": "\\resumeProjectHeading\n{{\\textbf{{{name}}}}}{{{time}}}\n\\resumeItem{{\\href{{{link}}}{{\\color{{blue}}{publisher}}}}}\n\n",
                "category": "resume",
                "is_default": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
            {
                "name": "skills",
                "content": "\\section{{Skills}}\n\\resumeSubHeadingListStart\n{skills_content}\n\\resumeSubHeadingListEnd\n",
                "category": "resume",
                "is_default": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
            {
                "name": "work_experience",
                "content": "\\section{{Work Experience}}\n\\vspace{{3pt}}\n\\resumeSubHeadingListStart\n{experience_content}\n\\resumeSubHeadingListEnd\n",
                "category": "resume",
                "is_default": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
            {
                "name": "work_experience_item",
                "content": "\\resumeSubheading\n    {{{job_title}}}{{{time}}}\n    {{{company}}}{{{location}}}\n    \\resumeItemListStart\n{responsibilities}\n    \\resumeItemListEnd\n\n",
                "category": "resume",
                "is_default": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
        ]

        # Insert tex_headers if they don't exist
        for header in tex_headers:
            existing = self.db.tex_headers.find_one(
                {"name": header["name"], "category": header["category"]}
            )
            if not existing:
                self.db.tex_headers.insert_one(header)

    def downgrade(self) -> None:
        """Revert the migration."""
        # Remove the seeded data
        self.db.preambles.delete_many({"name": "default"})
        self.db.tex_headers.delete_many({"category": "resume"})

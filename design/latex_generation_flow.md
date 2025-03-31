# LaTeX Generation Flow

This document outlines the flow of data through the LaTeX generation system, from database to PDF output. The system integrates with LLM-generated content structured as JSON and transforms it into LaTeX documents.

## System Architecture Overview

```mermaid
graph TD
    DB[(MongoDB)]
    LLM[LLM Service]
    RS[Resume Service]
    RGS[Resume Generation Service]
    LS[LaTeX Service]
    JTL[JSON to LaTeX]
    COMP[LaTeX Compiler]
    PDF[PDF Document]

    DB -->|Templates,\nHeaders,\nPreambles| LS
    DB -->|Resume,\nProfile,\nPortfolio Data| RGS

    LLM -->|JSON Schema\nResponses| RGS

    RGS -->|Section Content| LS
    LS -->|JSON Data| JTL
    JTL -->|LaTeX Sections| LS
    LS -->|Complete LaTeX| COMP
    COMP -->|Compiled Document| PDF

    style DB fill:#f9f,stroke:#333,stroke-width:2px
    style LLM fill:#bbf,stroke:#333,stroke-width:2px
    style PDF fill:#bfb,stroke:#333,stroke-width:2px
```

## Detailed Data Flow

```mermaid
sequenceDiagram
    participant DB as MongoDB
    participant RGS as Resume Generation Service
    participant LLM as LLM Service
    participant LS as LaTeX Service
    participant JTL as JSON to LaTeX
    participant LC as LaTeX Compiler
    participant FS as File System

    RGS->>DB: Get resume data (profile, portfolio)
    DB-->>RGS: Resume, profile, portfolio objects

    Note over RGS,LLM: For each section (if not hardcoded)
    RGS->>LLM: Generate section content with JSON schema
    LLM-->>RGS: JSON structured content

    RGS->>LS: Generate LaTeX (resume, profile, content)

    LS->>DB: Get templates, headers, preambles
    DB-->>LS: LaTeX template components

    Note over LS,JTL: For each content section
    LS->>JTL: Convert JSON to LaTeX for section
    JTL-->>LS: LaTeX-formatted section

    LS->>LC: Compile content to PDF
    LC->>FS: Write temporary .tex file
    LC->>LC: Run pdflatex compiler
    LC->>FS: Read compiled PDF
    LC-->>LS: PDF binary content

    LS-->>RGS: PDF document
```

## JSON Schema to LaTeX Conversion

```mermaid
flowchart TD
    A[JSON Schema Input] --> B{Parse JSON}
    B -->|Valid JSON| C[Identify Section Type]
    B -->|Invalid/String| D[Use as raw text]

    C --> E{Section Type}
    E -->|Personal Info| F[Format for personalinfo command]
    E -->|Skills| G[Format for resumeSkillHeading]
    E -->|Work Experience| H[Format for resumeSubheading]
    E -->|Education| I[Format for resumeEducationHeading]
    E -->|Projects| J[Format for resumeProjectHeading]
    E -->|Awards| K[Format for resumeAwardHeading]
    E -->|Publications| L[Format for citations]
    E -->|Career Summary| M[Format for careerSummary]

    F --> N[Sanitize LaTeX]
    G --> N
    H --> N
    I --> N
    J --> N
    K --> N
    L --> N
    M --> N
    D --> N

    N --> O[LaTeX Output]
```

## Components Interaction

```mermaid
classDiagram
    class ResumeGenerationService {
        +generate_resume_content()
        +generate_latex()
        +compile_pdf()
        -_process_section()
    }

    class LLMService {
        +generate_section()
        +get_structured_completion()
    }

    class LatexService {
        +generate_resume_latex()
        +compile_latex_to_pdf()
        +get_template()
        +get_header()
        +get_preamble()
    }

    class JSONToLatexUtility {
        +process_content_by_section()
        +process_personal_information()
        +process_skills()
        +process_work_experience()
        +process_education()
    }

    class LatexCompiler {
        +generate_tex_content()
        +compile_pdf()
    }

    class ResumeCompiler {
        +generate_tex_content()
    }

    ResumeGenerationService --> LLMService: uses
    ResumeGenerationService --> LatexService: uses
    LatexService --> JSONToLatexUtility: uses
    LatexService --> ResumeCompiler: uses
    LatexCompiler <|-- ResumeCompiler: inherits
```

## LaTeX Compilation Process

```mermaid
graph TD
    A[LaTeX Content] --> B[LatexService.compile_latex_to_pdf]
    B --> C{Is Cover Letter?}

    C -->|Yes| D[CoverLetterCompiler]
    C -->|No| E[ResumeCompiler]

    D --> F[Create Temp Directory]
    E --> F

    F --> G[Write .tex File]
    G --> H[Set Compiler Options]
    H --> I[Run pdflatex]
    I --> J{Compilation Success?}

    J -->|Yes| K[Read PDF Content]
    J -->|No| L[Parse Log for Errors]

    L --> M[Raise Exception]
    K --> N[Return PDF Bytes]
```

## Database Structure for LaTeX Templates

```mermaid
erDiagram
    Preamble {
        string name
        string type
        string content
        boolean is_default
    }

    TexHeader {
        string name
        string category
        string content
        boolean is_default
    }


    Resume {
        ObjectId id
        ObjectId user_id
        ObjectId profile_id
        ObjectId portfolio_id
        string title
        Object content
        Object personal_information
    }

    Profile {
        ObjectId id
        ObjectId user_id
        Object personal_information
        Object preferences
    }

    Preamble ||--o{ Resume : uses
    TexHeader ||--o{ Resume : uses
    Resume }|--|| Profile : references
```

## Example Flow: From LLM Response to LaTeX

Here's an example showing how a work experience section flows through the system:

```mermaid
graph TD
    subgraph "LLM Response (JSON)"
        A["{
            'work_experience': [
                {
                    'job_title': 'Software Engineer',
                    'company': 'Tech Corp',
                    'location': 'San Francisco, CA',
                    'time': '2020-2023',
                    'responsibilities': [
                        'Developed API',
                        'Optimized database'
                    ]
                }
            ]
        }"]
    end

    subgraph "JSON to LaTeX Conversion"
        B["process_work_experience()"]
        C["\\resumeSubHeadingListStart
           \\resumeSubheading{Software Engineer}{2020-2023}{Tech Corp}{San Francisco, CA}
           \\resumeItemListStart
             \\resumeItem{Developed API}
             \\resumeItem{Optimized database}
           \\resumeItemListEnd
         \\resumeSubHeadingListEnd"]
    end

    subgraph "Template Integration"
        D["\\section{Work Experience}
           \\vspace{3pt}
           ... LaTeX from previous step ..."]
    end

    A --> B
    B --> C
    C --> D
```

## Error Handling Flow

```mermaid
graph TD
    A[Process Section] --> B{JSON Parsing Error?}
    B -->|Yes| C[Log Error]
    C --> D[Fallback to Text]
    D --> F[Sanitize LaTeX]

    B -->|No| E{Field Missing?}
    E -->|Yes| G[Use Default Value]
    E -->|No| H[Process Normally]

    G --> F
    H --> F

    F --> I[Return LaTeX Code]
```

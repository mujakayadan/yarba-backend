# PDF Generation Implementation Guide

This document provides guidance on implementing PDF generation and preview functionality in the frontend application.

## Overview

The ResumeBuilderTeX application uses LaTeX to generate professional-quality PDF documents for resumes and cover letters. The frontend needs to interface with the backend API to request PDF generation and then display or download the resulting files.

## PDF Generation Flow

1. User creates or updates a resume/cover letter document
2. Frontend requests PDF generation via the API
3. Backend processes the request and generates a PDF using LaTeX
4. Frontend receives the PDF data or a URL to download the generated file
5. Frontend displays the PDF or provides a download option

## API Endpoints for PDF Generation

### Resume PDF Generation

```
GET /api/v1/resumes/{resume_id}/pdf
```

Query parameters:
- `timeout`: PDF generation timeout in seconds (default: 30, min: 5, max: 60)

Response:
- Content-Type: `application/pdf`
- Body: Binary PDF data

### Cover Letter PDF Generation

```
GET /api/v1/cover-letters/{cover_letter_id}/pdf
```

Query parameters:
- `timeout`: PDF generation timeout in seconds (default: 30, min: 5, max: 60)

Response:
- Content-Type: `application/pdf`
- Body: Binary PDF data

## Implementation in Frontend

### Requesting PDF Generation

```typescript
const generateResumePdf = async (resumeId: string, timeout: number = 30): Promise<Blob> => {
  const token = getToken();

  if (!token) {
    throw new Error('No authentication token found');
  }

  try {
    const response = await fetch(`/api/v1/resumes/${resumeId}/pdf?timeout=${timeout}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      if (response.headers.get('Content-Type')?.includes('application/json')) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'PDF generation failed');
      } else {
        throw new Error(`PDF generation failed with status: ${response.status}`);
      }
    }

    // Return the response as a blob for PDF data
    return await response.blob();
  } catch (error) {
    console.error('PDF generation error:', error);
    throw error;
  }
};

// Similar function for cover letters
const generateCoverLetterPdf = async (coverLetterId: string, timeout: number = 30): Promise<Blob> => {
  // Implementation similar to generateResumePdf but with different endpoint
};
```

### Displaying PDFs in the Browser

You can use libraries like `react-pdf` or browser built-in PDF viewing capabilities to display PDFs:

#### Using URL.createObjectURL

```tsx
import React, { useState } from 'react';

interface PdfViewerProps {
  resumeId: string;
}

const PdfViewer: React.FC<PdfViewerProps> = ({ resumeId }) => {
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const loadPdf = async () => {
    setLoading(true);
    setError(null);

    try {
      const pdfBlob = await generateResumePdf(resumeId);

      // Create a URL for the PDF blob
      const url = URL.createObjectURL(pdfBlob);
      setPdfUrl(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load PDF');
    } finally {
      setLoading(false);
    }
  };

  // Clean up object URL when component unmounts
  React.useEffect(() => {
    return () => {
      if (pdfUrl) {
        URL.revokeObjectURL(pdfUrl);
      }
    };
  }, [pdfUrl]);

  return (
    <div className="pdf-viewer">
      {loading && <div className="loading">Loading PDF...</div>}
      {error && <div className="error">{error}</div>}
      {pdfUrl && (
        <div className="pdf-container">
          <iframe
            src={pdfUrl}
            title="Resume PDF"
            width="100%"
            height="600px"
            style={{ border: 'none' }}
          />
          <a href={pdfUrl} download={`resume-${resumeId}.pdf`}>
            Download PDF
          </a>
        </div>
      )}

      {!loading && !pdfUrl && (
        <button onClick={loadPdf}>Generate and View PDF</button>
      )}
    </div>
  );
};

export default PdfViewer;
```

#### Using react-pdf

First, install the library:

```bash
npm install @react-pdf/renderer
# or
yarn add @react-pdf/renderer
```

Then implement the viewer:

```tsx
import React, { useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';

// Set up the worker for PDF.js
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

interface PdfDocumentViewerProps {
  resumeId: string;
}

const PdfDocumentViewer: React.FC<PdfDocumentViewerProps> = ({ resumeId }) => {
  const [pdfBlob, setPdfBlob] = useState<Blob | null>(null);
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const loadPdf = async () => {
    setLoading(true);
    setError(null);

    try {
      const blob = await generateResumePdf(resumeId);
      setPdfBlob(blob);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load PDF');
    } finally {
      setLoading(false);
    }
  };

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setPageNumber(1);
  };

  return (
    <div className="pdf-document-viewer">
      {loading && <div className="loading">Loading PDF...</div>}
      {error && <div className="error">{error}</div>}

      {pdfBlob && (
        <div>
          <Document
            file={pdfBlob}
            onLoadSuccess={onDocumentLoadSuccess}
            onLoadError={(err) => setError(err.message)}
          >
            <Page pageNumber={pageNumber} />
          </Document>

          <div className="pdf-controls">
            <p>
              Page {pageNumber} of {numPages}
            </p>
            <button
              disabled={pageNumber <= 1}
              onClick={() => setPageNumber(pageNumber - 1)}
            >
              Previous
            </button>
            <button
              disabled={numPages !== null && pageNumber >= numPages}
              onClick={() => setPageNumber(pageNumber + 1)}
            >
              Next
            </button>
          </div>

          <a
            href={URL.createObjectURL(pdfBlob)}
            download={`resume-${resumeId}.pdf`}
            className="download-button"
          >
            Download PDF
          </a>
        </div>
      )}

      {!loading && !pdfBlob && (
        <button onClick={loadPdf}>Generate and View PDF</button>
      )}
    </div>
  );
};

export default PdfDocumentViewer;
```

## Handling PDF Generation Errors

PDF generation can fail for various reasons, such as:

1. Invalid LaTeX syntax in the document
2. LaTeX compiler errors
3. Timeout during PDF generation
4. Server errors

The API provides debugging endpoints to help diagnose PDF generation issues:

```
POST /api/v1/resumes/{resume_id}/debug-pdf
```

Response:
```json
{
  "success": false,
  "error": "LaTeX compilation failed",
  "latex_log": "...",
  "steps_completed": ["template_loading", "content_generation"],
  "steps_failed": ["latex_compilation"],
  "compilation_output": "..."
}
```

Implement a function to call this debugging endpoint:

```typescript
const debugResumePdf = async (resumeId: string): Promise<any> => {
  const token = getToken();

  if (!token) {
    throw new Error('No authentication token found');
  }

  try {
    const response = await fetch(`/api/v1/resumes/${resumeId}/debug-pdf`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Debug request failed');
    }

    return await response.json();
  } catch (error) {
    console.error('PDF debug error:', error);
    throw error;
  }
};
```

Use this function to show detailed error information to the user when PDF generation fails, helping them understand and potentially fix the issues.

## Performance Considerations

1. **Loading States**: Always show loading indicators during PDF generation
2. **Caching**: Cache generated PDFs when possible to reduce server load
3. **Timeout Handling**: Provide appropriate feedback for long-running PDF generations
4. **Progressive Loading**: Display PDFs as they load, especially for larger documents

## UI/UX Best Practices

1. **Preview Button**: Separate PDF generation from the document editing workflow
2. **Error Messages**: Show user-friendly error messages with potential solutions
3. **Download Options**: Provide easy download buttons for generated PDFs
4. **Mobile Support**: Ensure PDF viewing works on mobile devices
5. **Printing**: Include print options for generated PDFs

## Testing PDF Generation

1. Test with various resume/cover letter templates
2. Test with different content lengths and formats
3. Test error scenarios and recovery
4. Test on different browsers and devices
5. Test download functionality

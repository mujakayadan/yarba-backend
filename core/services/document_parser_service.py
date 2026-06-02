"""Service for parsing documents (PDF, DOCX) into Portfolio objects."""

import io
from typing import Any

from docx import Document as DocxDocument
from fastapi import UploadFile
from pdfminer.high_level import extract_text as extract_text_from_pdf

from config.logging_config import get_logger
from core.schemas.portfolio_llm_schemas import PortfolioLLMSchema
from core.services.llm_service import LLMService
from prompts.portfolio_parser_prompts import MapDocumentToPortfolioPrompt

logger = get_logger(__name__)


class DocumentParserService:
    """Service to parse uploaded documents (PDF, DOCX)
    and convert them into a data dictionary suitable for creating a Portfolio model,
    using an LLM for mapping.
    """

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        self.map_to_portfolio_prompt = MapDocumentToPortfolioPrompt()

    async def _extract_text_from_file(
        self, file_content: bytes, content_type: str
    ) -> str:
        """Extracts text from PDF or DOCX file content."""
        text_content = ""
        try:
            if content_type == "application/pdf":
                text_content = extract_text_from_pdf(io.BytesIO(file_content))
                logger.info("Successfully extracted text from PDF.")
            elif (
                content_type
                == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ):
                doc = DocxDocument(io.BytesIO(file_content))
                full_text = [para.text for para in doc.paragraphs]
                text_content = "\n".join(full_text)
                logger.info("Successfully extracted text from DOCX.")
            else:
                logger.warning(
                    f"Unsupported content type for text extraction: {content_type}"
                )
                raise ValueError(
                    f"Unsupported file type: {content_type}. Only PDF and DOCX are supported for text extraction."
                )
        except Exception as e:
            logger.error(
                f"Error extracting text from file ({content_type}): {e}", exc_info=True
            )
            raise ValueError(f"Failed to extract text from the document: {str(e)}")
        return text_content

    async def _map_text_to_portfolio_dict_via_llm(
        self, document_text: str, user_id_str: str, file_name: str
    ) -> dict[str, Any]:
        """Uses LLMService to map extracted text to a dictionary matching PortfolioLLMSchema."""
        logger.info(
            f"Attempting to map extracted text from '{file_name}' to Portfolio structure via LLM for user {user_id_str}."
        )

        try:
            prompt_text = self.map_to_portfolio_prompt.format(
                document_text=document_text
            )
            logger.debug(f"Prepared prompt for LLM (length: {len(prompt_text)} chars).")

            (
                llm_output_model,
                llm_response,
            ) = await self.llm_service.get_structured_completion(
                prompt=prompt_text,
                schema_model=PortfolioLLMSchema,
                user_id=user_id_str,
                tags=[
                    "portfolio_parsing_to_llm_schema",
                    f"user_id:{user_id_str}",
                    f"file:{file_name}",
                ],
                fallback_to_text=False,
            )

            if isinstance(llm_output_model, PortfolioLLMSchema):
                logger.info(
                    f"Successfully received structured PortfolioLLMSchema from LLM for user {user_id_str} (file: '{file_name}')."
                )
                portfolio_dict = llm_output_model.model_dump(exclude_none=True)

                portfolio_dict.pop("user_id", None)
                portfolio_dict.pop("id", None)
                portfolio_dict.pop("created_at", None)
                portfolio_dict.pop("updated_at", None)

                return portfolio_dict
            else:
                logger.error(
                    f"LLM did not return a valid PortfolioLLMSchema instance for user {user_id_str} (file: '{file_name}'). "
                    f"Type received: {type(llm_output_model)}. "
                    f"Content: {str(llm_output_model)[:500]}..."
                )
                error_detail = (
                    "LLM failed to produce valid Portfolio structure using LLM schema."
                )
                if (
                    llm_response
                    and hasattr(llm_response, "choices")
                    and llm_response.choices
                ):
                    message_content = llm_response.choices[0].message.content
                    if message_content:
                        error_detail += f" LLM Message: {message_content[:200]}"
                raise ValueError(error_detail)

        except Exception as e:
            logger.error(
                f"Error mapping text to Portfolio dict via LLM for user {user_id_str} (file: '{file_name}'): {e}",
                exc_info=True,
            )
            raise

    async def parse_to_portfolio_data(
        self, file: UploadFile, user_id: str
    ) -> dict[str, Any]:
        """Parses uploaded file, extracts text, and maps text to Portfolio data dict using LLM."""
        try:
            logger.info(
                f"Starting text extraction for file: {file.filename} for user_id: {user_id}"
            )
            file_content = await file.read()

            if not file.content_type:
                logger.error(f"File {file.filename} is missing content_type.")
                raise ValueError(
                    "File content type is missing, cannot determine parser."
                )

            extracted_text = await self._extract_text_from_file(
                file_content, file.content_type
            )

            if not extracted_text.strip():
                logger.error("Extracted text is empty after parsing.")
                raise ValueError(
                    "Could not extract any text from the provided document."
                )

            logger.info(f"Successfully extracted text from document {file.filename}.")

            portfolio_data_dict = await self._map_text_to_portfolio_dict_via_llm(
                extracted_text, user_id, file.filename or "unknown"
            )
            return portfolio_data_dict

        except ValueError as ve:
            logger.error(
                f"ValueError during portfolio data parsing for {file.filename}: {ve}",
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error during document parsing for {file.filename}: {e}",
                exc_info=True,
            )
            raise ValueError(
                f"An unexpected error occurred during document processing: {str(e)}"
            )
        finally:
            if file:
                await file.close()
                logger.info(f"Closed uploaded file: {file.filename}")


# Removed old __main__ block as it was for docling and needs complete rework for new method.

# For instantiation in API router, DocumentParserService now needs LLMService.
# The LLMService itself needs ProfileRepository.
# Example of how dependencies might be set up:
# profile_repo = ProfileRepository() # This would come from a dependency injector
# llm_serv = LLMService(profile_repository=profile_repo)
# doc_parser_serv = DocumentParserService(llm_service=llm_serv)

# Example usage (for testing locally, not part of the service usually)
# if __name__ == "__main__":
#     async def main():
#         # This is a mock UploadFile for testing.
#         # In a real scenario, this would come from an HTTP request.
#         class MockUploadFile:
#             def __init__(self, filename, content_type, content):
#                 self.filename = filename
#                 self.content_type = content_type
#                 self._content = content
#             async def read(self):
#                 return self._content
#             async def close(self):
#                 pass

#         # Create a dummy PDF or DOCX file for testing (e.g., dummy.pdf)
#         # For example, create a simple text file and save it as dummy.pdf (though it won't be a real PDF)
#         # or use an actual small PDF/DOCX file.
#         try:
#             with open("dummy.pdf", "wb") as f: # Create a dummy pdf file
#                 # A very simple PDF content (not a real PDF, just for the test to run)
#                 # For real testing, use an actual PDF file.
#                 f.write(b"%PDF-1.4\n%test\n%%EOF")

#             with open("dummy.pdf", "rb") as f_rb:
#                 mock_file_content = f_rb.read()

#             mock_file = MockUploadFile(filename="dummy.pdf", content_type="application/pdf", content=mock_file_content)
#             parser_service = DocumentParserService()

#             # A mock user_id (in a real scenario, this should be a PydanticObjectId)
#             mock_user_id_str = "60c72b2f9b1d8c001f8e4a3c" # Example ObjectId string

#             try:
#                 # This will raise NotImplementedError as expected for now
#                 portfolio_result = await parser_service.parse_to_portfolio(mock_file, user_id=mock_user_id_str)
#                 print("Portfolio parsing (mocked result):", portfolio_result)
#             except NotImplementedError as nie:
#                 print(f"Caught expected error: {nie}")
#             except Exception as e:
#                 print(f"An error occurred during mock parsing: {e}")
#             finally:
#                 if Path("dummy.pdf").exists():
#                     Path("dummy.pdf").unlink()
#                 if Path("temp_dummy.pdf").exists(): # ensure temp file is also cleaned up
#                     Path("temp_dummy.pdf").unlink()


#         except FileNotFoundError:
#             print("Please create a 'dummy.pdf' or 'dummy.docx' file in the root for testing this script.")
#         except Exception as e:
#             print(f"An error occurred: {e}")

#     import asyncio
#     asyncio.run(main())

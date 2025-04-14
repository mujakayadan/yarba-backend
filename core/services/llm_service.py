"""Service for LLM operations using LiteLLM as an abstraction layer."""

import asyncio
from typing import Any, Dict, List, Optional, Tuple, Type, Union

import litellm
from beanie.odm.fields import PydanticObjectId
from litellm import acompletion, get_supported_openai_params, supports_response_schema
from pydantic import BaseModel

from config.logging_config import get_logger
from config.settings import settings
from core.models.profile import Profile
from core.repositories.profile_repository import ProfileRepository
from core.services.prompt_service import PromptService

logger = get_logger(__name__)


class LLMService:
    """
    Service for handling LLM operations using LiteLLM as an abstraction layer.

    This service provides a unified interface to multiple LLM providers
    and handles prompt formatting, API key management, and response processing.
    """

    def __init__(
        self,
        profile_repository: ProfileRepository,
        prompt_service: Optional[PromptService] = None,
        model: str = "claude-3-5-haiku-20241022",
        temperature: float = 0.1,
        enable_json_validation: bool = True,
    ):
        """
        Initialize the LLM service.

        Args:
            profile_repository: Repository for accessing user profiles and preferences
            prompt_service: Service for loading and formatting prompts
            model: Override the default model from settings
            temperature: Override the default temperature from settings
            enable_json_validation: Whether to enable client-side JSON schema validation
        """
        self.profile_repository = profile_repository
        self.prompt_service = prompt_service
        self.model = model
        self.temperature = temperature
        self.max_tokens = settings.llm.max_tokens
        self.enable_json_validation = enable_json_validation

        # Store API keys from environment config as fallbacks
        self.api_keys = {
            "openai": settings.llm.openai_api_key,
            "anthropic": settings.llm.anthropic_api_key,
            "google": settings.llm.gemini_api_key,
            "cohere": None,
            "mistral": None,
        }

        self._setup_litellm()
        self.logger = get_logger(self.__class__.__name__)
        self.logger.info(f"LLM service initialized with model: {self.model}")

    def _setup_litellm(self):
        """Set up litellm with API keys."""
        # Configure litellm with API keys
        try:
            litellm.api_key_dict = {
                "openai": self.api_keys["openai"],
                "anthropic": self.api_keys["anthropic"],
                "google": self.api_keys["google"],
            }

            # Enable JSON schema validation if needed
            if self.enable_json_validation:
                litellm.enable_json_schema_validation = True

            logger.debug("LiteLLM configured with API keys")
        except Exception as e:
            logger.error(f"Error configuring LiteLLM: {e}")
            raise

    async def _get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        Get LLM preferences for a user.

        Args:
            user_id: User ID

        Returns:
            Dictionary of LLM preferences
        """
        if not self.profile_repository:
            return {}

        try:
            profile = await self.profile_repository.get_by_user_id(user_id)
            if profile and profile.preferences and profile.preferences.llm_preferences:
                return profile.preferences.llm_preferences
        except Exception as e:
            self.logger.error(f"Error fetching user preferences: {e}")

        return {}

    async def _get_api_keys_for_user(self, user_id: str) -> Dict[str, str]:
        """
        Get all API keys for a user.

        Args:
            user_id: User ID

        Returns:
            Dictionary of API keys
        """
        if not self.profile_repository:
            return {}

        try:
            return await self.profile_repository.get_api_keys(user_id)
        except Exception as e:
            self.logger.error(f"Error fetching API keys: {e}")
            return {}

    async def configure_for_user(self, user_id: Union[str, PydanticObjectId]) -> None:
        """
        Configure the LLM service for a specific user.

        Args:
            user_id: User ID to configure for
        """
        try:
            # Get user profile
            profile = await self.profile_repository.get_by_user_id(user_id)

            if (
                profile
                and profile.preferences
                and "llm_preferences" in profile.preferences
            ):
                llm_prefs = profile.preferences["llm_preferences"]

                # Update model and temperature if specified
                if "model_name" in llm_prefs:
                    self.model = llm_prefs["model_name"]
                    logger.debug(f"Using model from user preferences: {self.model}")

                if "temperature" in llm_prefs:
                    self.temperature = llm_prefs["temperature"]
                    logger.debug(
                        f"Using temperature from user preferences: {self.temperature}"
                    )
            else:
                logger.debug("No user preferences found, using defaults")

            # Get all user API keys
            user_api_keys = await self._get_api_keys_for_user(user_id)

            # Update the service's API keys with user-specific keys if available
            if "OPENAI_API_KEY" in user_api_keys:
                self.api_keys["openai"] = user_api_keys["OPENAI_API_KEY"]
            if "ANTHROPIC_API_KEY" in user_api_keys:
                self.api_keys["anthropic"] = user_api_keys["ANTHROPIC_API_KEY"]
            if "GEMINI_API_KEY" in user_api_keys:
                self.api_keys["google"] = user_api_keys["GEMINI_API_KEY"]
            if "MISTRAL_API_KEY" in user_api_keys:
                self.api_keys["mistral"] = user_api_keys["MISTRAL_API_KEY"]
            if "COHERE_API_KEY" in user_api_keys:
                self.api_keys["cohere"] = user_api_keys["COHERE_API_KEY"]

            # Reconfigure litellm with updated keys
            self._setup_litellm()

            # Configure prompt service if available
            if self.prompt_service:
                self.prompt_service.set_user_id(user_id)

            self.logger.debug(f"LLM service configured for user {user_id}")

        except Exception as e:
            self.logger.error(f"Error configuring for user {user_id}: {e}")
            # Continue with defaults

    async def set_model_parameters(self, parameters: Dict[str, Any]) -> None:
        """
        Set model parameters for the LLM service temporarily.

        Args:
            parameters: Dictionary of parameters to set
                - model_name: Model name
                - temperature: Temperature for sampling
                - max_tokens: Maximum tokens in response
                - model_type: Model provider type
        """
        try:
            # Update model if specified
            if "model_name" in parameters:
                self.model = parameters["model_name"]
                self.logger.debug(f"Set model to: {self.model}")

            # Update temperature if specified
            if "temperature" in parameters:
                self.temperature = parameters["temperature"]
                self.logger.debug(f"Set temperature to: {self.temperature}")

            # Update max_tokens if specified
            if "max_tokens" in parameters:
                self.max_tokens = parameters["max_tokens"]
                self.logger.debug(f"Set max_tokens to: {self.max_tokens}")

            # Reconfigure litellm if needed
            if any(key in parameters for key in ["model_type", "provider"]):
                self._setup_litellm()

            self.logger.info("LLM parameters updated")
        except Exception as e:
            self.logger.error(f"Error setting model parameters: {e}")
            raise

    async def get_prompt(self, prompt_name: str) -> str:
        """
        Get a prompt by name.

        Args:
            prompt_name: Name of the prompt

        Returns:
            Formatted prompt text

        Raises:
            ValueError: If prompt_service is not available
        """
        if not self.prompt_service:
            raise ValueError("Prompt service not available")

        return await self.prompt_service.get_prompt(prompt_name)

    async def get_section_prompt(self, section_name: str) -> str:
        """
        Get a prompt for a specific portfolio section.

        Args:
            section_name: Name of the section

        Returns:
            Formatted prompt text

        Raises:
            ValueError: If prompt_service is not available
        """
        if not self.prompt_service:
            raise ValueError("Prompt service not available")

        return await self.prompt_service.get_section_prompt(section_name)

    def model_supports_json_mode(self, model: Optional[str] = None) -> bool:
        """
        Check if the model supports JSON output mode.

        Args:
            model: Model name to check, defaults to the service's model

        Returns:
            Boolean indicating whether the model supports JSON output
        """
        model = model or self.model

        try:
            supported_params = get_supported_openai_params(model=model)
            return "response_format" in supported_params
        except Exception as e:
            self.logger.warning(f"Error checking JSON mode support: {e}")
            return False

    def model_supports_json_schema(self, model: Optional[str] = None) -> bool:
        """
        Check if the model supports JSON schema for structured outputs.

        Args:
            model: Model name to check, defaults to the service's model

        Returns:
            Boolean indicating whether the model supports JSON schema
        """
        model = model or self.model

        try:
            provider = self._get_provider_from_model(model)
            return supports_response_schema(model=model, custom_llm_provider=provider)
        except Exception as e:
            self.logger.warning(f"Error checking JSON schema support: {e}")
            return False

    async def get_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Get a completion from the LLM.

        Args:
            prompt: The prompt to send to the LLM
            system_prompt: Optional system prompt (for models that support it)
            model: Optional model to use (overrides instance default)
            temperature: Optional temperature (overrides instance default)
            max_tokens: Optional max tokens (overrides instance default)

        Returns:
            str: The LLM's completion

        Raises:
            Exception: If the LLM call fails
        """
        try:
            # Use provided parameters or class defaults
            model = model or self.model
            temperature = temperature if temperature is not None else self.temperature
            max_tokens = max_tokens or self.max_tokens

            # Get provider from model name
            provider = self._get_provider_from_model(model)

            # Create messages with both system and user content
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            # Set up the completion parameters
            completion_kwargs = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            # Add provider if available
            if provider:
                completion_kwargs["api_base"] = None  # Let LiteLLM handle API base
                completion_kwargs["api_key"] = self.api_keys.get(provider)

            self.logger.debug(f"Calling LLM with model: {model}, temp: {temperature}")

            # Make the API call with retry logic to handle transient failures
            max_retries = 2
            retry_delay = 2  # seconds

            for attempt in range(max_retries + 1):
                try:
                    # Get completion from LiteLLM
                    response = await acompletion(**completion_kwargs)

                    # Extract and return the completion text
                    completion_text = response.choices[0].message.content

                    # Truncate for logging if too long
                    log_text = (
                        completion_text
                        if len(completion_text) < 100
                        else f"{completion_text[:100]}... (truncated)"
                    )
                    self.logger.debug(f"LLM response: {log_text}")

                    return completion_text

                except Exception as e:
                    if attempt < max_retries:
                        self.logger.warning(
                            f"LLM call attempt {attempt+1} failed: {str(e)}. Retrying in {retry_delay}s..."
                        )
                        await asyncio.sleep(retry_delay)
                        # Double delay for next retry
                        retry_delay *= 2
                    else:
                        # Last attempt failed, raise the exception
                        self.logger.error(
                            f"All LLM call attempts failed. Last error: {str(e)}"
                        )
                        raise

        except Exception as e:
            self.logger.error(f"Error getting LLM completion: {str(e)}")
            self.logger.error(f"Model: {model}, Prompt length: {len(prompt)}")
            # Log prompt first 100 chars for debugging
            truncated_prompt = prompt[:100] + "..." if len(prompt) > 100 else prompt
            self.logger.error(f"Prompt start: {truncated_prompt}")
            raise

    async def get_structured_completion(
        self,
        prompt: str,
        schema_model: Type[BaseModel],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        fallback_to_text: bool = True,
    ) -> Union[BaseModel, str]:
        """
        Get a structured completion from the LLM using JSON schema.

        Args:
            prompt: The prompt text
            schema_model: Pydantic model class to use as JSON schema
            system_prompt: Optional system prompt
            model: Optional model override
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            fallback_to_text: Whether to fallback to text completion if JSON mode not supported

        Returns:
            Instance of schema_model or raw text if fallback_to_text=True

        Raises:
            ValueError: If model doesn't support JSON mode and fallback_to_text=False
        """
        try:
            # Use provided values or fall back to instance defaults
            model = model or self.model
            temperature = temperature or self.temperature
            max_tokens = max_tokens or self.max_tokens

            # Prepare messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            else:
                # Add default system prompt for JSON output if none provided
                messages.append(
                    {
                        "role": "system",
                        "content": "You are a helpful assistant designed to output JSON.",
                    }
                )

            messages.append({"role": "user", "content": prompt})

            # Get the provider for this model
            provider = self._get_provider_from_model(model)
            api_key = self.api_keys.get(provider) if provider else None

            # Check if model supports JSON mode
            supports_json = self.model_supports_json_mode(model)
            supports_schema = self.model_supports_json_schema(model)

            # If model doesn't support JSON mode and we can't fallback, raise error
            if not supports_json and not fallback_to_text:
                raise ValueError(
                    f"Model {model} does not support JSON output and fallback is disabled"
                )

            # Configure response format if supported
            kwargs = {}
            if supports_json:
                if supports_schema:
                    # Use full JSON schema
                    self.logger.debug(f"Using full JSON schema with model {model}")
                    kwargs["response_format"] = schema_model
                else:
                    # Use simple JSON mode
                    self.logger.debug(f"Using basic JSON mode with model {model}")
                    kwargs["response_format"] = {"type": "json_object"}
            elif fallback_to_text:
                # Will use text mode with fallback parsing
                self.logger.warning(
                    f"Model {model} doesn't support JSON mode, will use text mode and try to parse result"
                )

            # Log the request
            self.logger.debug(
                f"Sending structured request to {model} with temperature {temperature}"
            )

            # Call the LLM
            response = await acompletion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=api_key,
                **kwargs,
            )

            # Process the response
            content = response.choices[0].message.content

            # If using JSON mode, content should already be structured
            # If using text mode with fallback, try to parse the content
            if isinstance(content, dict):
                # Content is already a dict, parse it into the model
                return schema_model.model_validate(content)
            else:
                # Content is text, try to parse if fallback enabled
                if fallback_to_text:
                    # In fallback mode, return the raw text
                    # This allows the caller to decide how to handle it
                    return content
                else:
                    # Try to parse JSON from text, may raise exception
                    import json

                    parsed = json.loads(content)
                    return schema_model.model_validate(parsed)

        except Exception as e:
            self.logger.error(f"Error getting structured completion: {e}")
            raise

    def _get_provider_from_model(self, model: str) -> Optional[str]:
        """
        Get the provider name from the model name.

        Args:
            model: Model name (e.g., 'gpt-4', 'claude-3-opus')

        Returns:
            Provider name or None if unknown
        """
        model_lower = model.lower()
        if "gpt" in model_lower or "text-embedding" in model_lower:
            return "openai"
        elif "claude" in model_lower:
            return "anthropic"
        elif "gemini" in model_lower:
            return "google"
        elif "command" in model_lower:
            return "cohere"
        elif "llama" in model_lower or "mistral" in model_lower:
            return "mistral"
        else:
            return None

    async def generate_section(
        self,
        section_name: str,
        context: Dict[str, Any],
        job_description: str,
        use_json_schema: bool = True,
        schema_model: Optional[Type[BaseModel]] = None,
    ) -> Union[BaseModel, str]:
        """
        Generate content for a resume section.

        Args:
            section_name: Name of the section to generate
            context: Context data for the generation
            job_description: Job description to target
            use_json_schema: Whether to use JSON schema output
            schema_model: Optional Pydantic model to use for JSON schema output

        Returns:
            Generated section content as a Pydantic model instance or string
        """
        try:
            # Get the appropriate prompt for this section
            prompt_text = await self.get_section_prompt(section_name)

            # Get system prompt
            system_prompt = await self.prompt_service.get_system_prompt()

            # If using JSON schema, append instructions to format as JSON
            if use_json_schema and system_prompt:
                system_prompt += "\nYou must output your response in valid JSON format."

            # Combine prompt with context and job description
            full_prompt = f"""
Job Description:
{job_description}

{prompt_text}

Section Data:
{context}
"""
            # If using JSON schema and a model is provided, use structured completion
            if use_json_schema and schema_model is not None:
                return await self.get_structured_completion(
                    prompt=full_prompt,
                    schema_model=schema_model,
                    system_prompt=system_prompt,
                    fallback_to_text=True,  # Fallback to text if model doesn't support JSON
                )
            else:
                # Otherwise use regular completion
                return await self.get_completion(
                    prompt=full_prompt,
                    system_prompt=system_prompt,
                )

        except Exception as e:
            self.logger.error(f"Error generating {section_name} section: {e}")
            raise

    async def generate_cover_letter(
        self,
        resume_content: Dict[str, Any],
        job_description: str,
        company_name: str,
        job_title: str,
    ) -> str:
        """
        Generate a cover letter based on resume content and job description.

        Args:
            resume_content: Resume content dictionary
            job_description: Job description text
            company_name: Company name
            job_title: Job title

        Returns:
            Generated cover letter text
        """
        try:
            # Get cover letter prompt
            prompt_text = await self.prompt_service.get_cover_letter_prompt()

            # Get system prompt
            system_prompt = await self.prompt_service.get_system_prompt()

            # Combine prompt with resume content and job details
            full_prompt = f"""
Job Title: {job_title}
Company Name: {company_name}
Job Description:
{job_description}

Resume Content:
{resume_content}

{prompt_text}
"""

            # Get completion
            return await self.get_completion(
                prompt=full_prompt,
                system_prompt=system_prompt,
                # Cover letters can be longer
                max_tokens=self.max_tokens * 2,
            )

        except Exception as e:
            self.logger.error(f"Error generating cover letter: {e}")
            raise

    async def extract_job_title_and_company(
        self, job_description: str
    ) -> Tuple[str, str]:
        """
        Extract job title and company name from a job description using LLM.

        Args:
            job_description: The job description text

        Returns:
            Tuple of (company_name, job_title)
        """
        if not job_description or len(job_description.strip()) < 50:
            self.logger.warning(f"Job description too short: {job_description}")
            return "unknown_company", "unknown_position"

        try:
            # Get the folder name prompt
            folder_name_prompt = await self.prompt_service.get_folder_name_prompt()

            # Use the LLM service to get the completion
            system_prompt = await self.prompt_service.get_system_prompt()

            # Trim job description if it's too long to avoid token limits
            max_desc_length = 5000
            trimmed_job_description = (
                job_description[:max_desc_length]
                if len(job_description) > max_desc_length
                else job_description
            )

            # Create a very explicit prompt
            prompt = f'{folder_name_prompt}\n\nJob Description:\n{trimmed_job_description}\n\nYour task is to extract ONLY the company name and job title from this job description. Reply with VALID JSON only in this format: {{"company_name": "extracted_company_name", "job_title": "extracted_job_title"}}'

            response = await self.get_completion(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.1,  # Lower temperature for more deterministic results
            )

            # Parse the JSON response according to CompanyJobSchema format
            try:
                import json

                # Clean the response to ensure it's valid JSON
                cleaned_response = response.strip()
                # Sometimes the response includes markdown code blocks or extra text
                if "```json" in cleaned_response:
                    json_start = cleaned_response.find("```json") + 7
                    json_end = cleaned_response.find("```", json_start)
                    cleaned_response = cleaned_response[json_start:json_end].strip()
                elif "```" in cleaned_response:
                    json_start = cleaned_response.find("```") + 3
                    json_end = cleaned_response.find("```", json_start)
                    cleaned_response = cleaned_response[json_start:json_end].strip()

                # Parse the JSON
                parsed_response = json.loads(cleaned_response)

                # Extract values from the parsed JSON
                company_name = parsed_response.get("company_name", "unknown_company")
                job_title = parsed_response.get("job_title", "unknown_position")

                # Validate that we don't have empty values
                if not company_name or company_name == "":
                    company_name = "unknown_company"
                if not job_title or job_title == "":
                    job_title = "unknown_position"

                self.logger.info(
                    f"Successfully extracted company: {company_name}, job: {job_title}"
                )
                return company_name, job_title

            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse JSON response: {response}")
                self.logger.error(f"JSON parse error: {e}")

            # If JSON parsing fails, try to search for keys in the raw text
            import re

            company_match = re.search(r'"company_name":\s*"([^"]+)"', response)
            job_match = re.search(r'"job_title":\s*"([^"]+)"', response)

            if company_match and job_match:
                company_name = company_match.group(1)
                job_title = job_match.group(1)

                # Validate that we don't have empty values
                if not company_name or company_name == "":
                    company_name = "unknown_company"
                if not job_title or job_title == "":
                    job_title = "unknown_position"

                self.logger.info(
                    f"Extracted via regex - company: {company_name}, job: {job_title}"
                )
                return company_name, job_title

            # Try other regex patterns that might match different formats
            company_matches = [
                re.search(r'company_name["\']:\s*["\']([^"\']+)["\']', response),
                re.search(r'company["\']:\s*["\']([^"\']+)["\']', response),
                re.search(r"company:\s*([^\n,]+)", response),
            ]

            job_matches = [
                re.search(r'job_title["\']:\s*["\']([^"\']+)["\']', response),
                re.search(r'job["\']:\s*["\']([^"\']+)["\']', response),
                re.search(r'position["\']:\s*["\']([^"\']+)["\']', response),
                re.search(r'title["\']:\s*["\']([^"\']+)["\']', response),
                re.search(r"job_title:\s*([^\n,]+)", response),
            ]

            company_name = next(
                (m.group(1) for m in company_matches if m), "unknown_company"
            )
            job_title = next((m.group(1) for m in job_matches if m), "unknown_position")

            if company_name != "unknown_company" or job_title != "unknown_position":
                self.logger.info(
                    f"Extracted via alternate regex - company: {company_name}, job: {job_title}"
                )
                return company_name, job_title

            # If all parsing fails, return default values
            self.logger.warning(
                f"Failed to extract company/title from response: {response}"
            )
            return "unknown_company", "unknown_position"

        except Exception as e:
            self.logger.error(f"Error extracting job title and company: {e}")
            return "unknown_company", "unknown_position"

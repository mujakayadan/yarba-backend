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
        self.logger = logger

        # Store API keys from environment config as fallbacks
        self.api_keys = {
            "openai": settings.llm.openai_api_key,
            "anthropic": settings.llm.anthropic_api_key,
            "google": settings.llm.gemini_api_key,
            "cohere": None,
            "mistral": None,
        }

        # For tracking costs against specific documents
        self.current_resume_id: Optional[PydanticObjectId] = None
        self.current_cover_letter_id: Optional[PydanticObjectId] = None

        self._setup_litellm()
        self.logger = get_logger(self.__class__.__name__)
        self.logger.info(f"LLM service initialized with model: {self.model}")

    def _setup_litellm(self):
        """Set up litellm with API keys and custom pricing."""
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

            # Configure cost tracking
            if settings.llm.enable_cost_tracking:
                # Use LiteLLM's built-in model cost map if enabled
                if settings.llm.use_litellm_model_cost_map:
                    # If we have a custom URL for the model cost map, use it
                    if settings.llm.custom_model_cost_map_url:
                        try:
                            self.logger.debug(
                                f"Using custom model cost map URL: {settings.llm.custom_model_cost_map_url}"
                            )
                            # Register the custom cost map from URL
                            litellm.register_model(
                                model_cost=settings.llm.custom_model_cost_map_url
                            )
                        except Exception as e:
                            self.logger.warning(
                                f"Error loading custom model cost map from URL: {e}"
                            )
                            self.logger.info(
                                "Falling back to LiteLLM's built-in model cost map"
                            )
                    else:
                        # Use the default model_cost_map from LiteLLM
                        self.logger.debug("Using LiteLLM's built-in model cost map")
                        # No need to do anything as LiteLLM uses its cost map by default

                # Register any custom model prices (only for models not in LiteLLM's cost map)
                if settings.llm.model_pricing:
                    self.logger.debug(
                        f"Registering custom pricing for {len(settings.llm.model_pricing)} models"
                    )

                    # Import model_cost here to check against it
                    from litellm import model_cost

                    for model_name, pricing in settings.llm.model_pricing.items():
                        # Skip if model is already in LiteLLM's cost map and we're using it
                        if (
                            settings.llm.use_litellm_model_cost_map
                            and model_name in model_cost
                        ):
                            self.logger.debug(
                                f"Skipping {model_name} as it's already in LiteLLM's cost map"
                            )
                            continue

                        input_cost = pricing.get("input_cost_per_token")
                        output_cost = pricing.get("output_cost_per_token")

                        if input_cost and output_cost:
                            self.logger.debug(
                                f"Setting custom pricing for model: {model_name}"
                            )

                            # Configure model info with pricing
                            model_info = {
                                "input_cost_per_token": input_cost,
                                "output_cost_per_token": output_cost,
                            }

                            # If we need to use a base model for tracking, add it
                            if "/" in model_name:
                                provider, base_model = model_name.split("/", 1)
                                if provider.lower() == "azure":
                                    model_info["base_model"] = model_name

                            # Use litellm's custom cost tracking
                            try:
                                litellm.register_model(
                                    model_name=model_name, model_info=model_info
                                )
                            except Exception as e:
                                self.logger.warning(
                                    f"Error registering custom pricing for {model_name}: {e}"
                                )

            self.logger.debug("LiteLLM configured with API keys and cost tracking")
        except Exception as e:
            self.logger.error(f"Error configuring LiteLLM: {e}")
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

    async def _track_usage(
        self,
        user_id: Optional[str],
        model: str,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        cost: float,
        operation_type: str,
        resume_id: Optional[PydanticObjectId] = None,
        cover_letter_id: Optional[PydanticObjectId] = None,
    ) -> None:
        """
        Track LLM usage in the user's profile and optionally in a specific resume or cover letter.

        Args:
            user_id: User ID (optional)
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            total_tokens: Total number of tokens
            cost: Cost of the operation
            operation_type: Type of operation
            resume_id: Optional Resume ID to track usage against
            cover_letter_id: Optional Cover Letter ID to track usage against
        """
        if (
            not user_id
            or not self.profile_repository
            or not settings.llm.enable_cost_tracking
        ):
            return

        try:
            # Extract operation type from tags if provided as a list
            if isinstance(operation_type, list) and len(operation_type) > 0:
                # Find the first tag that starts with "operation:"
                for tag in operation_type:
                    if isinstance(tag, str) and tag.startswith("operation:"):
                        operation_type = tag
                        break
                else:
                    # No operation tag found, use the first tag
                    operation_type = operation_type[0]

            # Ensure operation_type is a string
            if not isinstance(operation_type, str):
                operation_type = "unknown"

            # Update usage in profile
            await self.profile_repository.update_llm_usage(
                user_id=user_id,
                tokens_used=total_tokens,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost,
                model_name=model,
                operation_type=operation_type,
            )

            # If resume_id is provided directly or as a class property, track usage against the resume
            resume_id_to_use = resume_id or self.current_resume_id
            if resume_id_to_use:
                from core.repositories.resume_repository import ResumeRepository

                resume_repo = ResumeRepository()
                await resume_repo.update_llm_usage(
                    resume_id=resume_id_to_use,
                    tokens_used=total_tokens,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost=cost,
                    model_name=model,
                    operation_type=operation_type,
                )

            # If cover_letter_id is provided directly or as a class property, track usage against the cover letter
            cover_letter_id_to_use = cover_letter_id or self.current_cover_letter_id
            if cover_letter_id_to_use:
                from core.repositories.cover_letter_repository import (
                    CoverLetterRepository,
                )

                cover_letter_repo = CoverLetterRepository()
                await cover_letter_repo.update_llm_usage(
                    cover_letter_id=cover_letter_id_to_use,
                    tokens_used=total_tokens,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost=cost,
                    model_name=model,
                    operation_type=operation_type,
                )
        except Exception as e:
            self.logger.error(f"Error tracking LLM usage: {e}")

    async def check_usage_limits(self, user_id: Optional[str]) -> Dict[str, Any]:
        """
        Check if a user has exceeded their LLM usage limits.

        Args:
            user_id: User ID

        Returns:
            Dict with limit information
        """
        if (
            not user_id
            or not self.profile_repository
            or not settings.llm.enable_cost_tracking
        ):
            return {"can_use": True}

        try:
            limits = await self.profile_repository.check_llm_usage_limits(user_id)
            return limits
        except Exception as e:
            self.logger.error(f"Error checking LLM usage limits: {e}")
            # Allow usage on error
            return {"can_use": True, "error": str(e)}

    async def get_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        user_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> str:
        """
        Get a completion from the LLM.

        Args:
            prompt: The prompt to send to the LLM
            system_prompt: Optional system prompt (for models that support it)
            model: Optional model to use (overrides instance default)
            temperature: Optional temperature (overrides instance default)
            max_tokens: Optional max tokens (overrides instance default)
            user_id: Optional user ID for LiteLLM cost tracking
            tags: Optional tags for LiteLLM cost tracking

        Returns:
            str: The LLM's completion

        Raises:
            Exception: If the LLM call fails
        """
        try:
            # If user_id is provided, check usage limits
            if user_id and settings.llm.enable_cost_tracking:
                limits = await self.check_usage_limits(user_id)
                if not limits.get("can_use", True):
                    reason = "usage limit exceeded"
                    if limits.get("monthly_quota_exceeded"):
                        reason = "monthly token quota exceeded"
                    elif limits.get("monthly_cost_exceeded"):
                        reason = "monthly cost limit exceeded"

                    error_msg = f"LLM usage limit exceeded for user {user_id}: {reason}"
                    self.logger.warning(error_msg)
                    raise ValueError(error_msg)

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

            # Add cost tracking parameters
            if user_id:
                completion_kwargs["user"] = user_id

            # Add metadata with tags for cost tracking
            if tags:
                completion_kwargs["metadata"] = {"tags": tags}

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

                    # Log cost if available in response
                    if hasattr(response, "usage") and hasattr(
                        response.usage, "completion_tokens"
                    ):
                        input_tokens = getattr(response.usage, "prompt_tokens", 0)
                        output_tokens = getattr(response.usage, "completion_tokens", 0)
                        total_tokens = getattr(
                            response.usage, "total_tokens", input_tokens + output_tokens
                        )

                        # Calculate cost using litellm's completion_cost function
                        from litellm import completion_cost

                        # Try to get cost from response first
                        cost = getattr(response, "cost", None)

                        # If not available in response, calculate it
                        if cost is None and settings.llm.enable_cost_tracking:
                            try:
                                cost = completion_cost(completion_response=response)
                            except Exception as cost_e:
                                self.logger.warning(
                                    f"Error calculating completion cost: {cost_e}"
                                )

                        if cost:
                            self.logger.info(
                                f"Request cost: ${float(cost):.6f}, total tokens: {total_tokens} (in: {input_tokens}, out: {output_tokens})"
                            )

                            # Track usage in user profile
                            if user_id and settings.llm.enable_cost_tracking:
                                await self._track_usage(
                                    user_id=user_id,
                                    model=model,
                                    input_tokens=input_tokens,
                                    output_tokens=output_tokens,
                                    total_tokens=total_tokens,
                                    cost=float(cost),
                                    operation_type=tags if tags else "completion",
                                )
                        else:
                            self.logger.info(
                                f"Request used {total_tokens} tokens (in: {input_tokens}, out: {output_tokens})"
                            )

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
        user_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
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
            user_id: Optional user ID for cost tracking
            tags: Optional tags for cost tracking

        Returns:
            Instance of schema_model or raw text if fallback_to_text=True

        Raises:
            ValueError: If model doesn't support JSON mode and fallback_to_text=False
        """
        try:
            # If user_id is provided, check usage limits
            if user_id and settings.llm.enable_cost_tracking:
                limits = await self.check_usage_limits(user_id)
                if not limits.get("can_use", True):
                    reason = "usage limit exceeded"
                    if limits.get("monthly_quota_exceeded"):
                        reason = "monthly token quota exceeded"
                    elif limits.get("monthly_cost_exceeded"):
                        reason = "monthly cost limit exceeded"

                    error_msg = f"LLM usage limit exceeded for user {user_id}: {reason}"
                    self.logger.warning(error_msg)
                    raise ValueError(error_msg)

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

            # Add cost tracking parameters
            if user_id:
                kwargs["user"] = user_id

            # Add metadata with tags for cost tracking
            if tags:
                kwargs["metadata"] = {"tags": tags}

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

            # Log cost if available in response
            if hasattr(response, "usage") and hasattr(
                response.usage, "completion_tokens"
            ):
                input_tokens = getattr(response.usage, "prompt_tokens", 0)
                output_tokens = getattr(response.usage, "completion_tokens", 0)
                total_tokens = getattr(
                    response.usage, "total_tokens", input_tokens + output_tokens
                )

                # Calculate cost using litellm's completion_cost function
                from litellm import completion_cost

                # Try to get cost from response first
                cost = getattr(response, "cost", None)

                # If not available in response, calculate it
                if cost is None and settings.llm.enable_cost_tracking:
                    try:
                        cost = completion_cost(completion_response=response)
                    except Exception as cost_e:
                        self.logger.warning(
                            f"Error calculating completion cost: {cost_e}"
                        )

                if cost:
                    self.logger.info(
                        f"Request cost: ${float(cost):.6f}, total tokens: {total_tokens} (in: {input_tokens}, out: {output_tokens})"
                    )

                    # Track usage in user profile
                    if user_id and settings.llm.enable_cost_tracking:
                        await self._track_usage(
                            user_id=user_id,
                            model=model,
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                            total_tokens=total_tokens,
                            cost=float(cost),
                            operation_type=tags if tags else "structured_completion",
                        )
                else:
                    self.logger.info(
                        f"Request used {total_tokens} tokens (in: {input_tokens}, out: {output_tokens})"
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
        user_id: Optional[str] = None,
    ) -> Union[BaseModel, str]:
        """
        Generate content for a resume section.

        Args:
            section_name: Name of the section to generate
            context: Context data for the generation
            job_description: Job description to target
            use_json_schema: Whether to use JSON schema output
            schema_model: Optional Pydantic model to use for JSON schema output
            user_id: Optional user ID for cost tracking

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
            # Cost tracking tags
            tags = [f"operation:generate_section", f"section:{section_name}"]

            # If using JSON schema and a model is provided, use structured completion
            if use_json_schema and schema_model is not None:
                return await self.get_structured_completion(
                    prompt=full_prompt,
                    schema_model=schema_model,
                    system_prompt=system_prompt,
                    fallback_to_text=True,  # Fallback to text if model doesn't support JSON
                    user_id=user_id,
                    tags=tags,
                )
            else:
                # Otherwise use regular completion
                return await self.get_completion(
                    prompt=full_prompt,
                    system_prompt=system_prompt,
                    user_id=user_id,
                    tags=tags,
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
        user_id: Optional[str] = None,
    ) -> str:
        """
        Generate a cover letter based on resume content and job description.

        Args:
            resume_content: Resume content dictionary
            job_description: Job description text
            company_name: Company name
            job_title: Job title
            user_id: Optional user ID for cost tracking

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
            # Cost tracking tags
            tags = [
                "operation:generate_cover_letter",
                f"company:{company_name}",
                f"job:{job_title}",
            ]

            # Get completion
            return await self.get_completion(
                prompt=full_prompt,
                system_prompt=system_prompt,
                # Cover letters can be longer
                max_tokens=self.max_tokens * 2,
                user_id=user_id,
                tags=tags,
            )

        except Exception as e:
            self.logger.error(f"Error generating cover letter: {e}")
            raise

    async def extract_job_title_and_company(
        self, job_description: str, user_id: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Extract job title and company name from a job description using LLM.

        Args:
            job_description: The job description text
            user_id: Optional user ID for cost tracking

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

            # Add cost tracking tags
            tags = ["operation:extract_job_details"]

            response = await self.get_completion(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.1,  # Lower temperature for more deterministic results
                user_id=user_id,
                tags=tags,
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

    async def get_usage_statistics(
        self,
        user_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get usage statistics from LiteLLM cost tracking.

        Args:
            user_id: Optional user ID to filter by
            start_date: Optional start date in format YYYY-MM-DD
            end_date: Optional end date in format YYYY-MM-DD

        Returns:
            Dictionary with usage statistics
        """
        try:
            # Verify that litellm is properly configured
            if not settings.llm.enable_cost_tracking:
                self.logger.warning("Cost tracking is not enabled in settings")
                return {"error": "Cost tracking is not enabled", "enabled": False}

            # Note: In a production setup with LiteLLM proxy server,
            # you would use the LiteLLM API to get cost data from its database
            # This is a simpler implementation using the in-memory tracking

            # Get tracking data from litellm
            # This would typically come from a database in a proxy server setup
            cost_data = {
                "enabled": settings.llm.enable_cost_tracking,
                "message": "Cost tracking enabled but no database configured. Log data available.",
                "note": "For full cost tracking, configure LiteLLM with a database.",
                "models": list(settings.llm.model_pricing.keys()),
            }

            # If we had a proxy with database, we could query it here
            # Example future implementation:
            # if settings.litellm_proxy_url:
            #     async with httpx.AsyncClient() as client:
            #         params = {"user_id": user_id} if user_id else {}
            #         if start_date:
            #             params["start_date"] = start_date
            #         if end_date:
            #             params["end_date"] = end_date
            #
            #         response = await client.get(
            #             f"{settings.litellm_proxy_url}/spend/report",
            #             params=params,
            #             headers={"Authorization": f"Bearer {settings.litellm_proxy_key}"}
            #         )
            #         return response.json()

            return cost_data

        except Exception as e:
            self.logger.error(f"Error retrieving usage statistics: {e}")
            return {"error": str(e), "enabled": settings.llm.enable_cost_tracking}

    async def get_model_cost_info(self) -> Dict[str, Any]:
        """
        Get model cost information from LiteLLM.

        Returns:
            Dictionary with model cost information from LiteLLM
        """
        try:
            # Import model_cost from litellm
            from litellm import model_cost

            # Return key information about the models
            models_info = {}

            # Format the model cost information for better readability
            for model_name, cost_info in model_cost.items():
                # Skip entries that don't have proper cost info
                if not isinstance(cost_info, dict):
                    continue

                # Only include key pricing info
                models_info[model_name] = {
                    "input_cost_per_token": cost_info.get("input_cost_per_token", 0),
                    "output_cost_per_token": cost_info.get("output_cost_per_token", 0),
                    "max_tokens": cost_info.get("max_tokens", 0),
                }

                # Add other useful info if available
                for key in ["litellm_provider", "mode"]:
                    if key in cost_info:
                        models_info[model_name][key] = cost_info[key]

            return {
                "enabled": settings.llm.enable_cost_tracking,
                "using_litellm_model_cost_map": settings.llm.use_litellm_model_cost_map,
                "models": models_info,
            }

        except Exception as e:
            self.logger.error(f"Error retrieving model cost information: {e}")
            return {
                "error": str(e),
                "enabled": settings.llm.enable_cost_tracking,
                "using_litellm_model_cost_map": settings.llm.use_litellm_model_cost_map,
            }

    async def get_user_llm_usage(self, user_id: str) -> Dict[str, Any]:
        """
        Get LLM usage statistics for a user.

        Args:
            user_id: User ID

        Returns:
            Dict with LLM usage statistics
        """
        if (
            not user_id
            or not self.profile_repository
            or not settings.llm.enable_cost_tracking
        ):
            return {
                "enabled": settings.llm.enable_cost_tracking,
                "error": "Cost tracking not enabled or user ID/profile repository not available",
            }

        try:
            # Get usage data from profile repository
            usage_data = await self.profile_repository.get_llm_usage(user_id)
            if not usage_data:
                return {
                    "enabled": settings.llm.enable_cost_tracking,
                    "error": "No usage data found",
                    "total_tokens": 0,
                    "total_cost": 0.0,
                }

            # Check usage limits
            limits = await self.profile_repository.check_llm_usage_limits(user_id)

            # Combine usage data with limits data
            result = {"enabled": settings.llm.enable_cost_tracking, **usage_data}

            # Add limits info
            if limits:
                result["limits"] = {
                    "can_use": limits.get("can_use", True),
                    "monthly_quota_exceeded": limits.get(
                        "monthly_quota_exceeded", False
                    ),
                    "monthly_cost_exceeded": limits.get("monthly_cost_exceeded", False),
                }

            return result

        except Exception as e:
            self.logger.error(f"Error getting user LLM usage: {e}")
            return {"enabled": settings.llm.enable_cost_tracking, "error": str(e)}

    async def set_user_llm_limits(
        self,
        user_id: str,
        monthly_quota: Optional[int] = None,
        monthly_cost_limit: Optional[float] = None,
    ) -> bool:
        """
        Set LLM usage limits for a user.

        Args:
            user_id: User ID
            monthly_quota: Maximum number of tokens per month (None for unlimited)
            monthly_cost_limit: Maximum cost per month in USD (None for unlimited)

        Returns:
            bool: True if update was successful, False otherwise
        """
        if (
            not user_id
            or not self.profile_repository
            or not settings.llm.enable_cost_tracking
        ):
            return False

        try:
            # Set limits in profile repository
            return await self.profile_repository.set_llm_usage_limits(
                user_id=user_id,
                monthly_quota=monthly_quota,
                monthly_cost_limit=monthly_cost_limit,
            )
        except Exception as e:
            self.logger.error(f"Error setting user LLM limits: {e}")
            return False

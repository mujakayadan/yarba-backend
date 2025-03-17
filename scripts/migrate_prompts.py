"""Script to migrate txt prompts to Python modules."""

import os
import re
from pathlib import Path


def snake_case(s: str) -> str:
    """Convert a string to snake case."""
    # Remove file extension
    s = s.replace("_prompt.txt", "")
    return s


def create_prompt_module(source_file: Path, dest_file: Path) -> None:
    """Create a Python module from a prompt text file.

    Args:
        source_file: Path to the source txt file
        dest_file: Path to the destination py file
    """
    # Read the template content
    with open(source_file, "r", encoding="utf-8") as f:
        template = f.read().strip()

    # Convert the template to a Python string with proper escaping
    template = template.replace("\\", "\\\\")  # Escape backslashes
    template = template.replace("'", "\\'")  # Escape single quotes

    # Create the Python module content
    module_name = snake_case(source_file.name)
    class_name = (
        "".join(word.capitalize() for word in module_name.split("_")) + "Prompt"
    )
    constant_name = module_name.upper() + "_PROMPT"

    content = f'''"""Prompt template for {module_name.replace("_", " ")}."""

from .base import BasePrompt

TEMPLATE = \'\'\'{template}\'\'\'


class {class_name}(BasePrompt):
    """{module_name.replace("_", " ").title()} prompt template."""

    def __init__(self):
        """Initialize the {module_name.replace("_", " ")} prompt template."""
        super().__init__(TEMPLATE)


{constant_name} = {class_name}()
'''

    # Write the Python module
    with open(dest_file, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    """Main function to migrate prompts."""
    # Get the prompts directory
    prompts_dir = Path("core/llm/prompts")

    # Create __pycache__ directory if it doesn't exist
    cache_dir = prompts_dir / "__pycache__"
    cache_dir.mkdir(exist_ok=True)

    # Create base.py if it doesn't exist
    base_file = prompts_dir / "base.py"
    if not base_file.exists():
        with open(base_file, "w", encoding="utf-8") as f:
            f.write(
                '''"""Base prompt template."""

from typing import Dict, Optional


class BasePrompt:
    """Base class for all prompts."""

    def __init__(self, template: str):
        """Initialize the prompt template.
        
        Args:
            template: The prompt template string
        """
        self._template = template.strip()

    def format(self, **kwargs: Dict[str, str]) -> str:
        """Format the prompt template with the given arguments.
        
        Args:
            **kwargs: Keyword arguments to format the template with
            
        Returns:
            The formatted prompt string
        """
        return self._template.format(**kwargs)

    def __str__(self) -> str:
        """Return the prompt template as a string."""
        return self._template

    def __repr__(self) -> str:
        """Return a string representation of the prompt."""
        return f"{self.__class__.__name__}({self._template})"
'''
            )

    # Create __init__.py if it doesn't exist
    init_file = prompts_dir / "__init__.py"
    if not init_file.exists():
        with open(init_file, "w", encoding="utf-8") as f:
            f.write('''"""Prompt templates for LLM interactions."""\n\n''')

    # Process each txt file
    txt_files = list(prompts_dir.glob("*.txt"))
    for txt_file in txt_files:
        # Create corresponding .py file
        py_file = prompts_dir / f"{txt_file.stem[:-6]}.py"
        create_prompt_module(txt_file, py_file)

        # Add import to __init__.py
        module_name = snake_case(txt_file.name)
        constant_name = module_name.upper() + "_PROMPT"
        with open(init_file, "a", encoding="utf-8") as f:
            f.write(f"from .{module_name} import {constant_name}\n")

    # Add __all__ to __init__.py
    with open(init_file, "a", encoding="utf-8") as f:
        constants = [f"{snake_case(f.name).upper()}_PROMPT" for f in txt_files]
        f.write("\n__all__ = [\n")
        for constant in sorted(constants):
            f.write(f'    "{constant}",\n')
        f.write("]\n")


if __name__ == "__main__":
    main()

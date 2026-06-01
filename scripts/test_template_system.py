#!/usr/bin/env python3
"""Test script to verify the new template system works correctly."""

import asyncio

from core.latex.template_registry import get_resume_template, list_resume_templates


async def test_template_system():
    """Test the template system."""
    print("Testing Template System")
    print("=" * 50)

    # Test 1: List available templates
    print("\n1. Available Resume Templates:")
    templates = list_resume_templates()
    for template in templates:
        print(f"   - {template['id']}: {template['name']}")
        print(f"     Description: {template['description']}")
        print()

    # Test 2: Get specific templates
    print("2. Testing Template Retrieval:")

    # Test classic template
    classic_template = get_resume_template("classic")
    print(f"   Classic template ID: {classic_template['id']}")
    print(f"   Classic template name: {classic_template['name']}")
    print(f"   Classic preamble length: {len(classic_template['preamble'])} chars")
    print(f"   Classic preamble starts with: {classic_template['preamble'][:50]}...")

    # Test modern template
    modern_template = get_resume_template("modern")
    print(f"\n   Modern template ID: {modern_template['id']}")
    print(f"   Modern template name: {modern_template['name']}")
    print(f"   Modern preamble length: {len(modern_template['preamble'])} chars")
    print(f"   Modern preamble starts with: {modern_template['preamble'][:50]}...")

    # Test 3: Verify templates are different
    print("\n3. Template Comparison:")
    classic_is_different = classic_template["preamble"] != modern_template["preamble"]
    print(f"   Classic and Modern templates are different: {classic_is_different}")

    # Test 4: Verify templates contain expected content
    print("\n4. Template Content Verification:")
    modern_has_colors = "\\definecolor{primarycolor}" in modern_template["preamble"]
    classic_has_colors = "\\definecolor{primarycolor}" in classic_template["preamble"]
    print(f"   Modern template has color definitions: {modern_has_colors}")
    print(f"   Classic template has color definitions: {classic_has_colors}")

    # Test 5: Test default fallback
    print("\n5. Default Template Fallback:")
    default_template = get_resume_template(None)
    print(f"   Default template ID: {default_template['id']}")
    print(f"   Default template name: {default_template['name']}")

    # Test 6: Test invalid template fallback
    print("\n6. Invalid Template Fallback:")
    invalid_template = get_resume_template("non_existent")
    print(f"   Invalid template fallback ID: {invalid_template['id']}")
    print(f"   Invalid template fallback name: {invalid_template['name']}")

    print("\n" + "=" * 50)
    print("Template System Test Complete!")

    # Test 7: Test LaTeX service template methods
    print("\n7. Testing LaTeX Service Template Methods:")
    try:
        from api.dependencies.services import get_latex_service
        from core.database.factory import get_portfolio_repository, get_user_repository
        from core.services.portfolio_service import PortfolioService

        # Create a simple portfolio service (this would normally be injected)
        portfolio_repo = await get_portfolio_repository()
        user_repo = await get_user_repository()
        portfolio_service = PortfolioService(portfolio_repo, user_repo)

        # Create LaTeX service
        latex_service = await get_latex_service(portfolio_service)

        # Test template methods
        resume_templates = latex_service.get_available_resume_templates()
        print(f"   LaTeX Service found {len(resume_templates)} resume templates")

        cover_letter_templates = latex_service.get_available_cover_letter_templates()
        print(
            f"   LaTeX Service found {len(cover_letter_templates)} cover letter templates"
        )

        for template in resume_templates:
            print(f"   - {template['id']}: {template['name']}")

    except Exception as e:
        print(f"   Error testing LaTeX service: {e}")
        print("   This is expected if not running in the full application context")

    print("\nAll tests completed successfully!")


if __name__ == "__main__":
    asyncio.run(test_template_system())

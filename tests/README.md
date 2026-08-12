# Tests for the YARBA API

This directory contains tests for the YARBA API. The tests are organized by module and use pytest as the testing framework.

## Test Structure

The tests are organized as follows:

- `api/`: Tests for API endpoints and components
  - `test_auth.py`: Tests for authentication endpoints
  - `test_dependencies.py`: Tests for API dependencies
  - `test_health.py`: Tests for health check endpoint
  - `test_middleware.py`: Tests for middleware components
  - `test_resumes.py`: Tests for resume endpoints
  - `test_cover_letters.py`: Tests for cover letter endpoints
  - `test_schemas.py`: Tests for API schemas

- `core/`: Tests for core functionality
  - `test_database.py`: Tests for database connection
  - `test_exceptions.py`: Tests for exception classes
  - `test_repositories.py`: Tests for repositories
  - `test_services.py`: Tests for services
  - `test_utils.py`: Tests for utility functions

- `conftest.py`: Shared fixtures and configuration for tests

## Running Tests

To run all tests:

```bash
pytest
```

To run tests with coverage:

```bash
pytest --cov=new_structure
```

To run a specific test file:

```bash
pytest new_structure/tests/api/test_auth.py
```

To run a specific test:

```bash
pytest new_structure/tests/api/test_auth.py::test_register_user
```

## Test Configuration

The `conftest.py` file contains shared fixtures and configuration for tests. It includes:

- Mock database connections
- Mock repositories
- Mock services
- Test data fixtures
- Authentication fixtures
- Environment variable mocks

## Writing Tests

When writing tests, follow these guidelines:

1. Use the Arrange-Act-Assert pattern
2. Use descriptive test names
3. Use fixtures for shared setup
4. Mock external dependencies
5. Test both success and failure cases
6. Test edge cases
7. Use proper assertions

Example:

```python
@pytest.mark.asyncio
async def test_register_user_success(client):
    """Test successful user registration."""
    # Arrange
    user_data = {
        "email": "test@example.com",
        "password": "Password123!",
        "full_name": "Test User",
    }

    # Act
    response = client.post("/api/auth/register", json=user_data)

    # Assert
    assert response.status_code == 201
    assert "id" in response.json()
    assert response.json()["email"] == user_data["email"]
```

## Mocking

For mocking, use the `unittest.mock` module. For example:

```python
from unittest.mock import AsyncMock, MagicMock, patch

# Mock a function
with patch("module.function") as mock_function:
    mock_function.return_value = "mocked value"
    result = function()
    assert result == "mocked value"

# Mock an async function
with patch("module.async_function") as mock_function:
    mock_function.return_value = AsyncMock(return_value="mocked value")
    result = await async_function()
    assert result == "mocked value"
```

## Test Coverage

Aim for at least 80% test coverage. To check coverage:

```bash
pytest --cov=new_structure --cov-report=term-missing
```

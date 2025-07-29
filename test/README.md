# Unit Testing Guide for Your Daily Podcaster

This document outlines the testing strategy, best practices, and guidelines for writing comprehensive unit tests for the Your Daily Podcaster project.

## Table of Contents

- [Overview](#overview)
- [Testing Framework](#testing-framework)
- [Test Structure](#test-structure)
- [Best Practices](#best-practices)
- [Running Tests](#running-tests)
- [Coverage](#coverage)
- [Continuous Integration](#continuous-integration)
- [Test Categories](#test-categories)
- [Mocking Guidelines](#mocking-guidelines)
- [Common Patterns](#common-patterns)
- [Troubleshooting](#troubleshooting)

## Overview

Our test suite follows industry standards for Python testing, ensuring high-quality, maintainable, and reliable code. We use `pytest` as our primary testing framework with comprehensive mocking and fixtures.

### Goals

- **High Test Coverage**: Aim for 90%+ code coverage
- **Fast Execution**: Unit tests should run quickly (< 5 minutes total)
- **Isolation**: Each test should be independent and not rely on external services
- **Maintainability**: Tests should be easy to read, understand, and modify
- **Reliability**: Tests should consistently pass or fail based on code changes

## Testing Framework

We use the following testing stack:

- **pytest**: Main testing framework
- **pytest-cov**: Coverage reporting
- **pytest-mock**: Enhanced mocking capabilities
- **unittest.mock**: Python's built-in mocking library

### Dependencies

Install test dependencies:

```bash
pip install pytest pytest-cov pytest-mock
```

Or use the development dependencies:

```bash
pip install -e ".[test]"
```

## Test Structure

### File Organization

```
test/
├── README.md                     # This file
├── __init__.py                   # Test package initialization
├── test_step_by_step.py         # Integration tests
├── test_utils_time.py           # Utils: time module tests
├── test_utils_db.py             # Utils: database module tests
├── test_utils_logger.py         # Utils: logger module tests
├── test_utils_browser.py        # Utils: browser module tests
├── test_scraper_fetch_search_results.py  # Scraper: news fetcher tests
├── test_scraper_scrape_articles.py       # Scraper: article scraper tests
└── test_run_pipeline.py         # Pipeline orchestrator tests
```

### Test File Naming Convention

- Test files: `test_<module_name>.py`
- Test classes: `Test<ClassName>`
- Test methods: `test_<functionality_description>`

### Test Class Structure

```python
class TestClassName:
    """Test cases for ClassName functionality."""

    @pytest.fixture
    def sample_data(self):
        """Provide sample data for tests."""
        return {"key": "value"}

    def test_method_success(self):
        """Test successful method execution."""
        # Arrange
        # Act
        # Assert

    def test_method_error_handling(self):
        """Test method error handling."""
        # Test error conditions
```

## Best Practices

### 1. Test Structure (AAA Pattern)

Follow the **Arrange-Act-Assert** pattern:

```python
def test_calculate_total():
    # Arrange
    calculator = Calculator()
    items = [10, 20, 30]

    # Act
    result = calculator.calculate_total(items)

    # Assert
    assert result == 60
```

### 2. Test Naming

Use descriptive test names that explain:
- What is being tested
- Under what conditions
- What the expected outcome is

```python
# Good
def test_fetch_articles_returns_empty_list_when_no_topics_found(self):
    pass

# Bad
def test_fetch(self):
    pass
```

### 3. One Assertion Per Test

Focus each test on a single behavior:

```python
# Good
def test_user_creation_sets_name(self):
    user = User("John")
    assert user.name == "John"

def test_user_creation_sets_active_status(self):
    user = User("John")
    assert user.is_active is True

# Avoid
def test_user_creation(self):
    user = User("John")
    assert user.name == "John"
    assert user.is_active is True
```

### 4. Use Fixtures for Common Setup

```python
@pytest.fixture
def temp_database():
    """Provide a temporary database for testing."""
    with tempfile.NamedTemporaryFile() as temp_file:
        db = Database(temp_file.name)
        yield db
        # Cleanup happens automatically
```

### 5. Parameterized Tests

Use `pytest.mark.parametrize` for testing multiple scenarios:

```python
@pytest.mark.parametrize("url,expected", [
    ("https://example.com", True),
    ("http://test.com", True),
    ("invalid-url", False),
    ("", False),
])
def test_is_valid_url(url, expected):
    assert is_valid_url(url) == expected
```

## Running Tests

### Basic Commands

```bash
# Run all tests
pytest

# Run specific test file
pytest test/test_utils_time.py

# Run specific test class
pytest test/test_utils_time.py::TestTimeUtilities

# Run specific test method
pytest test/test_utils_time.py::TestTimeUtilities::test_get_yesterday_date

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=yourdaily --cov-report=html
```

### Useful Options

```bash
# Stop on first failure
pytest -x

# Show local variables in tracebacks
pytest -l

# Run only failed tests from last run
pytest --lf

# Run tests in parallel (requires pytest-xdist)
pytest -n auto
```

## Coverage

### Target Coverage

- **Minimum**: 80% overall coverage
- **Target**: 90%+ overall coverage
- **Critical modules**: 95%+ coverage (utils, core logic)

### Generating Coverage Reports

```bash
# Generate HTML coverage report
pytest --cov=yourdaily --cov-report=html

# Generate terminal coverage report
pytest --cov=yourdaily --cov-report=term-missing

# Generate XML coverage report (for CI)
pytest --cov=yourdaily --cov-report=xml
```

### Coverage Configuration

Add to `pyproject.toml`:

```toml
[tool.coverage.run]
source = ["yourdaily"]
omit = [
    "*/test/*",
    "*/tests/*",
    "*/venv/*",
    "*/.venv/*",
    "*/__pycache__/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if self.debug:",
    "if settings.DEBUG",
    "raise AssertionError",
    "raise NotImplementedError",
    "if 0:",
    "if __name__ == .__main__.:",
]
```

## Test Categories

### 1. Unit Tests

Test individual functions/methods in isolation:

```python
def test_parse_rss_date_success():
    """Test successful RSS date parsing."""
    fetcher = NewsFetcher()
    result = fetcher.parse_rss_date("Mon, 28 Jul 2025 09:00:06 GMT")
    assert result == "2025-07-28"
```

### 2. Integration Tests

Test interaction between components:

```python
def test_article_scraping_workflow(db_manager):
    """Test complete article scraping workflow."""
    scraper = ArticleScraper()
    # Test end-to-end workflow
```

### 3. Mock-Heavy Tests

Test external dependencies with mocks:

```python
@patch('yourdaily.scraper.requests.get')
def test_fetch_rss_feed(mock_get):
    """Test RSS feed fetching with mocked HTTP requests."""
    mock_response = MagicMock()
    mock_response.content = "rss_content"
    mock_get.return_value = mock_response

    # Test implementation
```

## Mocking Guidelines

### 1. Mock External Dependencies

Always mock:
- HTTP requests
- File system operations
- Database connections
- External APIs
- Time-dependent functions

```python
@patch('yourdaily.utils.time.datetime')
def test_get_yesterday_date(mock_datetime):
    mock_datetime.now.return_value = datetime(2024, 1, 15)
    result = get_yesterday_date()
    assert result == "2024-01-14"
```

### 2. Use Context Managers

```python
def test_with_context_manager():
    with patch('module.function') as mock_func:
        mock_func.return_value = "mocked_value"
        # Test code
```

### 3. Mock at the Right Level

Mock at the boundary of your unit:

```python
# Good - mock the external dependency
@patch('yourdaily.scraper.requests.get')

# Avoid - mocking internal logic
@patch('yourdaily.scraper.ArticleScraper.parse_content')
```

### 4. Verify Mock Calls

```python
@patch('yourdaily.utils.logger.get_logger')
def test_logging(mock_get_logger):
    mock_logger = MagicMock()
    mock_get_logger.return_value = mock_logger

    # Execute code that should log
    function_that_logs()

    # Verify logging occurred
    mock_logger.info.assert_called_once_with("Expected message")
```

## Common Patterns

### 1. Testing Exceptions

```python
def test_function_raises_value_error():
    with pytest.raises(ValueError, match="Expected error message"):
        function_that_should_raise()
```

### 2. Testing File Operations

```python
def test_file_operations():
    with tempfile.TemporaryDirectory() as temp_dir:
        file_path = os.path.join(temp_dir, "test.txt")
        # Test file operations
```

### 3. Testing Async Code

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result == expected_value
```

### 4. Testing Environment Variables

```python
def test_with_env_var():
    with patch.dict(os.environ, {'TEST_VAR': 'test_value'}):
        # Test code that uses environment variables
```

## Continuous Integration

### GitHub Actions Configuration

Create `.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, 3.10, 3.11]

    steps:
    - uses: actions/checkout@v3
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e ".[test]"

    - name: Run tests
      run: |
        pytest --cov=yourdaily --cov-report=xml

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
```

### Pre-commit Hooks

Configure pre-commit to run tests:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: tests
        name: tests
        entry: pytest
        language: system
        types: [python]
        pass_filenames: false
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Add project root to Python path
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"
   ```

2. **Mock Not Working**
   - Ensure you're patching the correct import path
   - Patch where the object is used, not where it's defined

3. **Flaky Tests**
   - Use deterministic test data
   - Mock time-dependent functions
   - Avoid relying on external services

4. **Slow Tests**
   - Mock external calls
   - Use smaller test datasets
   - Consider parallel execution

### Debugging Tests

```bash
# Run with pdb debugger
pytest --pdb

# Drop into debugger on failure
pytest --pdb --tb=short

# Print statements
pytest -s
```

## Code Quality Tools

### Linting and Formatting

```bash
# Run linting
flake8 test/

# Format code
black test/

# Sort imports
isort test/
```

### Type Checking

```bash
# Run mypy
mypy test/
```

## Examples

### Complete Test Example

```python
#!/usr/bin/env python3
"""
Unit tests for yourdaily.example.module.
"""

import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock
from yourdaily.example.module import ExampleClass


class TestExampleClass:
    """Test cases for ExampleClass."""

    @pytest.fixture
    def example_instance(self):
        """Create an ExampleClass instance for testing."""
        return ExampleClass()

    @pytest.fixture
    def sample_data(self):
        """Provide sample data for tests."""
        return {"key": "value", "number": 42}

    def test_init(self, example_instance):
        """Test class initialization."""
        assert example_instance is not None
        assert hasattr(example_instance, 'attribute')

    @pytest.mark.parametrize("input_value,expected", [
        ("test", "TEST"),
        ("hello", "HELLO"),
        ("", ""),
    ])
    def test_method_with_various_inputs(self, example_instance, input_value, expected):
        """Test method with various input values."""
        result = example_instance.process(input_value)
        assert result == expected

    @patch('yourdaily.example.module.external_dependency')
    def test_method_with_external_dependency(self, mock_dependency, example_instance):
        """Test method that depends on external service."""
        mock_dependency.return_value = "mocked_response"

        result = example_instance.method_using_external_service()

        assert result == "processed_mocked_response"
        mock_dependency.assert_called_once()

    def test_error_handling(self, example_instance):
        """Test error handling for invalid input."""
        with pytest.raises(ValueError, match="Invalid input"):
            example_instance.process(None)

    def test_with_temporary_file(self, example_instance):
        """Test functionality that requires file system operations."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write("test content")
            temp_file_path = temp_file.name

        try:
            result = example_instance.process_file(temp_file_path)
            assert result == "processed content"
        finally:
            os.unlink(temp_file_path)


if __name__ == "__main__":
    pytest.main([__file__])
```

## Conclusion

Following these guidelines ensures that our test suite remains:
- **Comprehensive**: Covers all critical functionality
- **Maintainable**: Easy to update as code evolves
- **Reliable**: Consistent results across environments
- **Fast**: Quick feedback during development

Remember: Good tests are an investment in code quality and development velocity. They catch bugs early, enable confident refactoring, and serve as living documentation of the system's behavior.

For questions or suggestions about testing practices, please refer to the project documentation or reach out to the development team.

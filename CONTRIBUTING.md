# Contributing to Agent Search

Thank you for your interest in contributing! This guide will help you get started.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Release Process](#release-process)

---

## Code of Conduct

This project and everyone participating in it is governed by our commitment to:

- Be respectful and inclusive
- Welcome newcomers
- Accept constructive criticism
- Focus on what is best for the community
- Show empathy towards others

---

## Getting Started

### Ways to Contribute

- **Report Bugs**: Open an issue with detailed information
- **Suggest Features**: Open an issue with feature description
- **Write Code**: Submit pull requests
- **Improve Documentation**: Fix typos, add examples
- **Answer Questions**: Help others in discussions

### Before You Start

1. Check existing issues to avoid duplicates
2. Comment on an issue if you're working on it
3. For major changes, open an issue first to discuss

---

## Development Setup

### Prerequisites

- Python 3.9+
- Git
- Virtual environment tool (venv, conda, etc.)

### Setup Steps

1. **Fork and Clone**:
   ```bash
git clone https://github.com/qwert/agent-search.git
cd agent-search
   ```

2. **Create Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate  # Windows
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Development dependencies
   ```

4. **Install in Development Mode**:
   ```bash
   pip install -e .
   ```

5. **Run Tests**:
   ```bash
   python -m pytest tests/ -v
   ```

### Development Dependencies

Create `requirements-dev.txt`:

```
pytest>=7.0.0
pytest-cov>=4.0.0
pytest-asyncio>=0.21.0
black>=23.0.0
flake8>=6.0.0
mypy>=1.0.0
pre-commit>=3.0.0
```

---

## Making Changes

### Branch Naming

- `feature/description` - New features
- `bugfix/description` - Bug fixes
- `docs/description` - Documentation
- `refactor/description` - Code refactoring

Example: `feature/add-websocket-support`

### Code Style

We follow PEP 8 with these additions:

1. **Use Black for formatting**:
   ```bash
   black src/agent_search/ tests/
   ```

2. **Use isort for imports**:
   ```bash
   isort src/agent_search/ tests/
   ```

3. **Type hints required**:
   ```python
   def fetch_url(url: str, timeout: int = 30) -> Response:
       ...
   ```

4. **Docstrings**:
   ```python
   def extract_data(html: str) -> List[Dict]:
       """
       Extract data from HTML.
       
       Args:
           html: HTML content
           
       Returns:
           List of extracted items
       """
   ```

### Pre-commit Hooks

Set up pre-commit:

```bash
pre-commit install
```

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=100]
```

---

## Testing

### Writing Tests

1. **Test Naming**:
   - `test_<module>_<function>_<scenario>`
   - Example: `test_proxy_chain_get_success`

2. **Test Structure**:
   ```python
   class TestProxyChain(unittest.TestCase):
       def setUp(self):
           """Set up test fixtures."""
           pass
       
       def test_get_success(self):
           """Test successful GET request."""
           # Arrange
           # Act
           # Assert
           pass
   ```

3. **Use Mocks**:
   ```python
   @patch('agent_search.proxy_chain.requests.request')
   def test_request(self, mock_request):
       mock_request.return_value = Mock(status_code=200)
       # Test code
   ```

### Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific module
python -m pytest tests/test_proxy_chain.py -v

# Run with coverage
python -m pytest tests/ --cov=agent_search --cov-report=html

# Run quick tests only
python -m pytest tests/ -m "not integration and not slow"
```

### Test Coverage

Aim for:
- **Core modules**: 90%+ coverage
- **Utility modules**: 80%+ coverage
- **New features**: Must include tests

---

## Submitting Changes

### Pull Request Process

1. **Update Documentation**:
   - Update README.md if needed
   - Update API.md for new features
   - Add examples to examples.md

2. **Update CHANGELOG.md**:
   - Add entry under [Unreleased]
   - Follow Keep a Changelog format

3. **Commit Messages**:
   ```
   type(scope): subject
   
   body
   
   footer
   ```
   
   Types:
   - `feat`: New feature
   - `fix`: Bug fix
   - `docs`: Documentation
   - `style`: Code style
   - `refactor`: Code refactoring
   - `test`: Tests
   - `chore`: Build/dependency changes
   
   Example:
   ```
   feat(proxy): add retry with exponential backoff
   
   Add retry logic to ProxyChain with configurable
   exponential backoff and jitter.
   
   Fixes #123
   ```

4. **Create Pull Request**:
   - Fill out PR template
   - Link related issues
   - Add screenshots if UI changes
   - Ensure CI passes

### PR Review Process

1. **Automated Checks**:
   - Linting (flake8, black)
   - Type checking (mypy)
   - Tests (pytest)
   - Coverage

2. **Manual Review**:
   - Code quality
   - Test coverage
   - Documentation
   - Breaking changes

3. **Approval**:
   - Requires 2 approvals
   - All checks must pass
   - No merge conflicts

---

## Release Process

### Version Numbering

We follow Semantic Versioning (SemVer):

- `MAJOR.MINOR.PATCH`
- MAJOR: Breaking changes
- MINOR: New features (backwards compatible)
- PATCH: Bug fixes

### Release Checklist

1. **Update Version**:
   ```python
   # In __init__.py
   __version__ = "2.1.0"
   ```

2. **Update CHANGELOG**:
   - Move [Unreleased] to version section
   - Add release date

3. **Create Release**:
   ```bash
   git tag -a v2.1.0 -m "Release version 2.1.0"
   git push origin v2.1.0
   ```

4. **Build and Publish**:
   ```bash
   python setup.py sdist bdist_wheel
   twine upload dist/*
   ```

5. **Update Documentation**:
   - Deploy docs
   - Update README badges
   - Announce in discussions

---

## Documentation

### README Updates

Update these sections if needed:
- Features
- Installation
- Usage examples
- API reference
- Troubleshooting

### Code Documentation

Add docstrings to:
- Classes
- Public methods
- Module-level functions
- Constants

Format:
```python
"""
Short description.

Longer description with details.

Args:
    param1: Description of param1
    param2: Description of param2
    
Returns:
    Description of return value
    
Raises:
    ExceptionType: When this happens
    
Example:
    >>> example_code()
    expected_output
"""
```

---

## Questions?

- **Discord**: [Join our community](link)
- **Discussions**: [GitHub Discussions](link)
- **Issues**: [GitHub Issues](link)

Thank you for contributing! 🎉

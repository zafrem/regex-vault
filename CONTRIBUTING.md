# Contributing to regex-vault

Thank you for your interest in contributing to regex-vault! This document provides guidelines and instructions for contributing.

## Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/regex-vault.git
   cd regex-vault
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install development dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=regexvault --cov-report=html

# Run specific test file
pytest tests/test_engine.py

# Run specific test
pytest tests/test_engine.py::TestFind::test_find_korean_mobile
```

## Code Quality

Before submitting a PR, ensure your code passes all checks:

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type check
mypy src/
```

## Adding New Patterns

When adding new patterns, follow these guidelines:

1. **File Organization**: Add patterns to the appropriate namespace file (e.g., `patterns/kr.yml`, `patterns/us.yml`)

2. **Pattern Structure**: Follow the schema defined in `schemas/pattern-schema.json`

3. **Required Fields**:
   - `id`: Unique identifier (lowercase, underscores) **with 2-digit suffix** (e.g., `mobile_01`, `ssn_02`)
   - `location`: Location/region identifier (e.g., `kr`, `us`, `comm`)
   - `category`: One of the allowed categories
   - `pattern`: Valid regex pattern
   - `description`: Clear description of what the pattern matches

4. **Naming Convention**: All pattern IDs must end with a 2-digit suffix (`_01`, `_02`, etc.) to enable multiple variations of similar patterns. For example:
   - `mobile_01` - Standard mobile format
   - `mobile_02` - Alternative mobile format
   - `ssn_01` - Standard SSN format
   - `ssn_02` - SSN without hyphens

5. **Location Field**: Each pattern must specify its location
   ```yaml
   - id: mobile_01
     location: kr          # Required: kr, us, comm, etc.
     category: phone
     pattern: '...'
   ```

6. **Examples**: Always include `match` and `nomatch` examples
   ```yaml
   examples:
     match:
       - "valid-example-1"
       - "valid-example-2"
     nomatch:
       - "invalid-example-1"
   ```

7. **Privacy Policy**: Set appropriate privacy settings
   ```yaml
   policy:
     store_raw: false  # Usually false for PII
     action_on_match: redact
     severity: high  # or low, medium, critical
   ```

8. **ReDoS Prevention**: Ensure patterns don't have catastrophic backtracking
   - Avoid nested quantifiers: `(a+)+`, `(a*)*`
   - Avoid overlapping alternatives: `(a|a)+`
   - Test with long inputs

9. **Validation**: Run pattern validation
   ```bash
   python -c "from regexvault import load_registry; load_registry(validate_examples=True)"
   ```

## Pull Request Process

1. **Fork the repository** and create a new branch
   ```bash
   git checkout -b feature/my-new-feature
   ```

2. **Make your changes** following the code style guidelines

3. **Add tests** for new functionality

4. **Update documentation** if needed

5. **Ensure all checks pass**:
   - Tests pass
   - Code is formatted
   - No linting errors
   - Type checks pass
   - Pattern validation passes

6. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

   Follow [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` New feature
   - `fix:` Bug fix
   - `docs:` Documentation changes
   - `test:` Test changes
   - `refactor:` Code refactoring
   - `chore:` Maintenance tasks

7. **Push to your fork**
   ```bash
   git push origin feature/my-new-feature
   ```

8. **Create a Pull Request** on GitHub

## Pattern Contribution Guidelines

### New Country Support

When adding support for a new country:

1. Create a new file: `patterns/{country_code}.yml`
2. Use ISO 3166-1 alpha-2 country codes
3. Include common PII types:
   - Phone numbers
   - National ID numbers
   - Postal codes
   - Tax IDs
   - Driver's licenses

### Pattern Testing

All patterns must have comprehensive examples:

```yaml
examples:
  match:
    - "010-1234-5678"    # Standard format
    - "01012345678"      # Without separators
    - "010 1234 5678"    # Space separators
  nomatch:
    - "02-1234-5678"     # Wrong prefix
    - "010-123-456"      # Too short
    - "010-1234-56789"   # Too long
```

### Security Considerations

- **Never include real PII** in examples or tests
- Use synthetic/fake data only
- Set `store_raw: false` for sensitive patterns
- Mark critical PII with `severity: critical`

## Release Process

Releases are automated via GitHub Actions:

1. Update version in `pyproject.toml`
2. Create and push a tag:
   ```bash
   git tag -a v0.2.0 -m "Release v0.2.0"
   git push origin v0.2.0
   ```
3. GitHub Actions will:
   - Run all tests
   - Build package
   - Publish to PyPI
   - Build and push Docker image
   - Create GitHub release

## Versioning

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features, pattern additions
- **PATCH**: Bug fixes, pattern fixes

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on the issue, not the person
- Assume good intentions

## Questions?

- Open an issue for bugs or feature requests
- Start a discussion for questions
- Check existing issues and discussions first

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

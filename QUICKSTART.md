# Quick Start Guide

This guide will help you get started with regex-vault in under 5 minutes.

## Installation

```bash
pip install regex-vault
```

## Basic Usage

### 1. Library API

```python
from regexvault import Engine, load_registry

# Load patterns
registry = load_registry()
engine = Engine(registry)

# Find PII in text
text = "Contact me at 010-1234-5678 or john@example.com"
result = engine.find(text, namespaces=["kr", "common"])

print(f"Found {result.match_count} matches:")
for match in result.matches:
    print(f"  - {match.ns_id} at position {match.start}-{match.end}")

# Validate a specific value
is_valid = engine.validate("010-1234-5678", "kr/mobile_01")
print(f"Valid Korean mobile: {is_valid.is_valid}")

# Redact PII
redacted = engine.redact(text, namespaces=["kr", "common"])
print(f"Redacted: {redacted.redacted_text}")
```

### 2. Command Line Interface

```bash
# Find PII in text
echo "Call 010-1234-5678" | regex-vault find --ns kr

# Validate a value
regex-vault validate --text "010-1234-5678" --ns-id kr/mobile_01

# Redact a file
regex-vault redact --in input.txt --out redacted.txt --ns kr common

# List available patterns
regex-vault list-patterns
```

### 3. HTTP Server

```bash
# Start server
regex-vault serve --port 8080

# In another terminal, use the API:
# Find PII
curl -X POST http://localhost:8080/find \
  -H "Content-Type: application/json" \
  -d '{"text": "Call 010-1234-5678", "namespaces": ["kr"]}'

# Validate
curl -X POST http://localhost:8080/validate \
  -H "Content-Type: application/json" \
  -d '{"text": "010-1234-5678", "ns_id": "kr/mobile_01"}'

# Redact
curl -X POST http://localhost:8080/redact \
  -H "Content-Type: application/json" \
  -d '{"text": "My phone: 010-1234-5678", "namespaces": ["kr"]}'

# Health check
curl http://localhost:8080/health
```

## Docker

```bash
# Build image
docker build -t regex-vault -f docker/Dockerfile .

# Run container
docker run -p 8080:8080 regex-vault

# Or use docker-compose
docker-compose -f docker/docker-compose.yml up
```

## Development

```bash
# Clone repository
git clone https://github.com/yourusername/regex-vault.git
cd regex-vault

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Format code
make format

# Validate patterns
make validate-patterns

# Start development server
make serve
```

## Common Use Cases

### Use Case 1: Log File Sanitization

```python
from regexvault import Engine, load_registry

# Load registry
registry = load_registry()
engine = Engine(registry)

# Read log file
with open("application.log", "r") as f:
    logs = f.read()

# Redact all PII
result = engine.redact(logs, namespaces=["kr", "us", "common"])

# Save sanitized logs
with open("sanitized.log", "w") as f:
    f.write(result.redacted_text)

print(f"Redacted {result.redaction_count} PII items")
```

### Use Case 2: Data Validation

```python
from regexvault import Engine, load_registry

registry = load_registry()
engine = Engine(registry)

# Validate user input
phone = input("Enter Korean mobile number: ")
result = engine.validate(phone, "kr/mobile_01")

if result.is_valid:
    print("✓ Valid phone number")
else:
    print("✗ Invalid phone number")
```

### Use Case 3: PII Detection in Database

```python
from regexvault import Engine, load_registry
import sqlite3

registry = load_registry()
engine = Engine(registry)

# Connect to database
conn = sqlite3.connect("users.db")
cursor = conn.cursor()

# Check for PII in comments
cursor.execute("SELECT id, comment FROM user_comments")
for row_id, comment in cursor.fetchall():
    result = engine.find(comment, namespaces=["kr", "common"])

    if result.has_matches:
        print(f"Row {row_id} contains PII:")
        for match in result.matches:
            print(f"  - {match.ns_id} ({match.severity.value})")
```

### Use Case 4: Real-time API Monitoring

```python
from regexvault import Engine, load_registry
from flask import Flask, request, jsonify

app = Flask(__name__)
registry = load_registry()
engine = Engine(registry)

@app.before_request
def check_pii():
    """Check requests for PII before processing."""
    if request.is_json:
        data_str = str(request.json)
        result = engine.find(data_str, namespaces=["kr", "us", "common"])

        if result.has_matches:
            critical = [m for m in result.matches if m.severity.value == "critical"]
            if critical:
                return jsonify({
                    "error": "Request contains critical PII",
                    "matches": [m.ns_id for m in critical]
                }), 400

@app.route("/api/submit", methods=["POST"])
def submit():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run()
```

## Configuration

Create a `config.yml` file:

```yaml
server:
  port: 8080
  host: "0.0.0.0"

registry:
  paths:
    - patterns/common.yml
    - patterns/kr.yml
    - patterns/us.yml
  hot_reload: true

redaction:
  default_strategy: mask
  mask_char: "*"

observability:
  metrics: prometheus
  log_level: INFO
```

Then use it:

```bash
regex-vault serve --config config.yml
```

## Available Patterns

### Korean (kr)
- `mobile_01` - Mobile phone numbers
- `landline_seoul_01` - Seoul landline numbers
- `rrn_01` - Resident Registration Number
- `business_registration_01` - Business Registration Number
- `corporate_registration_01` - Corporate Registration Number
- `passport_01` - Passport numbers
- `driver_license_01` - Driver's license numbers
- `bank_account_01` - Bank account numbers

### United States (us)
- `ssn_01` - Social Security Number
- `phone_01` - Phone numbers
- `zipcode_01` - ZIP codes
- `passport_01` - Passport numbers
- `ein_01` - Employer Identification Number
- `itin_01` - Individual Taxpayer Identification Number
- `driver_license_ca_01` - California driver's license
- `medicare_01` - Medicare Beneficiary Identifier

### Common
- `email_01` - Email addresses
- `ipv4_01` - IPv4 addresses
- `ipv6_01` - IPv6 addresses
- `credit_card_visa_01` - Visa credit cards
- `credit_card_mastercard_01` - MasterCard credit cards
- `url_01` - URLs

## Next Steps

- Read the [full documentation](README.md)
- Check [CONTRIBUTING.md](CONTRIBUTING.md) to add new patterns
- View [examples](examples/) for more use cases
- Join our [discussions](https://github.com/yourusername/regex-vault/discussions)

## Troubleshooting

### Pattern not found
```python
# List all available patterns
registry = load_registry()
for namespace in registry.namespaces:
    patterns = registry.get_namespace_patterns(namespace)
    print(f"{namespace}: {[p.id for p in patterns]}")
```

### False positives
- Use the `validate()` method for exact matching
- Adjust pattern examples and contribute improvements
- Use `severity` levels to filter results

### Performance issues
- Use specific namespaces instead of searching all
- Enable pattern caching
- Consider using the server mode for better performance

## Support

- 📖 [Documentation](README.md)
- 🐛 [Issues](https://github.com/yourusername/regex-vault/issues)
- 💬 [Discussions](https://github.com/yourusername/regex-vault/discussions)

# regex-vault

**regex-vault** is a general-purpose engine that detects and masks personal information (mobile phone numbers, social security numbers, email addresses, etc.) by **country and information type**, using a "pattern file-based + library + daemon (server)."

## Features

- 🌍 **Global Support**: Patterns organized by country (ISO2) and information type
- 🔍 **Detection**: Find PII in text using multiple patterns
- ✅ **Validation**: Validate text against specific patterns
- 🔒 **Redaction**: Mask, hash, or tokenize sensitive information
- 🚀 **Multiple Interfaces**: Library API, CLI, and HTTP/gRPC server
- ⚡ **High Performance**: p95 < 10ms for 1KB text (single namespace)
- 🔄 **Hot Reload**: Non-disruptive pattern reloading
- 📊 **Observability**: Prometheus metrics and health checks

## Quick Start

### Installation

```bash
pip install regex-vault
```

### Library Usage

```python
from regexvault import Engine, load_registry

# Load patterns
items = load_registry(paths=["patterns/common.yml", "patterns/kr.yml"])
engine = Engine(items)

# Validate
is_valid = engine.validate("010-1234-5678", "kr/mobile_01")  # True

# Find
results = engine.find(
    "My phone: 01012345678, email: test@example.com",
    namespaces=["kr", "common"]
)

# Redact
redacted = engine.redact(
    "SSN: 900101-1234567",
    namespaces=["kr"],
    strategy="mask"
)
```

### CLI Usage

```bash
# Find PII in text
regex-vault find --ns kr/mobile --file sample.txt

# Redact PII
regex-vault redact --in input.log --out redacted.log --ns kr us

# Start server
regex-vault serve --port 8080 --config config.yml
```

### Server Usage

Start the server:
```bash
regex-vault serve --port 8080
```

Use the REST API:
```bash
# Find PII
curl -X POST http://localhost:8080/find \
  -H "Content-Type: application/json" \
  -d '{"text": "010-1234-5678", "namespaces": ["kr"]}'

# Validate
curl -X POST http://localhost:8080/validate \
  -H "Content-Type: application/json" \
  -d '{"text": "010-1234-5678", "ns_id": "kr/mobile"}'

# Redact
curl -X POST http://localhost:8080/redact \
  -H "Content-Type: application/json" \
  -d '{"text": "My SSN is 900101-1234567", "namespaces": ["kr"]}'

# Health check
curl http://localhost:8080/health
```

## Pattern Structure

Patterns are defined in YAML files with the following structure:

```yaml
namespace: kr
description: Korean (South Korea) PII patterns

patterns:
  - id: mobile_01              # Required: Pattern ID with 2-digit suffix
    location: kr               # Required: Location identifier (kr, us, comm, etc.)
    category: phone            # Required: PII category
    description: Korean mobile phone number (010/011/016/017/018/019)
    pattern: '01[016-9]-?\d{3,4}-?\d{4}'  # Required: Regex pattern
    flags: [IGNORECASE]        # Optional: Regex flags
    mask: "***-****-****"      # Optional: Default mask template
    examples:                  # Optional but recommended
      match: ["010-1234-5678", "01012345678"]
      nomatch: ["012-999-9999"]
    policy:                    # Optional: Privacy and action policies
      store_raw: false
      action_on_match: redact
      severity: high
    metadata:                  # Optional: Additional metadata
      note: "Additional information"
```

### Required Fields

- **`id`**: Unique identifier with 2-digit suffix (e.g., `mobile_01`, `ssn_02`)
- **`location`**: Location/region code (2-4 lowercase letters: `kr`, `us`, `comm`, `intl`)
- **`category`**: PII category from: `phone`, `ssn`, `rrn`, `email`, `bank`, `passport`, `address`, `credit_card`, `ip`, `other`
- **`pattern`**: Regular expression pattern for matching

### Location Codes

The `location` field identifies the geographic or categorical scope of the pattern:

- **`comm`** - Common/International patterns
- **`kr`** - South Korea
- **`us`** - United States
- **`tw`** - Taiwan (Republic of China)
- **`jp`** - Japan
- **`cn`** - China (People's Republic of China)
- **`in`** - India
- **`eu`** - European Union (future)
- **`intl`** - International (multi-region)

**Note**: Pattern files can have any name. The system loads all `.yml` files from the `patterns/` directory and uses the `location` field to organize patterns.

## Configuration

Example `config.yml`:

```yaml
server:
  port: 8080
  tls: false

security:
  api_key_required: false
  rate_limit_rps: 100

registry:
  paths:
    - patterns/common.yml
    - patterns/kr.yml
    - patterns/us.yml
    - patterns/tw.yml
    - patterns/jp.yml
    - patterns/cn.yml
    - patterns/in.yml
  hot_reload: true

redaction:
  default_strategy: mask

observability:
  metrics: prometheus
```

## Docker

```bash
# Build
docker build -t regex-vault:latest .

# Run
docker run -p 8080:8080 -v ./patterns:/app/patterns regex-vault:latest
```

## Creating Custom Patterns

To add your own patterns:

1. **Create a YAML file** in the `patterns/` directory (any filename)

2. **Define your patterns** with required fields:

```yaml
namespace: custom
description: Custom organization patterns

patterns:
  - id: employee_id_01
    location: myorg     # Your organization/location code
    category: other
    description: Employee ID format
    pattern: 'EMP-\d{6}'
    mask: "EMP-******"
    examples:
      match: ["EMP-123456", "EMP-999999"]
      nomatch: ["EMP-12345", "TEMP-123456"]
    policy:
      store_raw: false
      action_on_match: redact
      severity: high
```

3. **Use your custom patterns**:

```python
from regexvault import load_registry, Engine

# Load with custom patterns
registry = load_registry(paths=["patterns/custom.yml"])
engine = Engine(registry)

# Use the pattern
result = engine.validate("EMP-123456", "custom/employee_id_01")
print(result.is_valid)  # True
```

### Pattern Naming Best Practices

- **ID Format**: `{name}_{NN}` where NN is a 2-digit number (e.g., `mobile_01`, `mobile_02`)
- **Location Codes**: Use 2-4 lowercase letters (e.g., `kr`, `us`, `comm`, `myorg`)
- **Versioning**: Increment the number suffix for pattern variations (e.g., `ssn_01`, `ssn_02`)

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=regexvault --cov-report=html

# Format code
black src/ tests/
ruff check src/ tests/

# Type check
mypy src/

# Validate patterns
python -c "from regexvault import load_registry; load_registry(validate_examples=True)"
```

## Performance

- **Latency**: p95 < 10ms for 1KB text with single namespace
- **Throughput**: 500+ RPS on 1 vCPU, 512MB RAM
- **Scalability**: Handles 1k+ patterns and 1k+ concurrent requests

## Security & Privacy

- No raw PII is logged (only hashes/metadata)
- TLS support for server
- Configurable rate limiting
- GDPR/CCPA compliant operations

## Supported Pattern Types

- 📱 Phone numbers
- 🆔 Social Security Numbers (SSN/RRN)
- 📧 Email addresses
- 🏦 Bank account numbers
- 🛂 Passport numbers
- 📍 Physical addresses

## Supported Patterns by Location

### Common/International (location: comm)
- `email` - Email addresses
- `ipv4` - IPv4 addresses
- `ipv6` - IPv6 addresses
- `credit_card_visa` - Visa credit cards
- `credit_card_mastercard` - MasterCard credit cards
- `url` - URLs

### Korean (location: kr)
- `mobile` - Mobile phone numbers
- `landline` - Landline numbers
- `rrn` - Resident Registration Number
- `business_registration` - Business Registration Number
- `corporate_registration` - Corporate Registration Number
- `passport` - Passport numbers
- `driver_license` - Driver's license numbers
- `bank_account` - Bank account numbers
- `korean_name` - Korean names

### United States (location: us)
- `ssn` - Social Security Number
- `phone` - Phone numbers
- `zipcode` - ZIP codes
- `passport` - Passport numbers
- `ein` - Employer Identification Number
- `itin` - Individual Taxpayer Identification Number
- `driver_license_ca` - California driver's license
- `medicare` - Medicare Beneficiary Identifier

### Taiwan (location: tw)
- `mobile` - Mobile phone numbers
- `landline` - Landline numbers
- `national_id` - National ID
- `passport` - Passport numbers
- `business_id` - Business Uniform Number
- `chinese_name` - Traditional Chinese names

### Japan (location: jp)
- `mobile` - Mobile phone numbers
- `landline` - Landline numbers
- `my_number` - My Number (individual number)
- `passport` - Passport numbers
- `zipcode` - Postal codes
- `driver_license` - Driver's license numbers
- `bank_account` - Bank account numbers
- `japanese_name_hiragana` - Japanese names (Hiragana)
- `japanese_name_katakana` - Japanese names (Katakana)
- `japanese_name_kanji` - Japanese names (Kanji)

### China (location: cn)
- `mobile` - Mobile phone numbers
- `landline` - Landline numbers
- `national_id` - National ID (18 digits)
- `passport` - Passport numbers
- `social_credit` - Unified Social Credit Code
- `bank_card` - Bank card numbers
- `chinese_name` - Simplified Chinese names

### India (location: in)
- `mobile` - Mobile phone numbers
- `landline` - Landline numbers
- `aadhaar` - Aadhaar number
- `pan` - PAN (Permanent Account Number)
- `passport` - Passport numbers
- `voter_id` - Voter ID (EPIC)
- `driving_license` - Driving license
- `pincode` - PIN codes
- `ifsc` - IFSC codes
- `gst` - GST numbers
- `indian_name` - Indian names (Latin script)

**Total**: 60+ patterns across 7 locations

## Roadmap

### Sprint 1 (Current)
- ✅ Pattern schema and validation
- ✅ Core engine (find/validate/redact)
- ✅ CLI interface
- ✅ Python API
- ✅ Multi-country patterns (KR/US/TW/JP/CN/IN/COMMON)

### Sprint 2
- REST/gRPC server
- Hot reload
- Prometheus metrics
- Docker packaging

### Sprint 3
- ReDoS detection and linting
- Tokenization strategy
- Extended pattern library (bank/address)

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests.

## Support

- 📖 [Documentation](https://github.com/yourusername/regex-vault/wiki)
- 🐛 [Issue Tracker](https://github.com/yourusername/regex-vault/issues)
- 💬 [Discussions](https://github.com/yourusername/regex-vault/discussions)

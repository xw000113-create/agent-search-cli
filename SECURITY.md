# Security Policy

## Supported Versions

We release patches for security vulnerabilities. Which versions are eligible
receiving such patches depend on the CVSS v3.0 Rating:

| Version | Supported          |
| ------- | ------------------ |
| 2.0.x   | :white_check_mark: |
| < 2.0   | :x:                |

## Reporting a Vulnerability

Please report security vulnerabilities by emailing security@qwert.ai

Please **DO NOT** file a public issue. Security reports are handled in
confidence.

Include as much information as possible:

- Type of vulnerability
- Full paths of source file(s) related to the manifestation of the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

## Response Timeline

1. **Acknowledgment**: Within 48 hours
2. **Assessment**: Within 7 days
3. **Fix release**: Depends on severity
   - Critical: Within 7 days
   - High: Within 30 days
   - Medium: Next release

## Security Best Practices

When using Agent Search:

1. **API Keys**: Store in environment variables, never commit to code
2. **Proxy Credentials**: Use secure storage, rotate regularly
3. **Rate Limiting**: Respect target website rate limits
4. **Data Storage**: Encrypt sensitive extracted data
5. **Network**: Use HTTPS for all API communications

## Disclosure Policy

- Security issues will be disclosed publicly after a fix is released
- Credit will be given to reporters who follow responsible disclosure
- CVE IDs will be requested for high/critical severity issues

## Security Features

Agent Search includes several security features:

- **API Key Authentication**: JWT-based for API endpoints
- **Rate Limiting**: Built-in to prevent abuse
- **Proxy Rotation**: Automatic IP rotation to prevent blocking
- **HTTPS Only**: All communications encrypted
- **No Data Retention**: Configurable data lifecycle

## Questions?

Contact: security@qwert.ai

PGP Key: [security@qwert.ai.asc](https://qwert.ai/security.asc)
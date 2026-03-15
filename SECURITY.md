# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 1.1.x   | ✅ Current release |
| 1.0.x   | ✅ Security fixes  |
| < 1.0   | ❌ Not supported   |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do NOT** open a public issue
2. Email: **security@xyvaclaw.com** or contact via [Discord](https://discord.gg/QABg4Z2Mzu) (DM an admin)
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
4. We will respond within **48 hours**

## Security Best Practices

When using xyvaClaw:

- Never commit your `.env` file (it's in `.gitignore`)
- Use app-specific passwords for email integration
- Keep API keys in environment variables, not in config files
- Regularly update: `cd XyvaClaw && git pull origin main`

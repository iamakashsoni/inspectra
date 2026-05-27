# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅ Yes    |

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Email: security@your-domain.com

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

You will receive a response within 72 hours.

## Security Notes for Self-Hosted Deployments

- Never expose your Ollama port (`11434`) publicly — bind to `localhost` only
- Never commit `.env` files or API keys to the repository
- The `.gitignore` already excludes `.env` and `.inspectra_cache/`
- Inspectra never executes code from the repository it reviews
- Prompts are sanitized before being sent to LLMs

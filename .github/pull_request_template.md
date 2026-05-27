## Summary

<!-- A clear, one-paragraph description of what this PR does and why. -->

Fixes #<!-- issue number, if applicable -->

---

## Type of change

<!-- Check all that apply -->

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 💥 Breaking change (fix or feature that changes existing behaviour)
- [ ] 🔧 Refactor (no functional changes)
- [ ] 📝 Documentation update
- [ ] 🧪 Test improvement
- [ ] 🔒 Security fix
- [ ] ⬆️ Dependency update

---

## Changes

<!-- List the key changes made in this PR -->

-
-
-

---

## Testing

<!-- Describe how you tested these changes -->

- [ ] Added new tests covering the changes
- [ ] All existing tests pass (`pytest`)
- [ ] Tested manually with a real git diff / PR
- [ ] Tested with provider: <!-- Ollama / OpenAI / Anthropic -->

```bash
# Commands used to test
pytest
inspectra review --dry-run
```

---

## Checklist

- [ ] My code follows the project's code style (`ruff check src/ tests/`)
- [ ] I have added/updated docstrings for new public functions
- [ ] I have updated the README if behaviour changed
- [ ] I have updated `CHANGELOG.md` under `[Unreleased]`
- [ ] I have not committed secrets, API keys, or credentials
- [ ] The PR title is descriptive and follows the format: `type: short description`
      (e.g. `feat: add Gemini provider`, `fix: handle empty diff gracefully`)

---

## Screenshots / Output

<!-- If this changes console output or review format, paste a before/after example -->

<details>
<summary>Before</summary>

```
paste output here
```

</details>

<details>
<summary>After</summary>

```
paste output here
```

</details>

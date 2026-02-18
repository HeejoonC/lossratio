# CLAUDE.md

This file provides guidance for AI assistants (Claude and others) working in this repository.

## Project Overview

**Repository:** `HeejoonC/lossratio`

This repository is currently in its initial state. Update this section as the project takes shape with:
- Purpose and domain context
- Target users / stakeholders
- High-level architecture decisions

> **Note for AI assistants:** This repository has no existing commits or code. When implementing features, establish conventions consistent with the stack chosen and keep this file updated.

---

## Repository Structure

*To be populated as the project grows.* Typical structure to document here:

```
lossratio/
├── CLAUDE.md          # This file
├── README.md          # User-facing documentation
├── src/               # Application source code
├── tests/             # Test suite
├── docs/              # Extended documentation
└── ...
```

---

## Development Workflow

### Branching Strategy

- **Main branch:** `main` (or `master`) — always deployable
- **Feature branches:** `<username>/<short-description>` or `feature/<short-description>`
- **Claude branches:** `claude/<task-id>` — used by AI-assisted sessions

### Commit Conventions

Use clear, imperative commit messages:
```
Add loss ratio calculation module
Fix edge case in premium aggregation
Refactor data ingestion pipeline for clarity
```

Prefer atomic commits (one logical change per commit).

### Pull Requests

- Open a PR for every change going into `main`
- Include a summary of what changed and why
- Link related issues
- Ensure CI passes before merging

---

## Build & Run

*Populate this section once a stack is chosen. Examples:*

### Install dependencies
```bash
# e.g., for a Python project
pip install -r requirements.txt

# e.g., for a Node.js project
npm install
```

### Run the application
```bash
# Add the command to start the project here
```

### Run tests
```bash
# Add the test command here (e.g., pytest, npm test, go test ./...)
```

### Linting / formatting
```bash
# Add lint/format commands here
```

---

## Testing

- Write tests alongside new features (not after the fact)
- Aim for meaningful coverage on business logic (loss ratio calculations, premium/claim aggregation, etc.)
- Unit tests for pure functions; integration tests for data pipelines or API boundaries
- Keep tests fast; mock external I/O where appropriate

---

## Code Conventions

*Update these once a primary language/framework is established.*

- Keep functions small and focused on a single responsibility
- Prefer explicit over implicit
- Document non-obvious domain logic (insurance terminology, actuarial formulas, etc.)
- Avoid magic numbers — name constants clearly (e.g., `MINIMUM_LOSS_RATIO = 0.6`)

### Domain Terminology

Loss ratio is a common insurance/actuarial metric:

| Term | Definition |
|------|-----------|
| Loss Ratio | Incurred losses ÷ Earned premiums |
| Combined Ratio | Loss ratio + Expense ratio |
| Earned Premium | The portion of written premium that covers the elapsed policy period |
| Incurred Loss | Claims paid + Change in reserves |

---

## Environment & Configuration

- Do **not** commit secrets, API keys, or credentials
- Use environment variables or a `.env` file (add `.env` to `.gitignore`)
- Document all required environment variables in a `.env.example` file

---

## AI Assistant Guidelines

When working in this repository as an AI assistant:

1. **Read before editing.** Always read a file before modifying it.
2. **Stay on scope.** Only make changes directly related to the task. Do not refactor unrelated code.
3. **Update this file.** When the project structure, stack, or conventions change, update the relevant sections of `CLAUDE.md`.
4. **Branch discipline.** Work on the designated `claude/<task-id>` branch; never push directly to `main`.
5. **Commit granularly.** Make small, focused commits with descriptive messages.
6. **Document domain logic.** Insurance/actuarial calculations can be non-obvious — add comments explaining the business rule, not just the code.
7. **No secrets.** Never commit credentials, tokens, or sensitive data.
8. **Ask when uncertain.** If requirements are ambiguous, ask before implementing.

---

## Useful References

- Update this section with links to:
  - Internal design docs / ADRs
  - External API documentation
  - Relevant actuarial standards or regulatory references
  - CI/CD pipeline configuration

# Spec Kit — Melos Project

This directory contains the Spec Kit infrastructure for the Melos project.

## Structure

```
.specify/
├── README.md                          # This file
├── extensions.yml                     # Extension hooks configuration
├── memory/
│   └── constitution.md                # The project constitution (governed document)
├── scripts/bash/
│   └── resolve-template.sh            # Template resolver
└── templates/
    └── constitution-template.md       # Constitution template (source of truth)
```

## Files

- **constitution.md**: The active project constitution. This is the governed document that all contributors must follow. It contains principles, rules, and governance procedures. Update it via `/speckit-constitution` command.

- **constitution-template.md**: The template that generates the constitution. Contains placeholder tokens like `[CONSTITUTION_VERSION]`, `[RATIFICATION_DATE]`, etc. Do not commit changes to this file without a clear reason—it is the source template.

- **extensions.yml**: Hooks that run before and after constitution updates. Use this to integrate with git, task management, or other workflows.

- **resolve-template.sh**: The Bash script that resolves templates by reading them and optionally outputting JSON. This is used by `/speckit-constitution` to load the template before filling in values.

## Usage

### View the constitution
```bash
.specify/scripts/bash/resolve-template.sh constitution-template
```

### Amend the constitution
```bash
/speckit-constitution
```

This will guide you through updating the constitution, incrementing the version, and recording the changes.

## Template Tokens

When editing `constitution-template.md`, use these placeholder tokens:
- `[CONSTITUTION_VERSION]` — Semver string (e.g., `1.0.0`, `1.1.0`)
- `[RATIFICATION_DATE]` — ISO date when first adopted (YYYY-MM-DD)
- `[LAST_AMENDED_DATE]` — ISO date of last amendment (YYYY-MM-DD)

## Integration with Project

The constitution is complementary to:
- **AGENTS.md**: Detailed how-to and structure guidance
- **CLAUDE.md**: Redirects to AGENTS.md
- **dev/memory/**: Session-based decision records and context

For operational questions, see AGENTS.md. For engineering governance, see the constitution.

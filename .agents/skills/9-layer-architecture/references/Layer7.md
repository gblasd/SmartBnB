# Layer 7 `.claude/` - The AI coding Assistant Menory Layer

The sevnth layer is:

```Plain Text
.claude/
└── rules/
    ├── code-style.md
    └── testing.md
CLAUDE.md
AGENTS.md
```

The `.claude/` layer gives your AI coding assistant project context before it touches your codebase.

We explain the project.

We explain the architecture.
We explain the folder structure.
We explain coding standards.
We explain testing rules.
We explain what should be avoided.
We explain how features should be added.

- `CLAUDE.md` : This file explains the project to the AI assistant. We can think of like a project instruction manual.

For example:

```Markdown
# Project Context
This is a production-ready AI application.
The system uses:
- RAG pipeline for document-based answers
- semantic cache to reduce repeated model calls
- agents for grading and task decomposition
- prompt registry for versioned prompts
- security guards for input, content, and output
- evaluation layer for offline and online quality checks
- observability for tracing, feedback, and cost tracking
Do not place AI logic directly inside main.py.
Use the existing layer-based architecture.
```


- `AGENTS.md`: This file explains how agents should behave in the project.

For example:

```Markdown
# Agent Rules
Agents should be small and task-specific.
Each agent should:
- have one clear responsibility
- use tools through the tools/ folder
- return structured output
- handle failure safely
- log important decisions
- avoid direct database writes unless required
```

- `.claude/rules/code-style.md`: This file defines coding style rules.

```Markdown
# Code Style Rules
- Keep functions small and readable.
- Do not hardcode prompts inside service files.
- Use type hints wherever possible.
- Keep business logic separate from API routes.
- Use meaningful names for services, agents, and tools.
- Follow the existing folder structure.
```

- `.claude/rules/testing.md`: This file tells the AI assistant how testing should be done.

```Markdown
# Testing Rules
When adding or changing a feature:
- Add or update tests.
- Test retrieval logic separately.
- Test prompt output format.
- Test security guards.
- Test routing decisions.
- Do not remove existing tests unless there is a clear reason.
```

## Why We Need This Layer
The `.claude/` layer exists because AI coding assistants are powerful, but they need direction. Without project context, they can create code that looks correct but damages the architecture. With project context, they become more useful.

* They understand your structure.
* They follow your rules.
* They place code in the right folders.
* They avoid hardcoded prompts.
* They remember testing expectations.
* They behave more like a trained team member.

This layer is not about the AI app answering users. It is about helping developers maintain the AI app safely.
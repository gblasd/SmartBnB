# SmartBnB – AI Agent Guidelines

## Architecture
This project follows the 9-layer AI production architecture:

| Layer | Directory | Purpose |
|-------|-----------|--------|
| 1 | app/services/ | Service orchestration |
| 2 | app/agents/ | AI agents and tools |
| 3 | app/prompts/ | Prompt management |
| 4 | app/security/ | Input/output safety |
| 5 | evaluation/ | AI quality testing |
| 6 | observability/ | Tracing, feedback, costs |
| 7 | .antigravity/ | AI assistant rules |
| 8 | data/ | Data management |
| 9 | tests/ | Automated tests |

## Import Convention
- All internal imports use `app.` prefix

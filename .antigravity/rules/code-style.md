# SmartBnB Code Style Rules

## Architecture
- Follow the 9-layer architecture pattern
- Services orchestrate, agents think, prompts are centralized
- Security filters are applied to all AI inputs and outputs

## Python Style
- Use async/await for all I/O operations
- Type hint all function parameters and return values
- Keep functions under 30 lines
- Use dependency injection over global state

## Imports
- Internal imports use `app.` prefix
- Never use `src.` imports

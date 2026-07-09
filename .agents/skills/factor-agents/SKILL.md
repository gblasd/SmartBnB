---
name: factor-agents
description: A skill that allows agents to perform factorization tasks.
---

# Factor Agents Skill

When you create an agent with the Factor Agents skill consider the following:

## Reviews checklist

1. Natural language to tools calls: 
    - Allow the agents to interpret natural language instructions and convert them into specific tool calls for factorization tasks. This approach creates a clean separation of concerns: the LLM decides what need to be done, while the regular code knows how to do it.

2. Own your prompts (set the stage):
    - Treat the prompt design as a first-class part of the codebase. The skill provides a framework for designing and managing prompts, allowing agents to generate effective prompts for factorization tasks.

3. Own your context window (provides exactly what's needed):
    - Actively design and optimize every token that goes into the context window to maximize the performance of the agent.

4. Tools are just structured outputs (ensures precision):
    - Tool calling is simply an application of Factor 1 - Structured outputs with schemas.

5. Unify execution state & business state.
    - Maintain a single source of truth by unifying the agent's execution state with the applications's business state.

6. Launch/Pause/Resume with simple APIs:
    - Allow the agent's process to be controlled via simple APIs, so you can statrt, pause, or resumen it easily.

7. Contact humans with tools calls:
    - Treathuman interaction as a first-class tool, not an afterthought.

8. Own you control flow:
    - Keep the control flow of the agent's reasoning loop under your explicit control.

9. Compact error into the context window:
    - When operations fail, provide a feedback to the agent so it can adapt its next steps.

10. Small, focused agents:
    - Prefer multiple narrow, focused agents over a monolithic one. Each agent should focus on a single responsability.

11. Trigeer from anywhere:
    - Make your agent channer-agnostic so it can be invoked from multple interfaces.

12. Make your agent a stateless reducer:
    - Design the agent like a stateless function that takes current state and input, then returns the next action and updated state.
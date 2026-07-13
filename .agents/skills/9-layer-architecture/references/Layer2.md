# Layer 2: `agents/` - The Workers That Think and Take Action

`services/` layer is the next important layer after the `services/` layer.

```Plain Text
agents/
├── document_grader.py
├── query_decomposer.py
├── adaptive_router.py
└── tools/
    ├── vector_search.py
    ├── web_search.py
    └── code_search.py
```

This layer handles tasks that need decision-making, tool usage, and self-correction. 

- `document_grader.py`: this agent is responsible for checking and grading documents. Insted of putting all logic inside one prompt, create a separate `document_grader.py` agent. This keeps the grading flow clean, reusable, and easier to improve.
- `query_decomposer.py`: The agent breaks a large task into smaller task. Query decomposition help the AI solver big problems step by step instead of trying to answer everything at one.
- `adaptative_router.py`: The adaptative router is like a smart traffic controller. 
- `adaptative_router.py`: the agent decides the best path based on the user request. The word "adaptative" means it can adjust based on the situation. 
  * If the query is simple, it keeps the flow simple.
  * If the query is complex, it sends it to the right agent or tool.
  * If the query needs documents, it connects with retrieval.
  * If the query look unsafe, it can stop or redirect the request.

This helps avoid unnecesary cost and improves response quality.

`tools/` - keep tools

Tool are external abilities given to agents.
- `vector_search.py`: this tool searches the vector database. 
- `web_search.py`: This tool is useful when the AI needs current or external information. The web search tool helps the agent fetch fresh information when needed.
- `code_search.py`: This is useful for AI coding assistant or developer tools. For example, if the AI need to understand the codebase, it shoul search existing files before making changes. This avoids random code gerenation. The Ai can first check: 
    * Where is this function?
    * Which file contains this logic?
    * What pattern does this project?
    * What tests already exists?
  

## Why We Need This Layer
The `agents/` layer exists because production AI apps need more than one simple response.

* They need planning.
* They need tool usage.
* They need task splitting.
* They need decision-making.
* They need self-correction.

A normal AI call answers a prompt. But an agent can follow a process. That is the difference.


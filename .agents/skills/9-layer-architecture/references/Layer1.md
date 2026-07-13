# Layer 1: `services/` - The Brain of the AI Application.

The purpose of this layer is controls how the user's question moves through the AI system. Think of `services/` like the main control room of the AI app. The real AI app has to do many thing before and after calling the model.

When a user asks a question, this layer decides:

* What is the user really asking?
* Do we need to rewrite the query?
* Do we need to search documents?
* Can we use a cached answer?
* Which AI model or agent should handle this request?
* How should the final response be prepared?



Create the `services/` layer, this is where AI app starts becoming a real system:

```
services/
├── rag_pipeline.py
├── semantic_cache.py
├── conversation.py
├── query_rewriter.py
└── query_router.py
```

- `rag_pipeline.py`: This file handles the RAG flow. Before asking the AI model to answer, we first search our own knowledge base or documents and give the model the right context.
- `semantic_cache.py`: This file helps save time and cost. Sometimes users ask the same or very similar questions again and again. Instead of calling the AI model every time, semantic chache checks wheter a similiar question was already answered before. If yes, it can return the previous userful response.
- `conversation.py`: This file manages conversation memory. When the second question depends on the first one, the AI systems need to unserstand the conversation flow. This file helps manage previous messages, user context, session history, and continuity. 
- `query_rewriter.py`: The file improves the user's raw question before sending it to retrieval or the model. It makes the query cleaner, more specific, and easier for the system to understand. This improves answer a quality a lot.
- `query_router.py`: On this files the query router decides where the request should go.


## Why We Need This Layer
The `services/` layer exists because production AI apps need control. A real AI product needs a proper flow. It needs to understand the request, improve the query, retrieve context, manage memory, reduce cost, choose the right path, and return a reliable answer. That is why `services/` is not just a folder. It is the brain of the AI system.
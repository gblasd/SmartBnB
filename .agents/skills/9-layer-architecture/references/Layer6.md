# Layer 6 `observability/` - Whatching What Happens Inside the AI System

The sixth layer is:
```Plain Text
observability/
├── tracer.py
├── feedback.py
└── cost_tracker.py
```

This layer is about visibility. We need to know why the bad answer happened. The `observability/` layer helps us see, trace, measure, and improve every important step inside the AI system.

For example: 

``Plain Text
Did retrieval fail?
Did the query router choose the wrong path?
Did the prompt produce weak output?
Did the model ignore the context?
Did the response cost too much?
Did the user give negative feedback?
```

- `tarcer.py`: This file tracks the full journey of a user request. For example, when a user asks a question, the system may pass through many stages: 

```Plain Text
User question
↓
Input guard
↓
Query rewriter
↓
Query router
↓
RAG pipeline
↓
Vector search
↓
Prompt generation
↓
Model response
↓
Output filter
↓
Final answer
```

If the final answer is bad, we should not guess what happened. The trace should show us each stage clearly.

For example:
```Plain Text
Query rewritten successfully
Router selected RAG pipeline
Vector search returned 3 documents
Model used prompt version v2
Output filter passed
Final response generated in 4.2 seconds
```

This makes debugging much easier. Without tracing, production AI becomes a black box. With tracing, you can understand what happened inside the system.

- `feedback.py`: This file connects user feedback with system behavior. For example, users may click:

```Plain text
Helpful
Not helpful
Wrong answer
Needs improvement
Report issue
```

But feedback alone is not enough. We need to connect feedback with the exact trace. That means when a user says, “This answer is wrong,” we should know:

```Plain Text
What was the original question?
Which documents were retrieved?
Which prompt version was used?
Which model answered?
How much did it cost?
What response was shown?
```

This helps the team improve the system properly. Instead of randomly changing prompts, we can look at real failed cases and fix the actual problem.

- `cost_tracker.py`: This file tracks how much each AI request costs. when real users start using your app, every model call, embedding call, reranking call, and tool call adds cost. This file can track:

```Plain Text
Cost per user request
Cost per model
Cost per feature
Cost per document upload
Cost per grading task
Cost per RAG query
Monthly AI usage
```
This helps you avoid surprise bills. 

The `observability/` layer exists because production AI systems must be visible.  production system needs to explain how that answer was created.

## Why We Need This Layer
The observability/ layer exists because production AI systems must be visible. You cannot improve what you cannot see.

* If the AI gives a bad answer, you need the full trace.
* If users complain, you need to connect feedback with the exact request.
* If costs increase, you need to know which feature is responsible.

A demo only needs to show an answer. A production system needs to explain how that answer was created.
# Layer 3: `prompt/` - Where AI Instructions Are Managed Properly

The Third layer is: 
```Plain Text
prompts/
├── templates.py
└── registry.py
```

The `prompt/` layer keeps all AI instructions organized, reusable, versiones and easy to improve.

- `templates.py`: This file stores reusable prompt templates. For example:

```python
GRADE_ANSWER_PROMPT = """
You are an expert teacher.Compare the student's answer with the reference answer.
Return:
- marks
- missing points
- wrong points
- feedback
- final score
"""
```

Keeps prompts clean and separate from the main application logic. The code can simply call the required prompt when needed. For example:

```python
from prompts.templates import GRADE_ANSWER_PROMPT
```

- `registry.py`: This files works like prompt manager. It tells the system which prompt should be used for which task. For example:

```Plaint Text
grading task      → grade_answer_prompt_v1
RAG answer        → rag_answer_prompt_v2
query rewrite     → query_rewrite_prompt_v1
safety check      → safety_prompt_v3
summary task      → summary_prompt_v1
```

## Why We Need This Layer
The `prompts/` layer exists because prompts are not temporary strings. They are the behavior engine of your AI app.

A bad prompt can make the system unreliable.
A missing rule can create unsafe output.
An unstructured prompt can break your frontend.
An unversioned prompt can make debugging impossible.

That is why production AI apps should never treat prompts casually. They should be managed properly.
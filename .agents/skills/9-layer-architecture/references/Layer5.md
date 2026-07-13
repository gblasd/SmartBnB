# Layer 5 `evaluation/` - The Testing Layer for AI Quality

The fift layer is:

```Plain Text
evaluation/
├── golden_dataset.json
├── offline_eval.py
├── online_monitor.py
└── eval_results/
```

The `evaluation/` layer checks whether the AI system is actually giving useful, accurate, safe, and consistent answers.

- `golden_dataset.json`: This file contains the best test examples. A golden dataset is a small but high-quality collection of inputs and expected outputs. 
For example, in an AI auto-grading app, it may look like this

```json
[
  {
    "question": "What is photosynthesis?",
    "teacher_answer": "Photosynthesis is the process by which green plants use sunlight, carbon dioxide, and water to make food and release oxygen.",
    "student_answer": "Photosynthesis is when plants make food using sunlight and release oxygen.",
    "expected_marks": 4,
    "total_marks": 5,
    "expected_feedback": "Good answer, but carbon dioxide and water are missing."
  }
]
```

This helps you check whether your AI system is grading properly. Without a golden dataset, you are only guessing that your AI works. With a golden dataset, you can measure it.

- `offline_eval.py`: This file runs evaluation before deployment. For example, before you release a new prompt, new model, or new RAG pipeline, you can run offline evaluation. It checks your system against the golden dataset. It can answer questions like:

```Plain Text
Did the new prompt improve grading?
Did the model become stricter?
Did the feedback quality improve?
Did the JSON output break?
Did the system miss important reference points?
```
Offline evaluation helps catch that before users see the problem.

- `online_monitor.py`: Offline evaluation happens before deployment. Online monitoring happens after deployment. Once real users start using your AI app, you need to watch how the system performs in the real world.

The `online_monitor.py` file can track things like:

```Plain Text
How often does the AI fail?
How often does it return invalid JSON?
How many users give negative feedback?
Which questions produce low-confidence answers?
Which requests cost too much?
Which outputs need human review?
```

The test dataset may be clean. Real users are not. Online monitoring helps you improve the system continuously.

- `eval_results/`: This folder stores evaluation reports. For example:

```Plain Text
eval_results/
├── grading_eval_2026_06_01.json
├── rag_eval_2026_06_02.json
└── prompt_v2_comparison.md
```

These reports helps compare versions. We can track:

```Plain Text
Prompt v1 vs Prompt v2
Model A vs Model B
Old RAG pipeline vs new RAG pipeline
Without reranker vs with reranker
Old grading logic vs improved grading logic
```

This gives you confidence before making changes. 
That is how AI engineering becomes measurable.

## Why We Need This Layer
The evaluation/ layer exists because AI systems can fail silently.

* The app may still return a response.
* The API may still work.
* The frontend may still show an answer.

But the answer may be wrong. That is dangerous. Evaluation helps us check quality before and after deployment. It gives us a way to measure improvement, catch regressions, and build trust in the system. A demo can survive without evaluation. A production AI product cannot.


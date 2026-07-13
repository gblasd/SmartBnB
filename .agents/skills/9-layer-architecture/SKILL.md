---
name: 9-layer-architecture
description: A skill that allows agents to build the architecture for a production-ready AI product. Use when create a AI system new architecture or improve an existing one.
---

# 9-layer AI Production Architecure Skills

When you create a AI system, a real system architecture that follow a production AI product.

## Layers

1. **Layer 1** — `services/` - The Brain of the AI Application. See [references/Layer1.md](references/Layer1.md).
2. **Layer 2** — `agents/` - The Workers That Think and Take Action. See [references/Layer2.md](references/Layer2.md).
3. **Layer 3** — `prompt/` - Where AI Instructions Are Managed Properly. See [references/Layer3.md](references/Layer3.md).
4. **Layer 4** — `security/` - The Safety Gate of the AI System. See [references/Layer4.md](references/Layer4.md).
5. **Layer 5** — `evaluation/` - The Testing Layer for AI Quality. See [references/Layer5.md](references/Layer5.md).
6. **Layer 6** — `observability/` - Whatching What Happens Inside the AI System. See [references/Layer6.md](references/Layer6.md).
7. **Layer 7** — `.claude/` - The AI coding Assistant Menory Layer. See [references/Layer7.md](references/Layer7.md).
8. **Layer 8** — `data/` - Where Raw Knowledge Becomes Usable AI Context. See [references/Layer8.md](references/Layer8.md).
9. **Layer 9** — `test/` - The Layer That Stops Your AI App From Breaking Silently. See [references/Layer9.md](references/Layer9.md).


Inside that build a sigle file like `main.py`, create an architecture decouped the taks on every folder and file.

This is an example of the repository architecture:

```plaint text
production-ai-app/
│
├── app/
│   ├── main.py
│   ├── config.py
│   ├── models.py
│   ├── Dockerfile
│   │
│   ├── components/
│   │   ├── hybrid_retriever.py
│   │   └── reranker.py
│   │
│   ├── services/
│   │   ├── rag_pipeline.py
│   │   ├── semantic_cache.py
│   │   ├── conversation.py
│   │   ├── query_rewriter.py
│   │   └── query_router.py
│   │
│   ├── prompts/
│   │   ├── templates.py
│   │   └── registry.py
│   │
│   ├── agents/
│   │   ├── document_grader.py
│   │   ├── query_decomposer.py
│   │   ├── adaptive_router.py
│   │   └── tools/
│   │       ├── vector_search.py
│   │       ├── web_search.py
│   │       └── code_search.py
│   │
│   └── security/
│       ├── input_guard.py
│       ├── content_filter.py
│       └── output_filter.py
│
├── evaluation/
│   ├── golden_dataset.json
│   ├── offline_eval.py
│   ├── online_monitor.py
│   └── eval_results/
│
├── observability/
│   ├── tracer.py
│   ├── feedback.py
│   └── cost_tracker.py
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── index_config/
│
├── scripts/
│   ├── seed.py
│   ├── migrate.py
│   └── healthcheck.py
│
├── frontend/
│   ├── app.py
│   ├── static/
│   ├── requirements.txt
│   └── Dockerfile
│
├── tests/
│   ├── test_retrieval.py
│   ├── test_cache.py
│   └── test_routing.py
│
├── docs/
│   ├── architecture.md
│   ├── api_reference.md
│   └── deployment.md
│
├── .claude/
│   └── rules/
│       ├── code-style.md
│       └── testing.md
│
├── CLAUDE.md
├── AGENTS.md
├── docker-compose.yml
├── pyproject.toml
└── README.md
``` 

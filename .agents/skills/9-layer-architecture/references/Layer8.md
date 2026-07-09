# Layer 8 `data/` - Where Raw Knowledge Becomes Usable AI Context

The eighth layer is:

```Plain Text
data/
├── raw/
├── processed/
└── index_config/
```

The `data/` layer manages how raw files become clean, structured, searchable knowledge for the AI system.
This layer helps us keep original files safe, clean the extracted content, structure it properly, and prepare it for search.



- `raw/`: this folder stores the original uploaded data.
For example: 
```Palin Text
data/raw/
├── teacher_reference_sheet.pdf
├── student_answer_sheet_01.jpg
├── company_policy.pdf
├── data.csv
└── product_docs.docx
```
This is the untouched version of the file. We keep raw files because sometimes processing may fail, OCR may extract wrong text, or we may need to reprocess the file later with a better model. `raw/` is the original source of truth.

- `processed/`: This folder stores cleaned and structured data. Is where messy files become AI-ready data.

- `index_config/` This folder stores configuration for search and retrieval. For example:

```Plain Text
data/index_config/
├── chunking_rules.json
├── embedding_config.json
└── metadata_schema.json
```

This tells the system how to prepare data for vector search. It may include:

```Plain Text
How large each text chunk should be
Which embedding model to use
What metadata should be stored
How documents should be grouped
Which fields should be searchable
```

This matters because RAG quality depends heavily on how your data is prepared. Bad chunks create bad retrieval. Bad retrieval creates bad AI answers. So this layer directly affects the final output quality.


## Why We Need This Layer

The data/ layer exists because AI is only as good as the context we give it. A powerful model with messy data can still give poor answers. But a normal model with clean, structured, well-indexed data can perform much better. In production AI, data preparation is not a side task. It is one of the core parts of the system. This layer helps us keep original files safe, clean the extracted content, structure it properly, and prepare it for search.
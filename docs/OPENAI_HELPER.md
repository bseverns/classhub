# Homework Helper (OpenAI)

The helper service is a Django app that exposes:

- `GET /helper/healthz`
- `POST /helper/chat`

## Responses API

We use OpenAI's **Responses API** (recommended for new projects), and read `response.output_text` from the SDK.

Reference examples show:

```python
from openai import OpenAI
client = OpenAI()
response = client.responses.create(model="gpt-5.2", input="hello")
print(response.output_text)
```

See OpenAI quickstart + guides for the current shape. citeturn0search0turn0search2turn0search3

## Tutor stance

We bias toward learning:
- ask clarifying questions
- give steps and hints
- avoid producing final answers for graded work

## RAG (planned)

Phase 2 will retrieve relevant snippets from class materials and include citations.

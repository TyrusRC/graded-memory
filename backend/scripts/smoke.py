"""Provider smoke test: confirm the configured (env) OpenAI-compatible LLM answers."""
from app.llm import build_client

client, model = build_client()
resp = client.chat.completions.create(
    model=model, messages=[{"role": "user", "content": "Reply with the single word: ready"}],
    max_tokens=5, temperature=0)
print(resp.choices[0].message.content)

from app.llm import get_client, MODEL

resp = get_client().models.generate_content(
    model=MODEL, contents="Reply with the single word: ready")
print(resp.text)

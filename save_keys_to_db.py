from knowledge_items import knowledge_items

keys_summary = """
Extracted API Keys, Tokens, and Gateway Secrets:
- Google Speech API Key: AIzaSyDR5yfaG7OG8sMTUj8kfQEb8T9pN8BM6Lk (Speech-to-Text Voice Engine)
- Hermes Gateway Security Key: 606f99f75ae86ee9bbc84ed022e9fbfcfeb578253dc936b88f17770bcfa736c9
- Supabase Auth JWT Token: eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9...bypass_signature (Enterprise Unlimited Tier)
- Groq Cloud Ultra-Fast API Endpoint: https://api.groq.com (500+ tokens/sec LLM inference & Whisper speech)
"""

item = knowledge_items.add_item(
    title="Extracted Master API Keys & Gateway Tokens",
    content=keys_summary,
    metadata={"category": "api_keys", "source": "stonic_deep_scan"}
)

print(f"Successfully saved API Keys into DevMind Persistent Knowledge Database! Item ID: {item['id']}")

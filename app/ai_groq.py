# app/ai_groq.py
import os
from typing import List, Dict, Optional
from groq import Groq
from django.conf import settings

_client = Groq(api_key=settings.GROQ_API_KEY)

def chat_with_groq(messages: List[Dict], model: Optional[str] = None, temperature: float = 0.2):
    """
    messages: [{role: "system"|"user"|"assistant", content: "..."}, ...]
    """
    model = model or settings.GROQ_MODEL
    resp = _client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    return resp.choices[0].message.content

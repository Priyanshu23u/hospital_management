# app/ai_groq.py
import os
from typing import List, Dict, Optional
from groq import Groq
from django.conf import settings

# Initialize Groq client
try:
    _client = Groq(api_key=settings.GROQ_API_KEY)
except Exception as e:
    print(f"Warning: Failed to initialize Groq client: {e}")
    _client = None

def chat_with_groq(messages: List[Dict], model: Optional[str] = None, temperature: float = 0.2, max_tokens: int = 1000):
    """
    Chat with Groq AI model with improved error handling
    
    Args:
        messages: List of message dictionaries with 'role' and 'content' keys
        model: Model name to use (defaults to settings.GROQ_MODEL)
        temperature: Sampling temperature (0.0 to 2.0)
        max_tokens: Maximum tokens in response
    
    Returns:
        str: AI response content
    """
    if not _client:
        raise Exception("Groq client not initialized. Please check your API key.")
    
    if not messages:
        raise ValueError("Messages list cannot be empty")
    
    # Validate message format
    for msg in messages:
        if not isinstance(msg, dict) or 'role' not in msg or 'content' not in msg:
            raise ValueError("Each message must be a dict with 'role' and 'content' keys")
        if msg['role'] not in ['system', 'user', 'assistant']:
            raise ValueError("Message role must be 'system', 'user', or 'assistant'")
    
    model = model or getattr(settings, 'GROQ_MODEL', 'llama3-70b-8192')
    
    try:
        response = _client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=1,
            stream=False
        )
        
        # Handle different response formats from Groq API
        try:
            # Method 1: Standard OpenAI-like response format
            if hasattr(response, 'choices') and response.choices:
                choice = response.choices[0]
                if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                    return choice.message.content
                elif isinstance(choice, dict) and 'message' in choice:
                    return choice['message'].get('content', '')
            
            # Method 2: Response is a list
            elif isinstance(response, list) and response:
                first_item = response[0]
                if isinstance(first_item, dict):
                    if 'message' in first_item:
                        return first_item['message'].get('content', '')
                    elif 'content' in first_item:
                        return first_item['content']
            
            # Method 3: Direct string response
            elif isinstance(response, str):
                return response
            
            # Method 4: Dict response
            elif isinstance(response, dict):
                if 'content' in response:
                    return response['content']
                elif 'message' in response:
                    return response['message'].get('content', '')
                elif 'text' in response:
                    return response['text']
            
            # Fallback: Convert to string
            return str(response)
            
        except Exception as parse_error:
            # Log the actual response structure for debugging
            print(f"Groq response parse error: {parse_error}")
            print(f"Response type: {type(response)}")
            print(f"Response content: {response}")
            raise Exception(f"Unable to parse Groq response: {parse_error}")
            
    except Exception as e:
        if "parse" in str(e).lower():
            raise e  # Re-raise parse errors as-is
        else:
            raise Exception(f"Groq API error: {str(e)}")

def validate_api_key():
    """
    Validate if the Groq API key is working
    """
    try:
        if not _client:
            return False
            
        # Test with a simple message
        test_messages = [
            {"role": "user", "content": "Hello, respond with 'OK'"}
        ]
        
        response = chat_with_groq(test_messages, max_tokens=10)
        return bool(response and len(response.strip()) > 0)
        
    except Exception as e:
        print(f"API key validation failed: {e}")
        return False

def get_available_models():
    """
    Get list of available Groq models
    """
    try:
        if not _client:
            return []
        
        models = _client.models.list()
        if hasattr(models, 'data'):
            return [model.id for model in models.data]
        elif isinstance(models, list):
            return [model.get('id', 'unknown') for model in models if isinstance(model, dict)]
        else:
            return ['llama3-70b-8192', 'llama3-8b-8192', 'mixtral-8x7b-32768']
    except Exception as e:
        print(f"Error fetching models: {e}")
        return ['llama3-70b-8192', 'llama3-8b-8192', 'mixtral-8x7b-32768']

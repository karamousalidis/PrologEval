import os
import time
import re
import logging
from typing import Dict, Any, Union
import openai
import textstat

# Initialize OpenRouter Client
def get_client() -> openai.OpenAI:
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    return openai.OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY
    )

def extract_prolog_comments(text: str) -> str:
    """Match single-line comments (%) and block comments (/* ... */)"""
    single_line_comments = re.findall(r'%(.*)', text)
    block_comments = re.findall(r'/\*(.*?)\*/', text, re.DOTALL)
    
    all_comments = " ".join(single_line_comments) + " " + " ".join(block_comments)
    return all_comments.strip()

def generate_openrouter_response(model_id: str, prompt: str) -> Dict[str, Any]:
    """Generates a response from OpenRouter and calculates metrics."""
    client = get_client()
    try:
        start_time = time.time()
        completion = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": prompt}]
        )
        end_time = time.time()
        
        response_message = completion.choices[0].message
        response_text = response_message.content if response_message.content else ""
        
        prompt_tokens = completion.usage.prompt_tokens if completion.usage else 0
        completion_tokens = completion.usage.completion_tokens if completion.usage else 0
        
        comments = extract_prolog_comments(response_text)
        readability = textstat.flesch_reading_ease(comments) if comments else "N/A (No comments found)" # type: ignore
        
        return {
            "text": response_text,
            "time_taken": end_time - start_time,
            "tokens_prompt": prompt_tokens,
            "tokens_completion": completion_tokens,
            "readability_score": readability
        }
    except Exception as e:
        logging.error(f"Error generating OpenRouter response: {e}", exc_info=True)
        return {"error": f"Error generating response: {str(e)}"}

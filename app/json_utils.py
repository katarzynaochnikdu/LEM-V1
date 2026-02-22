"""
Narzędzia do ekstrakcji JSON z odpowiedzi LLM.
Lokalne modele (Qwen, Mistral) nie zawsze zwracają czysty JSON.
"""

import json
import re


def extract_json_from_text(text: str) -> dict:
    """
    Wyciąga obiekt JSON z tekstu odpowiedzi LLM.
    Obsługuje odpowiedzi z markdown code blocks, dodatkowym tekstem itp.
    
    Args:
        text: Surowy tekst z odpowiedzi LLM
        
    Returns:
        Sparsowany dict z JSON
        
    Raises:
        ValueError: Jeśli nie da się wyciągnąć JSON
    """
    if not text or not text.strip():
        raise ValueError("Pusta odpowiedź z LLM")
    
    text = text.strip()
    
    # 1. Spróbuj bezpośrednio sparsować
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # 2. Wyciągnij JSON z markdown code block ```json ... ```
    json_block = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
    if json_block:
        try:
            return json.loads(json_block.group(1).strip())
        except json.JSONDecodeError:
            pass
    
    # 3. Znajdź pierwszy { ... } w tekście
    brace_start = text.find('{')
    if brace_start != -1:
        depth = 0
        for i in range(brace_start, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    candidate = text[brace_start:i+1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        pass
                    break
    
    # 4. Próba naprawienia częstych problemów
    cleaned = text
    # Usuń trailing comma przed }
    cleaned = re.sub(r',\s*}', '}', cleaned)
    # Usuń trailing comma przed ]
    cleaned = re.sub(r',\s*]', ']', cleaned)
    
    brace_start = cleaned.find('{')
    if brace_start != -1:
        brace_end = cleaned.rfind('}')
        if brace_end != -1:
            candidate = cleaned[brace_start:brace_end+1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass
    
    raise ValueError(f"Nie udało się wyciągnąć JSON z odpowiedzi LLM. Początek odpowiedzi: {text[:200]}")

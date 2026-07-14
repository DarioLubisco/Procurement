import os
from fastapi import APIRouter, Request, HTTPException
import httpx
import traceback
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

router = APIRouter(prefix="/api/webhook", tags=["Webhook"])

# Simple memory structure: session_id -> list of messages
session_memory: Dict[str, List[Dict[str, str]]] = {}

class N8NPayload(BaseModel):
    source: str
    session_id: str
    text: Optional[str] = None
    audio_base64: Optional[str] = None
    image_base64: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

async def call_gemini_openrouter(messages: List[Dict[str, str]]) -> str:
    # Use OpenRouter to call Gemini 2.0 Flash Lite
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        print("Warning: OPENROUTER_API_KEY not found in environment")
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://synapse.local", 
        "X-Title": "agente:equivalencias",
    }
    payload = {
        "model": "google/gemini-2.0-flash-lite-001",
        "messages": messages,
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload, timeout=60.0)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

@router.post("/n8n")
async def receive_n8n_webhook(payload: N8NPayload):
    try:
        session_id = payload.session_id
        source = payload.source
        
        # Initialize memory if it doesn't exist
        if session_id not in session_memory:
            session_memory[session_id] = [
                {
                    "role": "system",
                    "content": "Eres el agente:equivalencias. Tu trabajo es asistir amablemente y de forma clara."
                }
            ]
        
        # Handle Multimodal logic here
        # For this implementation, if there is audio or image, we add it to the content
        user_content = []
        if payload.text:
            user_content.append({"type": "text", "text": payload.text})
            
        if payload.image_base64:
            # Assuming it's already properly formatted or just raw base64. 
            # OpenRouter format for images
            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{payload.image_base64}"
                }
            })
            
        if payload.audio_base64:
             # NOTE: OpenRouter / Gemini might have specific formats for audio.
             # In some implementations it's handled via text/transcription first, 
             # but Gemini 2.0 supports audio directly.
             # We assume here we can pass it, or we handle it if needed.
             pass # Will implement audio handling logic based on actual requirements
             
        if not user_content:
            user_content.append({"type": "text", "text": "(Mensaje vacío)"})

        # Append user message
        session_memory[session_id].append({
            "role": "user",
            "content": user_content
        })
        
        # Enforce memory limit (keep system prompt + last 10 messages)
        if len(session_memory[session_id]) > 11:
            session_memory[session_id] = [session_memory[session_id][0]] + session_memory[session_id][-10:]

        # Simple Routing Logic based on Source
        # If source is chatwoot, we might answer FAQs. 
        # If web_ui, might be operational. 
        # In a real scenario we could route to different agents here.
        if source == "chatwoot":
             print(f"[{session_id}] Ruteando petición a sub-agente FAQ (Chatwoot)")
        elif source == "web_ui":
             print(f"[{session_id}] Ruteando petición a sub-agente Operativo (Web UI)")

        # Call LLM
        response_text = await call_gemini_openrouter(session_memory[session_id])
        
        # Append assistant response
        session_memory[session_id].append({
            "role": "assistant",
            "content": response_text
        })
        
        return {
            "status": "success",
            "response": response_text,
            "session_id": session_id,
            "source": source
        }
        
    except Exception as e:
        print(f"Error in webhook: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

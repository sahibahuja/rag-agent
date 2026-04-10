from pydantic import BaseModel
from typing import List, Dict

class StorePayload(BaseModel):
    file_path: str
    metadata: Dict[str, str] = {}

class Message(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str

class ChatPayload(BaseModel):
    question: str
    history: List[Message] = []
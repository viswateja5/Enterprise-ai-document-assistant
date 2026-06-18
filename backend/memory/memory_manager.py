from typing import Dict
from langchain_classic.memory import ConversationBufferMemory

# Global in-memory dictionary storing session memory objects
_session_memories: Dict[str, ConversationBufferMemory] = {}

def get_session_memory(session_id: str) -> ConversationBufferMemory:
    """
    Retrieves or creates a ConversationBufferMemory instance for the given session_id.
    
    Args:
        session_id (str): Unique identifier for the conversation session.
        
    Returns:
        ConversationBufferMemory: Conversation buffer memory object.
    """
    if session_id not in _session_memories:
        _session_memories[session_id] = ConversationBufferMemory(
            memory_key="chat_history",
            output_key="answer",
            return_messages=True
        )
    return _session_memories[session_id]

def clear_session_memory(session_id: str) -> None:
    """
    Deletes the memory buffer for a specific session.
    """
    if session_id in _session_memories:
        del _session_memories[session_id]

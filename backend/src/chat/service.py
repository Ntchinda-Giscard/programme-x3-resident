
from datetime import datetime
from sqlalchemy.orm import Session
from src.database.models import Conversation, ChatMessage
from src.core.rag import rag_instance
import uuid

async def process_chat_message(db: Session, query: str, conversation_id: str = None):
    # 1. Get or create conversation
    if not conversation_id:
        conversation_id = str(uuid.uuid4())
        conv = Conversation(id=conversation_id, title=query[:50], created_at=datetime.now().isoformat())
        db.add(conv)
        db.commit()
    else:
        # Check if conversation exists
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conv:
            conv = Conversation(id=conversation_id, title=query[:50], created_at=datetime.now().isoformat())
            db.add(conv)
            db.commit()

    # 2. Save user message
    user_msg = ChatMessage(
        role="user",
        content=query,
        timestamp=datetime.now().isoformat(),
        conversation_id=conversation_id
    )
    db.add(user_msg)
    db.commit()

    # 3. Get history (last 10 messages)
    history_msgs = db.query(ChatMessage).filter(ChatMessage.conversation_id == conversation_id).order_by(ChatMessage.timestamp.desc()).limit(11).all()
    history_msgs.reverse() # chronologique
    
    # Format history for RAG if needed (skipped for now for simplicity, but passed to prompt later)
    
    # 4. Get response from RAG
    # We include a reminder to the RAG about historical context if we want, 
    # but the SageRAG query method currently handles simple query.
    response_content = await rag_instance.query(query)

    # 5. Save assistant message
    assistant_msg = ChatMessage(
        role="assistant",
        content=response_content,
        timestamp=datetime.now().isoformat(),
        conversation_id=conversation_id
    )
    db.add(assistant_msg)
    db.commit()

    return {
        "response": response_content,
        "conversation_id": conversation_id
    }

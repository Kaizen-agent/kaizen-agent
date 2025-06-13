from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime

@dataclass
class ConversationState:
    """Tracks the state of the travel planning conversation."""
    destination: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    preferences: List[str] = field(default_factory=list)
    budget: Optional[str] = None
    current_intent: Optional[str] = None
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    
    def update_history(self, role: str, content: str) -> None:
        """Add a message to the conversation history."""
        self.conversation_history.append({"role": role, "content": content})
    
    def get_history(self) -> List[Dict[str, str]]:
        """Get the full conversation history."""
        return self.conversation_history
    
    def is_complete(self) -> bool:
        """Check if we have all necessary information for planning."""
        return all([
            self.destination,
            self.start_date,
            self.end_date,
            self.preferences,
            self.budget
        ]) 
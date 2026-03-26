"""
Egyszerű kliensoldali adatmodellek.
"""

from dataclasses import dataclass


@dataclass
class ChatMessage:
    """Egy bejövő vagy megjelenített chat üzenet."""
    message_id: int
    sender: str
    sender_machine: str
    text: str
    important: bool
    timestamp: str
    direction: str = "in"
    read_sent: bool = False
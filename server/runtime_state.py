from typing import Dict, List
from fastapi import WebSocket

online_clients: Dict[str, List[WebSocket]] = {}
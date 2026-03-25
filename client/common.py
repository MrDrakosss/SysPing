import json
import socket
import urllib.request

SERVER_HTTP = "http://192.168.1.10:8080"
SERVER_WS = "ws://192.168.1.10:8080/ws/client"
MACHINE_NAME = socket.gethostname()

def http_get_json(path: str):
    req = urllib.request.Request(f"{SERVER_HTTP}{path}", method="GET")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))

def http_patch_json(path: str, payload: dict):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{SERVER_HTTP}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="PATCH",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))

def http_post_json(path: str, payload: dict):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{SERVER_HTTP}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))

def http_delete(path: str):
    req = urllib.request.Request(f"{SERVER_HTTP}{path}", method="DELETE")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))
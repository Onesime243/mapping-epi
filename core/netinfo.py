"""Adresses réseau pour partager la version web sur le réseau local."""
from __future__ import annotations

import socket
from typing import List

WEB_PORT = 8050


def lan_ips() -> List[str]:
    ips = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))          # aucune donnée n'est envoyée
        ips.add(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    return sorted(ip for ip in ips if not ip.startswith("127."))


def lan_urls(port: int = WEB_PORT) -> List[str]:
    return [f"http://{ip}:{port}" for ip in lan_ips()] or ["(aucun réseau détecté)"]

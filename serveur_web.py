"""Démarre la version web de Mapping Épi sur le réseau local.

    python serveur_web.py                 # port 8050, accessible depuis le réseau (Wi-Fi)
    python serveur_web.py --port 9000
    python serveur_web.py --local         # uniquement sur cet ordinateur

Au premier lancement, ouvrez l'adresse affichée pour créer le compte administrateur.
"""
from __future__ import annotations

import argparse
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from core.netinfo import WEB_PORT, lan_urls  # noqa: E402
from core.paths import data_dir  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Serveur web Mapping Épi")
    ap.add_argument("--port", type=int, default=WEB_PORT)
    ap.add_argument("--local", action="store_true", help="n'accepter que les connexions de cet ordinateur")
    ap.add_argument("--public", action="store_true",
                    help="mode serveur internet : écoute 127.0.0.1 derrière Caddy (HTTPS), cookies sécurisés")
    args = ap.parse_args()
    (ROOT / "logs").mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s : %(message)s",
                        handlers=[RotatingFileHandler(ROOT / "logs" / "web.log", maxBytes=2_000_000, backupCount=3,
                                                      encoding="utf-8"), logging.StreamHandler()])
    import os
    if args.public:
        os.environ["MAPPING_EPI_PUBLIC"] = "1"
    from web.server import create_app
    app = create_app()
    host = "127.0.0.1" if (args.local or args.public) else "0.0.0.0"
    print("\n  Mapping Épi — version web")
    print(f"  Sur cet ordinateur : http://localhost:{args.port}")
    if not (args.local or args.public):
        for u in lan_urls(args.port):
            print(f"  Sur le réseau      : {u}")
    print(f"  Données locales    : {data_dir()}")
    print("  (Ctrl+C pour arrêter)\n", flush=True)
    try:
        from waitress import serve
        serve(app, host=host, port=args.port, threads=8, trusted_proxy="127.0.0.1" if args.public else None,
              trusted_proxy_headers={"x-forwarded-for", "x-forwarded-proto", "x-forwarded-host"} if args.public else None,
              clear_untrusted_proxy_headers=True)
    except ImportError:
        app.run(host=host, port=args.port, threaded=True, debug=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())

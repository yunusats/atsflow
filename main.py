import argparse
import os
import sys
import threading
import webbrowser

import core

APP_NAME = "AtsFlow"
APP_VERSION = "1.0"


def app_dir():
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


def base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def main():
    parser = argparse.ArgumentParser(description="AtsFlow - yerel ag dosya ve muzik akisi")
    parser.add_argument("--dir", default="shared", help="paylasilacak klasor (varsayilan: shared)")
    parser.add_argument("--port", type=int, default=0, help="HTTP portu (varsayilan: otomatik)")
    parser.add_argument("--no-browser", action="store_true", help="tarayiciyi otomatik acma")
    parser.add_argument("--no-gui", action="store_true", help="masaustu pencere olmadan calistir")
    args = parser.parse_args()

    web_dir = os.path.join(app_dir(), "web")
    assets_dir = os.path.join(app_dir(), "assets")
    shared_dir = os.path.abspath(args.dir)
    os.makedirs(shared_dir, exist_ok=True)

    probe = core.make_server(shared_dir, web_dir, None, args.port, assets_dir)
    port = probe.server_address[1]
    probe.server_close()

    discovery = core.Discovery(port)
    server = core.make_server(shared_dir, web_dir, discovery, port, assets_dir)
    discovery.start()

    threading.Thread(target=server.serve_forever, daemon=True).start()

    url = f"http://127.0.0.1:{port}/"
    print("=" * 52)
    print(f" {APP_NAME} v{APP_VERSION} calisiyor")
    print(f"  Bilgisayar adi : {discovery.name}")
    print(f"  Web arayuzu    : {url}")
    print(f"  Paylasim klsr. : {shared_dir}")
    print("  Kapatmak icin  : Ctrl+C")
    print("=" * 52)

    if not args.no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        if args.no_gui:
            while True:
                threading.Event().wait(3600)
        else:
            import gui

            gui.run(discovery, server, shared_dir, url, assets_dir)
    except KeyboardInterrupt:
        pass
    finally:
        discovery.stop()
        server.shutdown()
        print("\nKapatildi.")


if __name__ == "__main__":
    main()

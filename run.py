import os
import socket
from app import app

def get_available_port(default_port=8000):
    port = int(os.environ.get('PORT', default_port))
    # Test if port is available
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(('127.0.0.1', port))
        s.close()
        return port
    except Exception:
        # Fallback to alternate ports if busy or restricted
        for alt_port in [8000, 5001, 8080, 8888]:
            s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s2.bind(('127.0.0.1', alt_port))
                s2.close()
                return alt_port
            except Exception:
                continue
    return port

if __name__ == '__main__':
    port = get_available_port(default_port=8000)
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() in ['1', 'true']
    print(f"==================================================")
    print(f"  eDoc Doctor Appointment System (Flask)")
    print(f"  Running locally at: http://127.0.0.1:{port}")
    print(f"==================================================")
    app.run(host='127.0.0.1', port=port, debug=debug)

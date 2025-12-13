import socket, threading, os, time, mimetypes

HTTP_PORT = 8000
UDP_PORT  = 9000

# Basic ThreadPool
class ThreadPool:
    def __init__(self, n):
        from queue import Queue
        self.q = Queue()
        for _ in range(n):
            threading.Thread(target=self.worker, daemon=True).start()
    def worker(self):
        while True:
            conn, addr = self.q.get()
            handle_http(conn, addr)
    def add(self, conn, addr):
        self.q.put((conn, addr))

# HTTP Handler
def mime(path):
    t, _ = mimetypes.guess_type(path)
    return t or "application/octet-stream"

def handle_http(conn, addr):
    t0 = time.time()
    try:
        req = conn.recv(4096).decode(errors="ignore")
        if not req:
            conn.close(); return

        path = req.split("\n")[0].split()[1]
        path = "index.html" if path == "/" else path.lstrip("/")

        if not os.path.exists(path):
            body = b"<h1>404 Not Found</h1>"
            status = "404 Not Found"
            ctype  = "text/html"
        else:
            body = open(path, "rb").read()
            status = "200 OK"
            ctype = mime(path)

        header = (
            f"HTTP/1.1 {status}\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Content-Type: {ctype}\r\n"
            "Connection: close\r\n\r\n"
        ).encode()

        conn.sendall(header + body)

    except Exception as e:
        print("HTTP error:", e)
    finally:
        conn.close()
        print(f"[HTTP] {addr} | {path} | {status} | {len(body)}B | {(time.time()-t0):.4f}s")

# HTTP servers
def start_http_single():
    s = socket.socket()
    s.bind(("0.0.0.0", HTTP_PORT))
    s.listen(5)
    print("[HTTP SINGLE] running")
    while True:
        c, a = s.accept()
        handle_http(c, a)

def start_http_threaded(n=5):
    s = socket.socket()
    s.bind(("0.0.0.0", HTTP_PORT))
    s.listen(20)
    pool = ThreadPool(n)
    print(f"[HTTP THREADED] running workers={n}")
    while True:
        c, a = s.accept()
        pool.add(c, a)

# UDP Echo
def start_udp():
    u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    u.bind(("0.0.0.0", UDP_PORT))
    print("[UDP] running")
    while True:
        data, addr = u.recvfrom(65535)
        print(f"[UDP] {addr} : {data[:30]}")
        u.sendto(data, addr)

# Main
if __name__ == "__main__":
    print("1) HTTP Single\n2) HTTP Threaded\n3) Exit")
    c = input("Mode: ").strip()
    if c == "1":
        threading.Thread(target=start_http_single, daemon=True).start()
    elif c == "2":
        workers = int(input("Workers: ") or "5")
        threading.Thread(target=start_http_threaded, args=(workers,), daemon=True).start()
    else:
        exit()

    threading.Thread(target=start_udp, daemon=True).start()
    print("Server berjalan...\n")

    while True:
        time.sleep(1)
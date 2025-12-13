import socket, threading, time, datetime
from queue import Queue

PROXY_TCP_PORT = 8080
PROXY_UDP_PORT = 9090
SERVER_IP = "127.0.0.1"
SERVER_TCP_PORT = 8000
SERVER_UDP_PORT = 9000

CACHE_TTL = 3
DELAY = 0.15
THREADS = 10

cache = {}

def cache_get(p):
    if p in cache:
        resp, t = cache[p]
        if time.time() - t <= CACHE_TTL:
            return resp
    return None

def cache_put(p, r):
    cache[p] = (r, time.time())

# ThreadPool
class ThreadPool:
    def __init__(self, n):
        self.q = Queue()
        for _ in range(n):
            threading.Thread(target=self.w, daemon=True).start()
    def w(self):
        while True:
            c, a = self.q.get()
            handle_tcp(c, a)
    def add(self, c, a):
        self.q.put((c, a))

# TCP Proxy
def handle_tcp(cli, addr):
    try:
        req = cli.recv(4096)
        if not req:
            cli.close(); return

        line = req.decode(errors="ignore").split("\n")[0]
        parts = line.split()
        path = parts[1] if len(parts) > 1 else "/"

        t0 = datetime.datetime.now()

        resp = cache_get(path)
        hit = resp is not None

        if not hit:
            s = socket.socket()
            s.settimeout(5)
            s.connect((SERVER_IP, SERVER_TCP_PORT))
            s.sendall(req)

            chunks = []
            while True:
                try:
                    d = s.recv(4096)
                    if not d: break
                    chunks.append(d)
                except:
                    break
            s.close()
            resp = b"".join(chunks)
            cache_put(path, resp)

        time.sleep(DELAY)
        cli.sendall(resp)
        dur = (datetime.datetime.now() - t0).total_seconds()
        print(f"[TCP] {addr} {path} {'HIT' if hit else 'MISS'} {len(resp)}B {dur:.4f}s")

    except Exception as e:
        print("TCP err:", e)
    finally:
        cli.close()

def start_tcp():
    s = socket.socket()
    s.bind(("0.0.0.0", PROXY_TCP_PORT))
    s.listen(20)
    print("[PROXY TCP] running")
    pool = ThreadPool(THREADS)
    while True:
        c, a = s.accept()
        pool.add(c, a)

# UDP Proxy
def start_udp():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("0.0.0.0", PROXY_UDP_PORT))
    print("[PROXY UDP] running")

    while True:
        data, addr = s.recvfrom(2048)

        u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        u.sendto(data, (SERVER_IP, SERVER_UDP_PORT))
        u.settimeout(2)
        try:
            resp, _ = u.recvfrom(2048)
            time.sleep(DELAY)
            s.sendto(resp, addr)
            print(f"[UDP] {addr} {len(resp)}B")
        except:
            pass

# Main
if __name__ == "__main__":
    print("\n=== PROXY START ===")
    threading.Thread(target=start_tcp, daemon=True).start()
    threading.Thread(target=start_udp, daemon=True).start()
    while True: time.sleep(1)
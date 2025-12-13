import socket, time, csv, threading, datetime

PROXY_IP = "127.0.0.1"
TCP_PORT = 8080
UDP_PORT = 9090

def ts():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def recv_all(sock):
    sock.settimeout(2)
    out = []
    while True:
        try:
            d = sock.recv(4096)
            if not d: break
            out.append(d)
        except:
            break
    return b"".join(out)

# 1) HTTP Test
def http_test():
    print("\n[HTTP Test] GET / via proxy")
    s = socket.socket()
    s.settimeout(5)
    t0 = time.time()
    s.connect((PROXY_IP, TCP_PORT))
    s.sendall(b"GET / HTTP/1.1\r\nHost:x\r\nConnection:close\r\n\r\n")

    resp = recv_all(s)
    s.close()
    t1 = time.time()

    body = resp.split(b"\r\n\r\n", 1)[1] if b"\r\n\r\n" in resp else resp
    open("output.html", "wb").write(body)

    print("Saved to output.html")
    print(f"RTT: {(t1-t0)*1000:.2f} ms | {len(resp)} bytes\n")

# 2) UDP QoS CSV
def udp_qos():
    print("\n[UDP QoS]")
    n = int(input("Packets (default 20): ") or "20")
    interval = 0.1
    psize = 64

    fname = f"udp_qos_{ts()}.csv"
    print("Saving to", fname)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2)

    lats = []
    lost = 0
    tstart = time.time()

    for i in range(n):
        payload = f"{i}|".encode() + b"x" * max(0, psize - len(f"{i}|"))
        ts_send = time.time()

        try: sock.sendto(payload, (PROXY_IP, UDP_PORT))
        except:
            lost += 1
            continue

        try:
            d, _ = sock.recvfrom(65535)
            lat = (time.time() - ts_send) * 1000
            lats.append(lat)
            print(f"[{i}] {lat:.2f} ms")
        except:
            lost += 1
            print(f"[{i}] LOST")

        time.sleep(interval)

    sock.close()

    total = time.time() - tstart
    received = n - lost
    avg_lat = sum(lats)/len(lats) if lats else 0
    jitter = sum(abs(lats[i]-lats[i-1]) for i in range(1,len(lats))) / (len(lats)-1) if len(lats)>1 else 0
    loss_pct = (lost/n)*100
    data_received_bits = received * psize * 8
    throughput_bps = data_received_bits / total if total > 0 else 0
    timestamp_now = ts()

    with open(fname, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metric","value"])
        w.writerow(["timestamp", timestamp_now])
        w.writerow(["packet_sent", n])
        w.writerow(["packet_received", received])
        w.writerow(["packet_loss_percent", f"{loss_pct:.2f}"])
        w.writerow(["avg_latency_ms", f"{avg_lat:.2f}"])
        w.writerow(["jitter_ms", f"{jitter:.2f}"])
        w.writerow(["data_received_bits", data_received_bits])
        w.writerow(["total_time_seconds", f"{total:.6f}"])
        w.writerow(["throughput_bps", f"{throughput_bps:.6f}"])

    print("\nSemua hasil telah disimpan ke CSV.\n")

# 3) Multi Client HTTP
def worker(i, res):
    try:
        s = socket.socket()
        t0 = time.time()
        s.connect((PROXY_IP, TCP_PORT))
        s.sendall(b"GET / HTTP/1.1\r\nHost:x\r\nConnection:close\r\n\r\n")
        r = recv_all(s)
        t = (time.time()-t0)
        print(f"[C{i}] OK {len(r)}B {t*1000:.2f}ms")
        res.append((True,t,len(r)))
    except:
        print(f"[C{i}] FAIL")
        res.append((False,0,0))

def multi():
    print("\n[Multi Client Test]")
    N = 5
    res = []
    th = []
    for i in range(N):
        t=threading.Thread(target=worker,args=(i,res))
        t.start()
        th.append(t)
    for t in th: t.join()

    ok = [r for r in res if r[0]]
    if ok:
        avg = sum(r[1] for r in ok)/len(ok)
        total = sum(r[2] for r in ok)
        print("\nAvg latency:", avg*1000,"ms")
        print("Total bytes:", total)
    else:
        print("All failed")

# Main
def menu():
    print("\n1) HTTP Test ")
    print("2) UDP QoS (CSV)")
    print("3) Multi Client Test")
    print("4) Exit")

def main():
    while True:
        menu()
        c = input("Choice: ").strip()
        if c=="1": http_test()
        elif c=="2": udp_qos()
        elif c=="3": multi()
        else: break

if __name__ == "__main__":
    main()
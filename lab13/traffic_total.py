import psutil
import time

if __name__ == "__main__":
    prev = psutil.net_io_counters()
    print("Ctrl+C to stop")
    while True:
        time.sleep(1)
        cur = psutil.net_io_counters()
        in_b = cur.bytes_recv - prev.bytes_recv
        out_b = cur.bytes_sent - prev.bytes_sent
        print(f"+{in_b} B in, +{out_b} B out")
        prev = cur 
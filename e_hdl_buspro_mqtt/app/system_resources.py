"""On-demand metrics only: no history, tokens, hardware IDs or extra database."""
import os
from pathlib import Path
import shutil
import threading
import time


class Resources:
    def __init__(self, data_path="/data"):
        self.data_path = data_path
        self.started = time.monotonic()
        self.previous = None
        self.lock = threading.Lock()

    @staticmethod
    def fields(path):
        try:
            return {key.strip(): value.strip() for line in Path(path).read_text().splitlines() if ":" in line
                    for key, value in [line.split(":", 1)]}
        except OSError:
            return {}

    @staticmethod
    def kib(value):
        try:
            return int(value.split()[0]) * 1024
        except (ValueError, IndexError, AttributeError):
            return None

    def snapshot(self):
        with self.lock:
            now, process = time.monotonic(), time.process_time()
            ticks = None
            try:
                values = [int(v) for v in Path("/proc/stat").read_text().splitlines()[0].split()[1:9]]
                ticks = (sum(values), values[3] + values[4])
            except (OSError, ValueError, IndexError):
                pass
            host_percent = process_percent = None
            if self.previous:
                prior_time, prior_process, prior_ticks = self.previous
                elapsed = now - prior_time
                if elapsed > .1:
                    process_percent = round(100 * (process - prior_process) / elapsed, 2)
                if ticks and prior_ticks and ticks[0] > prior_ticks[0]:
                    host_percent = round(100 * (1 - (ticks[1] - prior_ticks[1]) / (ticks[0] - prior_ticks[0])), 2)
            self.previous = (now, process, ticks)
            memory = self.fields("/proc/meminfo")
            process_memory = self.fields("/proc/self/status")
            cpu_info = self.fields("/proc/cpuinfo")
            try:
                host_uptime = int(float(Path("/proc/uptime").read_text().split()[0]))
            except (OSError, ValueError, IndexError):
                host_uptime = None
            try:
                disk = shutil.disk_usage(self.data_path)
                disk_info = {"total": disk.total, "used": disk.used, "free": disk.free}
            except OSError:
                disk_info = None
            return {"sampled_at": time.time(), "uptime_seconds": round(now - self.started), "host_uptime_seconds": host_uptime,
                    "cpu": {"logical_cores": os.cpu_count(), "model": cpu_info.get("model name", cpu_info.get("Hardware", "")).strip()[:120],
                            "host_percent": host_percent, "process_percent": process_percent},
                    "memory": {"host_total": self.kib(memory.get("MemTotal")), "host_available": self.kib(memory.get("MemAvailable")),
                               "swap_total": self.kib(memory.get("SwapTotal")), "swap_free": self.kib(memory.get("SwapFree")),
                               "process_rss": self.kib(process_memory.get("VmRSS"))},
                    "data_filesystem": disk_info}

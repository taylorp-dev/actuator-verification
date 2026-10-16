"""Live bench helpers: record channel A, and drive the Raspberry Pi over SSH.

Used by tools/bench_capture.py (manual) and by `pytest --live` (automated).

Control goes over SSH on Wi-Fi (e.g. taylor@dronepi.local). Data goes over the
direct Ethernet cable (Pi 192.168.2.1 -> laptop 192.168.2.2). Keeping them on
different paths is what lets the test take the Ethernet link down without
cutting its own control line.
"""

from __future__ import annotations

import shlex
import socket
import subprocess
import time
from dataclasses import dataclass
from typing import Callable

from .link import DEFAULT_PORT, label_lookup, label_of, unpack_word
from .receiver import Receiver

PI_REPO = "~/actuator-verification"
PI_PYTHON = "~/av-env/bin/python"


def capture_udp(labels, stale_intervals: float, duration_s: float, *,
                port: int = DEFAULT_PORT, first_word_timeout_s: float = 20.0,
                after_bind: Callable[[], None] | None = None,
                status: Callable[[float, int, float, bool, list], None] | None = None,
                status_every_s: float = 0.5):
    """Receive ARINC 429 words over UDP and timestamp them on arrival.

    after_bind runs once the port is open (e.g. start the remote sender), so no
    words are missed. status(t, n_words, pitch, valid, reasons) is called every
    status_every_s with the live receiver state. Returns (rows, sender_ip)."""
    lookup = label_lookup(labels)
    rx = Receiver(labels, stale_intervals=stale_intervals)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", port))
    sock.settimeout(0.05)
    rows: list[tuple[float, int]] = []
    sender = None
    try:
        if after_bind:
            after_bind()
        t_wait = time.perf_counter()
        t0 = None
        next_status = 0.0
        while True:
            try:
                data, addr = sock.recvfrom(64)
                now = time.perf_counter()
                if t0 is None:
                    t0, sender = now, addr[0]
                t = now - t0
                word = unpack_word(data)
                rows.append((t, word))
                name = lookup.get(label_of(word))
                if name:
                    rx.receive(name, word, t)
            except socket.timeout:
                if t0 is None:
                    if time.perf_counter() - t_wait > first_word_timeout_s:
                        raise TimeoutError(
                            f"no words on UDP {port} within {first_word_timeout_s:g} s: "
                            "is the sender running, pointed at this PC, and the firewall open?")
                    continue
                t = time.perf_counter() - t0
            if status and t >= next_status:
                valid, value, reasons = rx.read("pitch", t)
                status(t, len(rows), value, valid, reasons)
                next_status += status_every_s
            if t >= duration_s:
                break
    finally:
        sock.close()
    return rows, sender


@dataclass
class PiRemote:
    """Runs commands on the Pi over SSH (key-based login, no password prompts)."""

    target: str = "taylor@dronepi.local"     # control path: Wi-Fi
    data_host: str = "192.168.2.2"           # where the Pi sends words: laptop on the cable
    iface: str = "eth0"
    timeout_s: float = 20.0

    def run(self, cmd: str, check: bool = True) -> subprocess.CompletedProcess:
        full = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", self.target, cmd]
        p = subprocess.run(full, capture_output=True, text=True, timeout=self.timeout_s)
        if check and p.returncode != 0:
            raise RuntimeError(f"ssh {self.target} {cmd!r} failed ({p.returncode}): "
                               f"{(p.stderr or p.stdout).strip()}")
        return p

    def background(self, cmd: str) -> None:
        """Start cmd on the Pi detached from this SSH session, so it keeps going
        even if the session drops."""
        self.run(f"setsid nohup sh -c {shlex.quote(cmd)} > /dev/null 2>&1 < /dev/null &")

    # --- steps used by the live test -----------------------------------------
    def check_ready(self) -> str:
        p = self.run(f"test -x {PI_PYTHON} && test -f {PI_REPO}/tools/pi_channel_a.py "
                     f"&& sudo -n /usr/sbin/ip link show {self.iface} > /dev/null && echo ok",
                     check=False)
        if p.returncode != 0 or "ok" not in p.stdout:
            raise RuntimeError(
                "Pi not ready for live tests. Check, on the Pi: the repo is at "
                f"{PI_REPO}, the venv at ~/av-env, and the sudo rule for 'ip link' "
                f"(docs/BENCH-GUIDE.md, live setup). ssh said: {(p.stderr or p.stdout).strip()}")
        return "ok"

    def update_code(self) -> str:
        p = self.run(f"git -C {PI_REPO} pull -q && git -C {PI_REPO} rev-parse --short HEAD",
                     check=False)
        if p.returncode == 0:
            return p.stdout.strip()
        return "unknown (git pull failed: " + (p.stderr.strip().splitlines() or ["?"])[0] + ")"

    def stop_sender(self) -> None:
        # "[p]i_..." so the pattern doesn't match the shell running pkill itself
        self.run("pkill -f '[p]i_channel_a.py' || true", check=False)

    def start_sender(self, duration_s: float) -> None:
        self.background(f"cd {PI_REPO} && {PI_PYTHON} tools/pi_channel_a.py "
                        f"--host {self.data_host} --duration {duration_s:g} "
                        f"> /tmp/av_sender.log 2>&1")

    def schedule_link_drop(self, at_s: float, for_s: float) -> None:
        """Automated cable pull: take the Ethernet port down, then back up.
        Runs detached on the Pi so it always brings the link back."""
        ip = f"sudo -n /usr/sbin/ip link set {self.iface}"
        self.background(f"sleep {at_s:g}; {ip} down; sleep {for_s:g}; {ip} up")

    def link_up(self) -> None:
        self.run(f"sudo -n /usr/sbin/ip link set {self.iface} up", check=False)

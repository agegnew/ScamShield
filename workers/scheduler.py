"""Run the radars on a timer and keep the scan workers running. New URLs are de-duplicated by the store.

Usage: python -m workers.scheduler [--workers 3]
"""
import argparse
import logging
import subprocess
import sys
import time

log = logging.getLogger("scheduler")

# Seconds between runs. Daily lists and slow sources run rarely; Search costs SerpApi credits.
RADARS = {
    "workers.radar.certificates": 60 * 60,
    "workers.radar.search": 2 * 60 * 60,
    "workers.radar.new_domains": 6 * 60 * 60,
    "workers.radar.lookalikes": 6 * 60 * 60,
}
TICK_S = 30


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    runner = subprocess.Popen([sys.executable, "-m", "workers.runner", "run", "--workers", str(args.workers)])
    running: dict[str, subprocess.Popen] = {}
    last_start: dict[str, float] = {}
    try:
        while True:
            if runner.poll() is not None:
                log.warning("scan workers exited (%s), restarting", runner.returncode)
                runner = subprocess.Popen([sys.executable, "-m", "workers.runner", "run", "--workers", str(args.workers)])
            for module, interval in RADARS.items():
                proc = running.get(module)
                if proc and proc.poll() is None:
                    continue
                if proc:
                    log.info("%s finished (%s)", module, proc.returncode)
                    running.pop(module)
                if time.time() - last_start.get(module, 0) >= interval:
                    log.info("starting %s", module)
                    running[module] = subprocess.Popen([sys.executable, "-m", module])
                    last_start[module] = time.time()
            time.sleep(TICK_S)
    except KeyboardInterrupt:
        for proc in [runner, *running.values()]:
            proc.terminate()


if __name__ == "__main__":
    main()

import os
import argparse
import logging
import zipfile
import time
import random
from datetime import datetime


def setup_logging(log_dir="logs", level=logging.INFO):
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "alpha_omega.log")
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8"), logging.StreamHandler()],
    )
    return logging.getLogger("alpha_omega")


def initialize_foundation(folders=None):
    folders = folders or ["core", "agents", "memory", "logs"]
    for folder in folders:
        path = os.path.join(os.getcwd(), folder)
        if not os.path.exists(path):
            os.makedirs(path)
            logging.info("Alpha Phase: Created %s substrate.", folder)


def autonomous_objective_loop(goal: str):
    logging.info("Omega Phase: Objective set to - %s", goal)
    manifest_dir = os.path.join(os.getcwd(), "core")
    os.makedirs(manifest_dir, exist_ok=True)
    manifest_path = os.path.join(manifest_dir, "manifest.txt")
    with open(manifest_path, "a", encoding="utf-8") as f:
        f.write(f"\n{datetime.utcnow().isoformat()} Task: Initialize {goal} architecture.")
    logging.info("Heartbeat: System is scanning for next autonomous action...")


def build_package():
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    zip_name = f"alpha_omega_{ts}.zip"
    to_include = ["core", "agents", "memory", "logs", "alpha_omega.py"]
    with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in to_include:
            if os.path.isfile(item):
                zf.write(item, arcname=item)
            elif os.path.isdir(item):
                for root, _, files in os.walk(item):
                    for file in files:
                        full = os.path.join(root, file)
                        rel = os.path.relpath(full, os.getcwd())
                        zf.write(full, arcname=rel)
    print(f"Build complete: {zip_name}")


def simulate_protection(hours=24):
    logging.info("Simulation Started: Monitoring Local Environment for %d hours (accelerated)", hours)
    events = [
        "Scanning local file system integrity...",
        "Verifying backup consistency...",
        "Optimizing local resource allocation...",
        "Detected high CPU usage: Throttling background tasks.",
        "Local firewall check: All ports secure.",
        "System Health: 100% - No anomalies detected.",
        "Encrypted vault check: Access secured.",
        "Routine maintenance: Clearing temporary caches."
    ]
    
    for hour in range(1, hours + 1):
        event = random.choice(events)
        timestamp = datetime.utcnow().strftime("%H:%M:%S")
        logging.info(f"Hour {hour:02d}: {event}")
        time.sleep(0.1)  # Fast-forward simulation
        
    logging.info("Simulation Complete: Environment Secured.")


def main():
    parser = argparse.ArgumentParser(description="Alpha & Omega initialization")
    sub = parser.add_subparsers(dest="cmd", required=True)
    
    init = sub.add_parser("init", help="Initialize foundation and objective")
    init.add_argument("--goal", default="Build Protected Personal Environment", help="Objective string")
    init.add_argument("--folders", nargs="*", help="Override default folders")
    init.add_argument("--verbose", action="store_true", help="Enable debug logging")
    
    bld = sub.add_parser("build", help="Package project into timestamped zip")
    
    sim = sub.add_parser("simulate", help="Run a local protection simulation")
    sim.add_argument("--hours", type=int, default=24, help="Number of hours to simulate")
    
    args = parser.parse_args()

    if args.cmd == "init":
        setup_logging(level=logging.DEBUG if args.verbose else logging.INFO)
        initialize_foundation(folders=args.folders)
        autonomous_objective_loop(args.goal)
    elif args.cmd == "build":
        build_package()
    elif args.cmd == "simulate":
        setup_logging()
        simulate_protection(hours=args.hours)


if __name__ == "__main__":
    main()
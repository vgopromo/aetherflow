#!/usr/bin/env python3
"""
AETHERFLOW — Autonomous Git Intelligence Framework
--------------------------------------------------
A high-efficiency automation layer for synchronizing local data to GitHub,
with intelligent commit generation and telemetry logging.
"""

import os, base64, json, time, hashlib, difflib, requests
from pathlib import Path
from datetime import datetime

# === CONFIGURATION ===
GITHUB_TOKEN = "YOUR_TOKEN_HERE"
REPO_OWNER   = "your-user"
REPO_NAME    = "your-repo"
BRANCH       = "main"
SYNC_FOLDER  = "sync"
LOG_FILE     = "aetherflow.log"
WEBHOOK_URL  = None  # optional: your webhook or Telegram bot URL

# === CORE FUNCTIONS ===
def log(msg: str):
    now = datetime.utcnow().isoformat()
    with open(LOG_FILE, "a") as f:
        f.write(f"[{now}] {msg}\n")
    print(f"[{now}] {msg}")

def get_remote_file_sha(path: str):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    return r.json().get("sha") if r.status_code == 200 else None

def smart_commit_message(local, remote):
    diff = difflib.unified_diff(
        remote.splitlines(), local.splitlines(), lineterm=""
    )
    summary = "\n".join(list(diff)[:5])
    return f"🤖 AutoSync: {len(local)} bytes updated\n\n{summary}"

def sha256sum(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def sync_file(local_path: Path):
    rel_path = local_path.relative_to(SYNC_FOLDER)
    content = local_path.read_text(encoding="utf-8")
    encoded = base64.b64encode(content.encode()).decode()

    sha = get_remote_file_sha(str(rel_path))
    commit_msg = smart_commit_message(content, "")

    payload = {
        "message": commit_msg,
        "content": encoded,
        "branch": BRANCH
    }
    if sha: payload["sha"] = sha

    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{rel_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.put(url, headers=headers, data=json.dumps(payload))

    if r.status_code in (200, 201):
        log(f"✅ Synced {rel_path} ({sha256sum(local_path)[:8]})")
        return True
    else:
        log(f"❌ Failed {rel_path}: {r.status_code} {r.text}")
        return False

def notify(msg):
    if WEBHOOK_URL:
        try:
            requests.post(WEBHOOK_URL, json={"text": msg})
        except Exception as e:
            log(f"Webhook failed: {e}")

# === MAIN LOOP ===
def main():
    folder = Path(SYNC_FOLDER)
    if not folder.exists():
        log("Creating sync folder.")
        folder.mkdir()
    for file in folder.glob("**/*"):
        if file.is_file():
            sync_file(file)
            time.sleep(1)
    notify("AetherFlow synchronization complete.")

if __name__ == "__main__":
    log("=== AETHERFLOW STARTED ===")
    main()
    log("=== COMPLETE ===")

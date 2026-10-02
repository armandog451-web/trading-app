import subprocess, time, sys
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Root of the project (where the .git folder lives)
PROJECT_ROOT = Path(__file__).resolve().parents[1]  # assumes this script is in <project>/backend/

class GitSyncHandler(FileSystemEventHandler):
    """Debounced handler that stages, commits and pushes any change."""
    def __init__(self, debounce_seconds: float = 5.0):
        self.debounce = debounce_seconds
        self.last_event = 0.0

    def on_any_event(self, event):
        # Ignore directory events that fire excessively
        if event.is_directory:
            return
        now = time.time()
        if now - self.last_event < self.debounce:
            return  # skip rapid successive events
        self.last_event = now
        self._run_git_sync()

    def _run_git_sync(self):
        try:
            # Stage all changes
            subprocess.run(["git", "add", "-A"], cwd=PROJECT_ROOT, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # Determine if there is anything to commit
            diff_result = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=PROJECT_ROOT)
            if diff_result.returncode == 0:
                # No changes staged
                return
            # Commit with a generic message (include timestamp for uniqueness)
            commit_msg = f"Auto‑sync {time.strftime('%Y-%m-%d %H:%M:%S')}"
            subprocess.run(["git", "commit", "-m", commit_msg], cwd=PROJECT_ROOT, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # Push to the remote (origin)
            subprocess.run(["git", "push"], cwd=PROJECT_ROOT, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            print(f"[GitSync] Git command failed: {e}", file=sys.stderr)

if __name__ == "__main__":
    observer = Observer()
    handler = GitSyncHandler()
    observer.schedule(handler, str(PROJECT_ROOT), recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

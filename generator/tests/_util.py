"""Test helpers: put generator/scripts on sys.path and build throwaway roots/repos."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import awarelib  # noqa: E402

CONFIG = awarelib.load_config()
CAPS = CONFIG["limits"]["caps"]


def run_script(name, *args, cwd=None):
    """Run a harness script as a subprocess; returns CompletedProcess."""
    return subprocess.run([sys.executable, str(SCRIPTS / name), *map(str, args)],
                          capture_output=True, text=True, cwd=cwd)


GIT_ENV = {
    "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "t@example.invalid",
    "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "t@example.invalid",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
}


def git(repo, *args, env=None):
    full_env = {**os.environ, **GIT_ENV, **(env or {})}
    res = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, env=full_env)
    if res.returncode != 0:
        raise RuntimeError(f"git {args}: {res.stderr}")
    return res.stdout


def make_repo():
    """Temp git repo on branch main with one initial commit. Caller cleans up the TemporaryDirectory."""
    tmp = tempfile.TemporaryDirectory()
    repo = Path(tmp.name)
    git(repo, "init", "-q", "-b", "main")
    (repo / "README.md").write_text("root\n")
    (repo / ".gitignore").write_text(".work/\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "init")
    return tmp, repo


def commit_file(repo, rel, content, msg="change", env=None):
    p = Path(repo) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", msg, env=env)
    return git(repo, "rev-parse", "HEAD").strip()

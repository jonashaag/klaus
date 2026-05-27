"""On-demand SCIP index generation.

When ``scip_policy`` allows it (see :func:`klaus.Klaus.should_generate_scip`),
:func:`request_index` schedules a background job that:

1. Adds a ``git worktree`` at a tempdir checked out to the requested commit.
2. Runs the first matching indexer (see :data:`INDEXERS`) inside the
   worktree.
3. Moves the resulting ``index.scip`` to ``<repo>/.scip/<sha>.scip``.
4. Tears the worktree down.

Subsequent requests for the same revision pick up the dump via
:mod:`klaus.scip_index`.  Concurrent requests for the same ``(repo, sha)``
share a single background job via an in-process lock.
"""

import logging
import os
import shutil
import subprocess
import tempfile
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from klaus import scip_index

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Indexer:
    """A SCIP indexer for some language family.

    :param name: human-readable name shown in logs.
    :param applies: predicate run against a checked-out worktree path; returns
        ``True`` if this indexer should handle the project.
    :param command: argv to invoke inside the worktree.  Must write
        ``index.scip`` to the current working directory.
    """

    name: str
    applies: Callable[[str], bool]
    command: list[str]


def _looks_like_python(worktree: str) -> bool:
    for marker in ("pyproject.toml", "setup.py", "setup.cfg"):
        if os.path.isfile(os.path.join(worktree, marker)):
            return True
    for root, _, files in os.walk(worktree):
        # Skip hidden dirs (notably .git, .scip)
        if os.path.basename(root).startswith("."):
            continue
        if any(f.endswith(".py") for f in files):
            return True
    return False


#: Built-in indexers, tried in order.  External integrators can append to this
#: list before constructing the app.
INDEXERS: list[Indexer] = [
    Indexer(
        name="scip-python",
        applies=_looks_like_python,
        command=["scip-python", "index", "."],
    ),
]


_LOCK = threading.Lock()
_INFLIGHT: dict[tuple[str, str], threading.Thread] = {}


def request_index(repo_path: str, sha: str) -> None:
    """Schedule background generation of ``<repo_path>/.scip/<sha>.scip``.

    Returns immediately.  Idempotent: if a generation job is already running
    for ``(repo_path, sha)``, or if the dump already exists, this is a no-op.
    """
    sha = sha.lower()
    if os.path.isfile(_dump_path(repo_path, sha)):
        return
    key = (repo_path, sha)
    with _LOCK:
        if key in _INFLIGHT and _INFLIGHT[key].is_alive():
            logger.debug(
                "scip: %s@%s already being indexed; skipping",
                repo_path,
                sha[:7],
            )
            return
        thread = threading.Thread(
            target=_run,
            args=(repo_path, sha),
            name=f"scip-index {os.path.basename(repo_path)}@{sha[:7]}",
            daemon=True,
        )
        _INFLIGHT[key] = thread
    logger.info("scip: scheduled index for %s@%s", repo_path, sha[:7])
    thread.start()


def _dump_path(repo_path: str, sha: str) -> str:
    return os.path.join(repo_path, ".scip", f"{sha}.scip")


def _run(repo_path: str, sha: str) -> None:
    started = time.monotonic()
    logger.info("scip: starting index for %s@%s", repo_path, sha[:7])
    try:
        _generate(repo_path, sha)
    except Exception:
        elapsed = time.monotonic() - started
        logger.exception(
            "scip: index for %s@%s failed after %.1fs", repo_path, sha[:7], elapsed
        )
    else:
        elapsed = time.monotonic() - started
        logger.info(
            "scip: finished index for %s@%s in %.1fs", repo_path, sha[:7], elapsed
        )
    finally:
        with _LOCK:
            _INFLIGHT.pop((repo_path, sha), None)
        scip_index.clear_cache()


def _generate(repo_path: str, sha: str) -> None:
    dump_path = _dump_path(repo_path, sha)
    if os.path.isfile(dump_path):
        return

    worktree = tempfile.mkdtemp(prefix="klaus-scip-")
    # `git worktree add` will fail if the destination directory already
    # exists; mkdtemp created it, so remove it first.
    os.rmdir(worktree)
    try:
        subprocess.check_call(
            ["git", "worktree", "add", "--detach", worktree, sha],
            cwd=repo_path,
        )
        try:
            indexer = _pick_indexer(worktree)
            if indexer is None:
                logger.info(
                    "scip: no matching indexer for %s@%s; skipping",
                    repo_path,
                    sha[:7],
                )
                return
            logger.info("scip: running %s for %s@%s", indexer.name, repo_path, sha[:7])
            subprocess.check_call(indexer.command, cwd=worktree)
            produced = os.path.join(worktree, "index.scip")
            if not os.path.isfile(produced):
                raise RuntimeError(
                    f"{indexer.name} did not produce index.scip in {worktree}"
                )
            os.makedirs(os.path.dirname(dump_path), exist_ok=True)
            shutil.move(produced, dump_path)
            logger.debug("scip: wrote %s", dump_path)
        finally:
            subprocess.call(
                ["git", "worktree", "remove", "--force", worktree],
                cwd=repo_path,
            )
    finally:
        # `git worktree remove` should have cleaned up, but if it didn't
        # (e.g. it was never created), drop the directory ourselves.
        if os.path.isdir(worktree):
            shutil.rmtree(worktree, ignore_errors=True)


def _pick_indexer(worktree: str) -> Indexer | None:
    for indexer in INDEXERS:
        try:
            applies = indexer.applies(worktree)
        except Exception:
            applies = False
        if applies:
            return indexer
    return None

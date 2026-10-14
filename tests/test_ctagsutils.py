import os
import subprocess

import pytest

from klaus import ctagsutils


def _git(cwd, *args):
    subprocess.check_call(["git", *args], cwd=cwd)


def _make_hostile_repo(path, outside):
    """A repo that ships a ctags options file and a symlink out of the tree."""
    os.makedirs(path)
    os.makedirs(outside)
    with open(os.path.join(outside, "secret.py"), "w") as f:
        f.write("def secret_fn():\n    pass\n")
    with open(os.path.join(path, "ok.c"), "w") as f:
        f.write("int ok(void) { return 0; }\n")
    os.symlink(outside, os.path.join(path, "linked"))
    os.makedirs(os.path.join(path, ".ctags.d"))
    with open(os.path.join(path, ".ctags.d", "x.ctags"), "w") as f:
        # If honoured, this turns the C parser off and ok.c gets no tag.
        f.write("--languages=-C\n")
    _git(path, "init", "-q")
    _git(path, "add", "-A")
    env = dict(
        os.environ,
        GIT_AUTHOR_NAME="t",
        GIT_AUTHOR_EMAIL="t@t",
        GIT_COMMITTER_NAME="t",
        GIT_COMMITTER_EMAIL="t@t",
    )
    subprocess.check_call(["git", "commit", "-q", "-m", "x"], cwd=path, env=env)
    return (
        subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path).decode().strip()
    )


def test_create_tagsfile_ignores_repo_options_and_symlinks(tmp_path):
    if not ctagsutils.check_have_compatible_ctags():
        pytest.skip("no compatible ctags binary")
    repo = str(tmp_path / "repo")
    outside = str(tmp_path / "outside")
    rev = _make_hostile_repo(repo, outside)
    tagsfile = ctagsutils.create_tagsfile(repo, rev)
    try:
        with open(tagsfile) as f:
            tags = f.read()
    finally:
        ctagsutils.delete_tagsfile(tagsfile)
    # --options=NONE: the repo's .ctags.d file is ignored, so ok.c is tagged.
    assert "ok\tok.c\t" in tags
    # --links=no: the out-of-tree symlink is not followed.
    assert "secret_fn" not in tags

import os
import shutil
import subprocess
import tempfile


def check_have_compatible_ctags():
    """Check that the 'ctags' binary is a compatible ctags (Universal or Exuberant, not etags etc)"""
    try:
        out = subprocess.check_output(["ctags", "--version"], stderr=subprocess.PIPE)
        return b"Universal" in out or b"Exuberant" in out
    except subprocess.CalledProcessError:
        return False


def create_tagsfile(git_repo_path, git_rev):
    """Create a ctags tagsfile for the given Git repository and revision.

    This creates a temporary clone of the repository, checks out the revision,
    runs 'ctags -R' and deletes the temporary clone.

    :return: path to the generated tagsfile
    """
    assert (
        check_have_compatible_ctags()
    ), "'ctags' binary is missing or not *Universal* (or *Exuberant*) ctags"

    _, target_tagsfile = tempfile.mkstemp()
    checkout_tmpdir = tempfile.mkdtemp()
    try:
        subprocess.check_call(
            ["git", "clone", "-q", "--shared", git_repo_path, checkout_tmpdir]
        )
        subprocess.check_call(["git", "checkout", "-q", git_rev], cwd=checkout_tmpdir)
        subprocess.check_call(
            ["ctags", "--fields=+l", "-Rno", target_tagsfile], cwd=checkout_tmpdir
        )
    finally:
        shutil.rmtree(checkout_tmpdir)
    return target_tagsfile


def delete_tagsfile(tagsfile_path):
    """Delete a tagsfile."""
    os.remove(tagsfile_path)

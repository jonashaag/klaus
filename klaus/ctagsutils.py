import os
import subprocess
import shutil
import tempfile
from klaus.utils import check_output


def check_have_exuberant_ctags():
    """Check that the 'ctags' binary is *Exuberant* ctags (not etags etc)"""
    try:
        return b"Exuberant" in check_output(["ctags", "--version"], stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        return False


def create_tagsfile(git_repo_path, git_rev):
    """Create a ctags tagsfile for the given Git repository and revision.

    This creates a temporary clone of the repository, checks out the revision,
    runs 'ctags -R' and deletes the temporary clone.

    :return: path to the generated tagsfile
    """
    assert check_have_exuberant_ctags(), "'ctags' binary is missing or not *Exuberant* ctags"

    _, target_tagsfile = tempfile.mkstemp()
    checkout_tmpdir = tempfile.mkdtemp()
    try:
        subprocess.check_call(["git", "clone", "-q", "--shared", git_repo_path, checkout_tmpdir])
        subprocess.check_call(["git", "checkout", "-q", git_rev], cwd=checkout_tmpdir)
        subprocess.check_call(["ctags", "--fields=+l", "-Rno", target_tagsfile], cwd=checkout_tmpdir)
    finally:
        shutil.rmtree(checkout_tmpdir)
    return target_tagsfile


def delete_tagsfile(tagsfile_path):
    """Delete a tagsfile."""
    os.remove(tagsfile_path)

import os


def get_args_from_env():
    repos = os.environ.get('KLAUS_REPOS', [])
    if repos:
        repos = repos.split()
    args = (
        repos,
        os.environ['KLAUS_SITE_NAME']
    )
    kwargs = dict(
        htdigest_file=os.environ.get('KLAUS_HTDIGEST_FILE'),
        use_smarthttp=bool(os.environ.get('KLAUS_USE_SMARTHTTP')),
        require_browser_auth=bool(os.environ.get('KLAUS_REQUIRE_BROWSER_AUTH')),
        disable_push=bool(os.environ.get('KLAUS_DISABLE_PUSH')),
        unauthenticated_push=bool(os.environ.get('KLAUS_UNAUTHENTICATED_PUSH')),
        ctags_policy=os.environ.get('KLAUS_CTAGS_POLICY', 'none')
    )
    return args, kwargs

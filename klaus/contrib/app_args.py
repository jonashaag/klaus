import os


def strtobool(val):
    """Convert a string representation of truth to 0 or 1.
    
    Args:
        val (str): String value to convert to boolean integer.
        
    Returns:
        int: 1 for truthy values, 0 for falsy values.
        
    Raises:
        ValueError: If the input string is not a recognized truth value.
        
    Note:
        Truthy values: 'y', 'yes', 't', 'true', 'on', '1' (case insensitive)
        Falsy values: 'n', 'no', 'f', 'false', 'off', '0' (case insensitive)
    """
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return 1
    elif val in ("n", "no", "f", "false", "off", "0"):
        return 0
    else:
        raise ValueError(f"invalid truth value {val!r}")


def get_args_from_env():
    """Extract Klaus application arguments and configuration from environment variables.
    
    Returns:
        tuple: A tuple containing (args, kwargs) where:
            - args (tuple): Positional arguments (repos list, site name)
            - kwargs (dict): Keyword arguments with configuration options
            
    Environment Variables:
        KLAUS_REPOS: Space-separated list of repository paths
        KLAUS_SITE_NAME: Name of the site (default: "unnamed site")
        KLAUS_HTDIGEST_FILE: Path to htdigest authentication file
        KLAUS_USE_SMARTHTTP: Enable smart HTTP protocol (default: "0")
        KLAUS_REQUIRE_BROWSER_AUTH: Require browser authentication (default: "0")
        KLAUS_DISABLE_PUSH: Disable push operations (default: "0")
        KLAUS_UNAUTHENTICATED_PUSH: Allow unauthenticated push (default: "0")
        KLAUS_CTAGS_POLICY: Policy for ctags usage (default: "none")
    """
    repos = os.environ.get("KLAUS_REPOS", [])
    if repos:
        repos = repos.split()
    args = (repos, os.environ.get("KLAUS_SITE_NAME", "unnamed site"))
    kwargs = dict(
        htdigest_file=os.environ.get("KLAUS_HTDIGEST_FILE"),
        use_smarthttp=strtobool(os.environ.get("KLAUS_USE_SMARTHTTP", "0")),
        require_browser_auth=strtobool(
            os.environ.get("KLAUS_REQUIRE_BROWSER_AUTH", "0")
        ),
        disable_push=strtobool(os.environ.get("KLAUS_DISABLE_PUSH", "0")),
        unauthenticated_push=strtobool(
            os.environ.get("KLAUS_UNAUTHENTICATED_PUSH", "0")
        ),
        ctags_policy=os.environ.get("KLAUS_CTAGS_POLICY", "none"),
    )
    return args, kwargs
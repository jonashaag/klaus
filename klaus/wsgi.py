import os
from klaus import make_app

application = make_app(
    os.environ['KLAUS_REPOS'].split(),
    os.environ['KLAUS_SITE_NAME'],
    os.environ.get('KLAUS_USE_SMARTHTTP'),
    os.environ.get('KLAUS_HTDIGEST_FILE'),
)

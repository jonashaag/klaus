import os
from klaus import make_app

if 'KLAUS_HTDIGEST_FILE' in os.environ:
    with open(os.environ['KLAUS_HTDIGEST_FILE']) as file:
        application = make_app(
            os.environ['KLAUS_REPOS'].split(),
            os.environ['KLAUS_SITE_NAME'],
            os.environ.get('KLAUS_USE_SMARTHTTP'),
            file,
        )
else:
    application = make_app(
        os.environ['KLAUS_REPOS'].split(),
        os.environ['KLAUS_SITE_NAME'],
        os.environ.get('KLAUS_USE_SMARTHTTP'),
        None,
    )

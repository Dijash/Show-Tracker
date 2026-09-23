import os
import sys
from pathlib import Path

# Ensure project root is in sys.path for Vercel Serverless Function runtime
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from django.core.wsgi import get_wsgi_application

_django_app = get_wsgi_application()


def app(environ, start_response):
    """
    WSGI wrapper ensuring proper PATH_INFO routing on Vercel Serverless Functions.
    """
    path_info = environ.get('PATH_INFO', '')
    if path_info.startswith('/api/index.py') or path_info.startswith('/api/index'):
        matched_path = environ.get('HTTP_X_MATCHED_PATH') or environ.get('HTTP_X_FORWARDED_PATH')
        if matched_path:
            environ['PATH_INFO'] = matched_path
        elif path_info in ('/api/index.py', '/api/index'):
            environ['PATH_INFO'] = '/'
        elif path_info.startswith('/api/index.py/'):
            environ['PATH_INFO'] = path_info[len('/api/index.py'):]
        elif path_info.startswith('/api/index/'):
            environ['PATH_INFO'] = path_info[len('/api/index'):]

    return _django_app(environ, start_response)

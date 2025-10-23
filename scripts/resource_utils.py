import os
import sys

def resource_path(rel_path: str) -> str:
    """Return absolute path to resource, works for dev and PyInstaller bundling.

    Usage:
        from scripts.resource_utils import resource_path
        img = Image.open(resource_path('images/mode1.png'))
    """
    try:
        base = sys._MEIPASS
    except AttributeError:
        base = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base, rel_path)

# Smoke tests basiques pour vérifier l'import et les fonctions principales
import sys
import os
import pytest

# S'assurer que le répertoire racine du repo est dans sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from main_tkinter import load_config, surfacing, contour_drilling, matrix_drilling


def test_import_and_load_config():
    cfg = load_config()
    assert isinstance(cfg, dict)


@pytest.mark.parametrize("fn", [surfacing, contour_drilling, matrix_drilling])
def test_generation_returns_tuple(fn):
    cfg = load_config()
    res = fn(cfg)
    assert isinstance(res, tuple), f"{fn.__name__} should return a tuple"
    assert len(res) == 8, f"{fn.__name__} should return 8 elements (gcode,start_x,start_y,start_z,current_z,end_x,end_y,clearance)"
    gcode = res[0]
    assert isinstance(gcode, str) and gcode.strip() != "", "gcode should be a non-empty string"

import sys
import os

# Ensure repository root is on sys.path when running from tests/
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from main_tkinter import (
    load_config,
    surfacing,
    contour_drilling,
    matrix_drilling,
    corner_radius,
    threading,
)


def run_and_check(fn, name):
    cfg = load_config()
    try:
        res = fn(cfg)
    except Exception as e:
        print(f"ERROR: {name} raised an exception: {e}")
        raise

    if not isinstance(res, tuple):
        raise AssertionError(f"{name} should return a tuple, got {type(res)}")
    if len(res) < 1:
        raise AssertionError(f"{name} returned an empty tuple")

    gcode = res[0]
    if not isinstance(gcode, str) or len(gcode) == 0:
        raise AssertionError(f"{name}: gcode must be a non-empty string")

    print(f"{name}: OK (gcode length={len(gcode)})")


def main():
    tests = [
        (surfacing, "surfacing"),
        (contour_drilling, "contour_drilling"),
        (matrix_drilling, "matrix_drilling"),
        (corner_radius, "corner_radius"),
        (threading, "threading"),
    ]

    for fn, name in tests:
        run_and_check(fn, name)

    print("All smoke tests passed.")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('Smoke tests failed:', e)
        sys.exit(1)

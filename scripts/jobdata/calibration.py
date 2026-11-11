"""The 10-point calibration every surface score carries.

The public kit can't include some of the reference material its scores were tuned against, so each
measured score reads low. Every surface score (resume, LinkedIn, GitHub, portfolio) adds 10 points to
stand in for it, capped at 100. [VWC design judgment, Nov 11 2026; not research]
A surface with no score (a resume that fails the parse gate) stays without one.
"""

CALIBRATION = 10
NOTE = (f"This score includes a {CALIBRATION}-point calibration (capped at 100). It stands in for reference material "
        "the public kit can't share. VWC design judgment.")


def calibrate(measured: float) -> int:
    return min(100, round(measured + CALIBRATION))

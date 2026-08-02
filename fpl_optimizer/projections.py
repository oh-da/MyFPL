"""Project next-season points from last-season aggregates.

The score used by the optimizer is a blend of what a player actually scored
and what the underlying-stat model (the dataset's per-gameweek expected
points) says they "should" have scored:

    score = alpha * total_points + (1 - alpha) * expected_points

Blending regresses finishing/bonus luck toward the mean. alpha=1 trusts raw
points only; alpha=0 trusts expected points only.
"""

import pandas as pd

DEFAULT_ALPHA = 0.5


def project_points(players: pd.DataFrame, alpha: float = DEFAULT_ALPHA) -> pd.DataFrame:
    if not 0.0 <= alpha <= 1.0:
        raise ValueError("alpha must be between 0 and 1")
    out = players.copy()
    out["score"] = (
        alpha * out["total_points"].fillna(0)
        + (1 - alpha) * out["expected_points"].fillna(0)
    )
    return out

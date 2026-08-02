"""Official FPL squad rules (fantasy.premierleague.com/en/help/rules).

Only the rules the optimizer enforces live here; the scoring system is
documented in the README (player points are taken from historical data,
not recomputed).
"""

BUDGET = 100.0  # million

# Position ids as used by the FPL API ("element_type").
GKP, DEF, MID, FWD = 1, 2, 3, 4
POSITION_NAMES = {GKP: "GKP", DEF: "DEF", MID: "MID", FWD: "FWD"}

# 15-man squad composition.
SQUAD_SIZE = 15
SQUAD_COMPOSITION = {GKP: 2, DEF: 5, MID: 5, FWD: 3}

MAX_PER_CLUB = 3

# Starting XI: 11 players, exactly 1 GK, and formation limits that
# cover all legal formations (3-4-3 ... 5-4-1).
XI_SIZE = 11
XI_MIN = {GKP: 1, DEF: 3, MID: 2, FWD: 1}
XI_MAX = {GKP: 1, DEF: 5, MID: 5, FWD: 3}

"""Select the optimal 15-man FPL squad as an integer linear program.

Maximizes projected points of the best legal starting XI, with the captain
counted double and a small weight on bench players' points, subject to the
official squad rules (budget, 2-5-5-3 composition, max 3 per club, legal
formations).
"""

from dataclasses import dataclass

import pandas as pd
import pulp

from . import rules

BENCH_WEIGHT = 0.1


def resolve_player(players: pd.DataFrame, name: str):
    """Find the index of a player by (case-insensitive) name.

    Tries an exact web_name match first, then substring. Raises ValueError
    if the name is unknown or matches more than one player.
    """
    lowered = players["web_name"].str.lower()
    matches = players[lowered == name.lower()]
    if matches.empty:
        matches = players[lowered.str.contains(name.lower(), regex=False)]
    if matches.empty:
        raise ValueError(f"no player matching {name!r}")
    if len(matches) > 1:
        options = ", ".join(
            f"{r.web_name} ({r.team_name})" for r in matches.itertuples()
        )
        raise ValueError(f"{name!r} is ambiguous: {options}")
    return matches.index[0]


@dataclass
class Squad:
    players: pd.DataFrame  # squad of 15, with 'starting' and 'captain' columns
    total_cost: float
    projected_xi_points: float

    @property
    def starting_xi(self) -> pd.DataFrame:
        return self.players[self.players["starting"]]

    @property
    def bench(self) -> pd.DataFrame:
        return self.players[~self.players["starting"]]

    @property
    def formation(self) -> str:
        counts = self.starting_xi["element_type"].value_counts()
        return "-".join(
            str(counts.get(p, 0)) for p in (rules.DEF, rules.MID, rules.FWD)
        )


def optimize_squad(
    players: pd.DataFrame,
    budget: float = rules.BUDGET,
    locked: list | None = None,
) -> Squad:
    """players needs columns: web_name, team_name, element_type, price, score.

    locked: player indices (rows of `players`) that must be in the squad;
    the rest of the team is optimized around them.
    """
    idx = list(players.index)
    pos = players["element_type"]
    price = players["price"]
    score = players["score"]

    in_squad = pulp.LpVariable.dicts("squad", idx, cat="Binary")
    in_xi = pulp.LpVariable.dicts("xi", idx, cat="Binary")
    captain = pulp.LpVariable.dicts("cap", idx, cat="Binary")

    prob = pulp.LpProblem("fpl_squad", pulp.LpMaximize)
    prob += (
        pulp.lpSum(score[i] * in_xi[i] for i in idx)
        + pulp.lpSum(score[i] * captain[i] for i in idx)
        + BENCH_WEIGHT * pulp.lpSum(score[i] * (in_squad[i] - in_xi[i]) for i in idx)
    )

    prob += pulp.lpSum(in_squad[i] for i in idx) == rules.SQUAD_SIZE
    prob += pulp.lpSum(price[i] * in_squad[i] for i in idx) <= budget
    for p, n in rules.SQUAD_COMPOSITION.items():
        prob += pulp.lpSum(in_squad[i] for i in idx if pos[i] == p) == n
    for club in players["team_name"].unique():
        prob += (
            pulp.lpSum(in_squad[i] for i in idx if players["team_name"][i] == club)
            <= rules.MAX_PER_CLUB
        )

    prob += pulp.lpSum(in_xi[i] for i in idx) == rules.XI_SIZE
    for i in idx:
        prob += in_xi[i] <= in_squad[i]
        prob += captain[i] <= in_xi[i]
    for p in rules.SQUAD_COMPOSITION:
        n_pos = pulp.lpSum(in_xi[i] for i in idx if pos[i] == p)
        prob += n_pos >= rules.XI_MIN[p]
        prob += n_pos <= rules.XI_MAX[p]

    prob += pulp.lpSum(captain[i] for i in idx) == 1

    for i in locked or []:
        prob += in_squad[i] == 1

    status = prob.solve(pulp.PULP_CBC_CMD(msg=False))
    if pulp.LpStatus[status] != "Optimal":
        raise RuntimeError(f"solver failed: {pulp.LpStatus[status]}")

    chosen = [i for i in idx if in_squad[i].value() == 1]
    squad = players.loc[chosen].copy()
    squad["starting"] = [in_xi[i].value() == 1 for i in chosen]
    squad["captain"] = [captain[i].value() == 1 for i in chosen]
    squad = squad.sort_values(
        ["starting", "element_type", "score"], ascending=[False, True, False]
    )

    xi_points = squad.loc[squad["starting"], "score"].sum()
    return Squad(
        players=squad,
        total_cost=squad["price"].sum(),
        projected_xi_points=xi_points,
    )

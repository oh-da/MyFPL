import pandas as pd
import pytest

from fpl_optimizer import rules
from fpl_optimizer.optimizer import optimize_squad, resolve_player
from fpl_optimizer.projections import project_points


def make_pool():
    """Synthetic pool: 4 GK, 8 DEF, 8 MID, 6 FWD across many clubs."""
    rows = []
    counts = {rules.GKP: 4, rules.DEF: 8, rules.MID: 8, rules.FWD: 6}
    n = 0
    for pos, count in counts.items():
        for k in range(count):
            rows.append(
                {
                    "web_name": f"p{pos}_{k}",
                    "team_name": f"club{n % 10}",
                    "element_type": pos,
                    "price": 4.0 + k * 0.5,
                    "score": 50.0 + k * 10,  # pricier players score more
                }
            )
            n += 1
    return pd.DataFrame(rows)


def test_squad_respects_all_rules():
    squad = optimize_squad(make_pool(), budget=80.0)

    assert len(squad.players) == rules.SQUAD_SIZE
    assert squad.total_cost <= 80.0 + 1e-6

    by_pos = squad.players["element_type"].value_counts()
    for pos, n in rules.SQUAD_COMPOSITION.items():
        assert by_pos[pos] == n

    assert squad.players["team_name"].value_counts().max() <= rules.MAX_PER_CLUB

    xi = squad.starting_xi
    assert len(xi) == rules.XI_SIZE
    xi_pos = xi["element_type"].value_counts()
    for pos in rules.SQUAD_COMPOSITION:
        assert rules.XI_MIN[pos] <= xi_pos.get(pos, 0) <= rules.XI_MAX[pos]

    assert squad.players["captain"].sum() == 1
    assert squad.players.loc[squad.players["captain"], "starting"].all()


def test_locked_players_forced_into_squad():
    # An expensive zero-scoring forward is never picked on merit.
    dud = pd.DataFrame(
        [
            {
                "web_name": "dud",
                "team_name": "club_dud",
                "element_type": rules.FWD,
                "price": 6.0,
                "score": 0.0,
            }
        ]
    )
    pool = pd.concat([make_pool(), dud], ignore_index=True)
    dud_idx = pool.index[-1]

    free = optimize_squad(pool, budget=80.0)
    assert dud_idx not in free.players.index

    locked = optimize_squad(pool, budget=80.0, locked=[dud_idx])
    assert dud_idx in locked.players.index
    assert len(locked.players) == rules.SQUAD_SIZE
    assert locked.total_cost <= 80.0 + 1e-6


def test_resolve_player():
    pool = make_pool()
    assert resolve_player(pool, "P4_2") == pool[pool["web_name"] == "p4_2"].index[0]
    with pytest.raises(ValueError, match="no player"):
        resolve_player(pool, "Zidane")
    with pytest.raises(ValueError, match="ambiguous"):
        resolve_player(pool, "p4")  # matches every forward


def test_infeasible_budget_raises():
    with pytest.raises(RuntimeError):
        optimize_squad(make_pool(), budget=10.0)


def test_projection_blend():
    df = pd.DataFrame({"total_points": [100.0], "expected_points": [60.0]})
    assert project_points(df, alpha=1.0)["score"].iloc[0] == 100.0
    assert project_points(df, alpha=0.0)["score"].iloc[0] == 60.0
    assert project_points(df, alpha=0.5)["score"].iloc[0] == 80.0
    with pytest.raises(ValueError):
        project_points(df, alpha=1.5)

"""Command-line interface: build the optimal FPL squad."""

import argparse
import sys

from . import data, projections, rules
from .optimizer import optimize_squad

DEFAULT_CSV = "data/fpl_2025-26_stats.csv"


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="fpl-optimizer",
        description="Pick the optimal FPL 15-man squad from last-season stats.",
    )
    parser.add_argument(
        "--data", default=DEFAULT_CSV, help="per-gameweek stats CSV (last season)"
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="fetch current player list and prices from the FPL API "
        "(requires internet access to fantasy.premierleague.com)",
    )
    parser.add_argument(
        "--budget", type=float, default=rules.BUDGET, help="budget in millions"
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=projections.DEFAULT_ALPHA,
        help="blend between actual points (1.0) and expected points (0.0)",
    )
    args = parser.parse_args(argv)

    history = data.load_history(args.data)
    if args.live:
        live = data.fetch_live_players()
        players = data.merge_live_with_history(live, history)
        players = players[players["status"] == "a"]  # exclude injured/unavailable
        source = "live FPL API prices + last-season stats"
    else:
        players = history
        source = f"last-season data only ({args.data})"

    players = projections.project_points(players, alpha=args.alpha)
    squad = optimize_squad(players, budget=args.budget)

    print(f"Source: {source}")
    print(f"Budget: {args.budget:.1f}m | Spent: {squad.total_cost:.1f}m "
          f"| In the bank: {args.budget - squad.total_cost:.1f}m")
    print(f"Formation: {squad.formation} | "
          f"Projected XI points (captain doubled not included): "
          f"{squad.projected_xi_points:.0f}")
    print()

    def show(df, title):
        print(title)
        for _, r in df.iterrows():
            tag = " (C)" if r["captain"] else ""
            print(
                f"  {rules.POSITION_NAMES[r['element_type']]}  "
                f"{r['web_name']:<18} {r['team_name']:<15} "
                f"{r['price']:>5.1f}m  score {r['score']:6.1f}{tag}"
            )
        print()

    show(squad.starting_xi, "Starting XI:")
    show(squad.bench, "Bench:")

    return 0


if __name__ == "__main__":
    sys.exit(main())

# MyFPL — Fantasy Premier League Squad Optimizer

Picks the mathematically optimal 15-man FPL squad under the official game
rules, using last season's per-gameweek statistics (and, when available,
live prices from the FPL API).

## How it works

1. **Data** (`fpl_optimizer/data.py`) — aggregates the per-gameweek stats in
   `data/fpl_2025-26_stats.csv` (points, expected points, minutes, price)
   into one row per player. With `--live`, the current season's player list
   and prices are fetched from
   `https://fantasy.premierleague.com/api/bootstrap-static/` and matched to
   last season's stats by name/team.
2. **Projection** (`fpl_optimizer/projections.py`) — each player's score is
   a blend of actual and expected season points,
   `alpha * total_points + (1 - alpha) * expected_points` (default
   `alpha = 0.5`), which regresses finishing/bonus luck toward the mean.
3. **Optimization** (`fpl_optimizer/optimizer.py`) — an integer linear
   program (PuLP/CBC) maximizes the projected points of the best legal
   starting XI, with the captain counted double and a 10% weight on bench
   points, subject to the squad rules below.

## Rules enforced (fantasy.premierleague.com/en/help/rules)

- £100.0m budget
- 15 players: 2 GKP, 5 DEF, 5 MID, 3 FWD
- Max 3 players from any one club
- Starting XI of 11 with a legal formation: exactly 1 GKP, 3–5 DEF,
  2–5 MID, 1–3 FWD
- One captain (scores double), chosen from the XI

Player scoring itself (goals, assists, clean sheets, defensive
contribution, bonus, …) is not recomputed — the dataset's actual
`total_points` and model-based `expected_points` already encode it.

## Usage

```bash
pip install -r requirements.txt

# Optimize from last season's data (offline)
python -m fpl_optimizer.cli

# Use current-season players and prices from the live FPL API
python -m fpl_optimizer.cli --live

# Lock players into the squad and build the best team around them
python -m fpl_optimizer.cli --lock Haaland --lock Saka

# Options
python -m fpl_optimizer.cli --budget 100.0 --alpha 0.5 --data data/fpl_2025-26_stats.csv
```

`--lock` guarantees a place in the 15 (not necessarily the starting XI);
names are case-insensitive and may be partial, as long as they match a
single player.

`--alpha 1.0` trusts raw points only; `--alpha 0.0` trusts expected points
only.

Run tests with `python -m pytest tests/`.

## Limitations

- Without `--live`, prices and club assignments are last season's final
  values, and players from relegated clubs are still in the pool.
- With `--live`, players with no last-season history (new signings,
  promoted-team players) get a zero score and are never picked.
- The projection is a season-total blend; it does not model fixtures,
  minutes risk, or price changes.

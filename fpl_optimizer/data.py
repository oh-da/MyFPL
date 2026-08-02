"""Load player data.

Two sources:
- Historical per-gameweek stats CSV (last season) -> per-player season aggregates.
- Live FPL API (bootstrap-static) -> current player list, teams and prices.

When the live API is used, last-season stats are matched onto the current
player list by name/team so prices and availability are up to date.
"""

import json
import unicodedata
import urllib.request

import pandas as pd

FPL_API_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"


def load_history(csv_path: str) -> pd.DataFrame:
    """Aggregate per-gameweek rows into one row per player.

    Returns columns: id, web_name, team_name, element_type, price,
    total_points, expected_points, minutes, appearances.
    Team, position and price are taken from the player's latest gameweek row
    (players can move clubs mid-season).
    """
    gw = pd.read_csv(csv_path)
    gw = gw.sort_values("gameweek")

    latest = gw.groupby("id").last()
    totals = gw.groupby("id").agg(
        total_points=("total_points", "sum"),
        expected_points=("expected_points", "sum"),
        minutes=("minutes", "sum"),
        appearances=("minutes", lambda m: int((m > 0).sum())),
    )
    players = totals.join(
        latest[["web_name", "team_name", "element_type", "now_cost"]]
    ).rename(columns={"now_cost": "price"})
    return players.reset_index()


def fetch_live_players(url: str = FPL_API_URL) -> pd.DataFrame:
    """Fetch the current season's player list and prices from the FPL API."""
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.load(resp)
    teams = {t["id"]: t["name"] for t in data["teams"]}
    rows = [
        {
            "id": e["id"],
            "web_name": e["web_name"],
            "team_name": teams[e["team"]],
            "element_type": e["element_type"],
            "price": e["now_cost"] / 10.0,  # API prices are in 0.1m units
            "status": e["status"],  # 'a' = available
        }
        for e in data["elements"]
    ]
    return pd.DataFrame(rows)


def _name_key(name: str) -> str:
    return (
        unicodedata.normalize("NFKD", name)
        .encode("ascii", "ignore")
        .decode()
        .lower()
    )


def merge_live_with_history(live: pd.DataFrame, history: pd.DataFrame) -> pd.DataFrame:
    """Attach last-season stats to the live player list.

    Matches on (name, team) first, then on name alone when it is unambiguous.
    Players with no history (new signings, promoted-team players) keep zero
    stats and are effectively never selected.
    """
    hist = history.copy()
    hist["_name"] = hist["web_name"].map(_name_key)
    hist["_key"] = hist["_name"] + "|" + hist["team_name"]

    by_key = hist.set_index("_key")
    name_counts = hist["_name"].value_counts()
    by_name = hist[hist["_name"].map(name_counts) == 1].set_index("_name")

    stat_cols = ["total_points", "expected_points", "minutes", "appearances"]
    out = live.copy()
    for col in stat_cols:
        out[col] = 0.0

    for i, row in out.iterrows():
        name = _name_key(row["web_name"])
        key = name + "|" + row["team_name"]
        if key in by_key.index:
            match = by_key.loc[key]
        elif name in by_name.index:
            match = by_name.loc[name]
        else:
            continue
        for col in stat_cols:
            out.at[i, col] = match[col]

    return out

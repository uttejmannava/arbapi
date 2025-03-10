import requests
import json
from datetime import datetime

def get_odds(sport: str, api_key: str, market: str, bookmakers: list) -> list:
    
    url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"
    params = {
        "apiKey": api_key,
        "markets": market, # only 1 market at a time - guarantees request size
        "bookmakers": ",".join(bookmakers),
        "oddsFormat": "decimal",
        "includeLinks": 'true',
        "includeSids": 'true',
        "includeBetLimits": 'true',
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()

        raw_data = response.json()
        formatted_data = []

        for game in raw_data:
            game_data = {
                "game_id": game["id"],
                "home_team": game["home_team"],
                "away_team": game["away_team"],
                "commence_time": datetime.fromisoformat(game["commence_time"].replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S"),
                "bookmakers": {}
            }

            for bookmaker in game["bookmakers"]:
                bookmaker_data = {
                    "name": bookmaker["title"],
                    "market": market,
                    "last_update": datetime.fromisoformat(bookmaker["last_update"].replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S"),
                    "game_link": bookmaker["link"],
                    "game_sid": bookmaker["sid"],
                    "odds": {}
                }

                if bookmaker["markets"]:
                    # Initialize a temporary dictionary to store outcomes
                    temp_odds = {}

                    for outcome in bookmaker["markets"][0]["outcomes"]:
                        point = outcome.get("point")
                        if point is not None:
                            point = float(point)
                        odds = outcome["price"]

                        if market == "totals":
                            # Store outcomes in temp_odds to ensure they are added once
                            if outcome["name"] == "Over":
                                temp_odds["home"] = (outcome["name"], [odds, point])
                            elif outcome["name"] == "Under":
                                temp_odds["away"] = (outcome["name"], [odds, point])

                        elif market == "spreads":
                            # Handle spreads, considering potential flips
                            if outcome["name"] == game["home_team"]:
                                home_point = point
                                away_point = -point
                                temp_odds["home"] = (outcome["name"], [odds, point])
                            elif outcome["name"] == game["away_team"]:
                                away_point = point
                                home_point = -point
                                temp_odds["away"] = (outcome["name"], [odds, point])

                        elif market == "h2h":
                            # Directly add h2h odds, ensuring home team is first
                            if outcome["name"] == game["home_team"]:
                                temp_odds["home"] = (outcome["name"], [odds])
                            elif outcome["name"] == game["away_team"]:
                                temp_odds["away"] = (outcome["name"], [odds])

                    # Add bookmaker data for totals
                    if market == "totals" and "home" in temp_odds and "away" in temp_odds:
                        if point not in game_data["bookmakers"]:
                            game_data["bookmakers"][point] = []
                        bookmaker_data["odds"][temp_odds["home"][0]] = temp_odds["home"][1]
                        bookmaker_data["odds"][temp_odds["away"][0]] = temp_odds["away"][1]
                        game_data["bookmakers"][point].append(bookmaker_data)

                    # Ensure the home team comes first in the odds dictionary for spreads
                    if market == "spreads" and "home" in temp_odds and "away" in temp_odds:
                        bookmaker_data["odds"][temp_odds["home"][0]] = temp_odds["home"][1]
                        bookmaker_data["odds"][temp_odds["away"][0]] = temp_odds["away"][1]

                        # Use a string representation of the tuple to group spreads
                        point_pair = f"{temp_odds['home'][1][1]}/{temp_odds['away'][1][1]}"
                        if point_pair not in game_data["bookmakers"]:
                            game_data["bookmakers"][point_pair] = []
                        game_data["bookmakers"][point_pair].append(bookmaker_data)

                    # Add bookmaker data for h2h
                    if market == "h2h" and "home" in temp_odds and "away" in temp_odds:
                        bookmaker_data["odds"][temp_odds["home"][0]] = temp_odds["home"][1]
                        bookmaker_data["odds"][temp_odds["away"][0]] = temp_odds["away"][1]
                        if "default" not in game_data["bookmakers"]:
                            game_data["bookmakers"]["default"] = []
                        game_data["bookmakers"]["default"].append(bookmaker_data)

            formatted_data.append(game_data)

        remaining_requests = response.headers.get('x-requests-remaining', 'Unknown')
        formatted_data.append({"remaining_requests": remaining_requests})
        formatted_data.append({"sport": sport, "market": market, "bookmakers": bookmakers})
 
        return formatted_data

    except requests.exceptions.RequestException as e:
        if isinstance(e, requests.exceptions.HTTPError):
            if e.response.status_code == 401:
                print("Error: Invalid API key")
            elif e.response.status_code == 429:
                print("Error: API request limit exceeded")
            else:
                print(f"HTTP Error: {e}")
        elif isinstance(e, requests.exceptions.ConnectionError):
            print("Error: Unable to connect to the API")
        elif isinstance(e, requests.exceptions.Timeout):
            print("Error: API request timed out")
        else:
            print(f"An unexpected error occurred: {e}")
        return None
    except json.JSONDecodeError:
        print("Error: Unable to parse API response")
        return None
    except KeyError as e:
        print(f"Error: Expected data not found in API response: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None


# find best odds for each market passed in
def best_odds(processed_odds: list) -> list:
    # just the games, not the requests header
    data = processed_odds[:-2]
    sport, market = processed_odds[-1]["sport"], processed_odds[-1]["market"]
    best_odds = []

    for game in data:
        game_best_odds = {
            "game_id": game["game_id"],
            "sport": sport,
            "home_team": game["home_team"],
            "away_team": game["away_team"],
            "commence_time": game["commence_time"],
            "market": market,
            "best_odds": {}
        }

        if market == "h2h":
            best_h2h = {
                "outcome_a": {
                    "name": None,
                    "odds": None,
                    "bookmaker": None,
                    "last_update": None,
                    "game_link": None,
                    "game_sid": None
                },
                "outcome_b": {
                    "name": None,
                    "odds": None,
                    "bookmaker": None,
                    "last_update": None,
                    "game_link": None,
                    "game_sid": None
                }
            }
            for bookmaker in game["bookmakers"].get("default", []):
                for outcome_name, outcome_details in bookmaker["odds"].items():
                    if outcome_name == game["home_team"]:
                        if best_h2h["outcome_a"]["odds"] is None or outcome_details[0] > best_h2h["outcome_a"]["odds"]:
                            best_h2h["outcome_a"].update({
                                "name": outcome_name,
                                "odds": outcome_details[0],
                                "bookmaker": bookmaker["name"],
                                "last_update": bookmaker["last_update"],
                                "game_link": bookmaker["game_link"],
                                "game_sid": bookmaker["game_sid"]
                            })
                    elif outcome_name == game["away_team"]:
                        if best_h2h["outcome_b"]["odds"] is None or outcome_details[0] > best_h2h["outcome_b"]["odds"]:
                            best_h2h["outcome_b"].update({
                                "name": outcome_name,
                                "odds": outcome_details[0],
                                "bookmaker": bookmaker["name"],
                                "last_update": bookmaker["last_update"],
                                "game_link": bookmaker["game_link"],
                                "game_sid": bookmaker["game_sid"]
                            })
            game_best_odds["best_odds"] = best_h2h

        elif market == "totals":
            for point, bookmakers in game["bookmakers"].items():
                best_totals = {
                    "outcome_a": {
                        "name": None,
                        "odds": None,
                        "point": None,
                        "bookmaker": None,
                        "last_update": None,
                        "game_link": None,
                        "game_sid": None
                    },
                    "outcome_b": {
                        "name": None,
                        "odds": None,
                        "point": None,
                        "bookmaker": None,
                        "last_update": None,
                        "game_link": None,
                        "game_sid": None
                    }
                }
                for bookmaker in bookmakers:
                    for outcome_name, outcome_details in bookmaker["odds"].items():
                        if outcome_name == "Over":
                            if best_totals["outcome_a"]["odds"] is None or outcome_details[0] > best_totals["outcome_a"]["odds"]:
                                best_totals["outcome_a"].update({
                                    "name": outcome_name,
                                    "odds": outcome_details[0],
                                    "point": point,
                                    "bookmaker": bookmaker["name"],
                                    "last_update": bookmaker["last_update"],
                                    "game_link": bookmaker["game_link"],
                                    "game_sid": bookmaker["game_sid"]
                                })
                        elif outcome_name == "Under":
                            if best_totals["outcome_b"]["odds"] is None or outcome_details[0] > best_totals["outcome_b"]["odds"]:
                                best_totals["outcome_b"].update({
                                    "name": outcome_name,
                                    "odds": outcome_details[0],
                                    "point": point,
                                    "bookmaker": bookmaker["name"],
                                    "last_update": bookmaker["last_update"],
                                    "game_link": bookmaker["game_link"],
                                    "game_sid": bookmaker["game_sid"]
                                })
                game_best_odds["best_odds"][point] = best_totals

        elif market == "spreads":
            for point_pair, bookmakers in game["bookmakers"].items():
                best_spreads = {
                    "outcome_a": {
                        "name": None,
                        "odds": None,
                        "bookmaker": None,
                        "last_update": None,
                        "game_link": None,
                        "game_sid": None
                    },
                    "outcome_b": {
                        "name": None,
                        "odds": None,
                        "bookmaker": None,
                        "last_update": None,
                        "game_link": None,
                        "game_sid": None
                    }
                }
                for bookmaker in bookmakers:
                    for outcome_name, outcome_details in bookmaker["odds"].items():
                        if outcome_name == game["home_team"]:
                            if best_spreads["outcome_a"]["odds"] is None or outcome_details[0] > best_spreads["outcome_a"]["odds"]:
                                best_spreads["outcome_a"].update({
                                    "name": outcome_name,
                                    "odds": outcome_details[0],
                                    "point": point_pair,
                                    "bookmaker": bookmaker["name"],
                                    "last_update": bookmaker["last_update"],
                                    "game_link": bookmaker["game_link"],
                                    "game_sid": bookmaker["game_sid"]
                                })
                        elif outcome_name == game["away_team"]:
                            if best_spreads["outcome_b"]["odds"] is None or outcome_details[0] > best_spreads["outcome_b"]["odds"]:
                                best_spreads["outcome_b"].update({
                                    "name": outcome_name,
                                    "odds": outcome_details[0],
                                    "point": point_pair,
                                    "bookmaker": bookmaker["name"],
                                    "last_update": bookmaker["last_update"],
                                    "game_link": bookmaker["game_link"],
                                    "game_sid": bookmaker["game_sid"]
                                })
                game_best_odds["best_odds"][point_pair] = best_spreads

        if game_best_odds["best_odds"]:
            best_odds.append(game_best_odds)
        
    best_odds.append(processed_odds[-2:])

    return best_odds


# find arb and low-hold pairs
def arb_pairs(best_odds: list, total_stake: float = 1000) -> dict:
    data = best_odds[:-1]
    pairs = {"arb_pairs": [], "low_hold_pairs": [], "low_vig_pairs": []}

    for game in data:
        game_id = game["game_id"]
        sport = game["sport"]
        market = game["market"]
        home_team = game["home_team"]
        away_team = game["away_team"]
        commence_time = game["commence_time"]

        if market == "h2h":
            best_h2h = game["best_odds"]
            # Check if both odds are not None
            if best_h2h["outcome_a"]["odds"] is not None and best_h2h["outcome_b"]["odds"] is not None:
                arb_value, arb_data = calculate_arb(best_h2h, total_stake)
                if arb_value < 1:
                    pairs["arb_pairs"].append(format_arb_data(game_id, sport, market, home_team, away_team, commence_time, arb_data, best_h2h))
                elif arb_value == 1:
                    pairs["low_hold_pairs"].append(format_arb_data(game_id, sport, market, home_team, away_team, commence_time, arb_data, best_h2h))
                elif 1 < arb_value < 1.01:
                    pairs["low_vig_pairs"].append(format_arb_data(game_id, sport, market, home_team, away_team, commence_time, arb_data, best_h2h))

        elif market == "totals":
            for point, best_totals in game["best_odds"].items():
                if best_totals["outcome_a"]["odds"] is not None and best_totals["outcome_b"]["odds"] is not None:
                    arb_value, arb_data = calculate_arb(best_totals, total_stake)
                    if arb_value < 1:
                        pairs["arb_pairs"].append(format_arb_data(game_id, sport, market, home_team, away_team, commence_time, arb_data, best_totals, point))
                    elif arb_value == 1:
                        pairs["low_hold_pairs"].append(format_arb_data(game_id, sport, market, home_team, away_team, commence_time, arb_data, best_totals, point))
                    elif 1 < arb_value < 1.01:
                        pairs["low_vig_pairs"].append(format_arb_data(game_id, sport, market, home_team, away_team, commence_time, arb_data, best_totals, point))

        elif market == "spreads":
            for point_pair, best_spreads in game["best_odds"].items():
                if best_spreads["outcome_a"]["odds"] is not None and best_spreads["outcome_b"]["odds"] is not None:
                    arb_value, arb_data = calculate_arb(best_spreads, total_stake)
                    if arb_value < 1:
                        pairs["arb_pairs"].append(format_arb_data(game_id, sport, market, home_team, away_team, commence_time, arb_data, best_spreads, point_pair))
                    elif arb_value == 1:
                        pairs["low_hold_pairs"].append(format_arb_data(game_id, sport, market, home_team, away_team, commence_time, arb_data, best_spreads, point_pair))
                    elif 1 < arb_value < 1.01:
                        pairs["low_vig_pairs"].append(format_arb_data(game_id, sport, market, home_team, away_team, commence_time, arb_data, best_spreads, point_pair))

    pairs["metadata"] = best_odds[-1:]
    return pairs

def calculate_arb(best_odds, total_stake):
    decimal_a = best_odds["outcome_a"]["odds"]
    decimal_b = best_odds["outcome_b"]["odds"]

    implied_prob_a = 1 / decimal_a
    implied_prob_b = 1 / decimal_b

    arb_value = implied_prob_a + implied_prob_b

    # Calculate stakes for arbitrage
    stake_a = total_stake * implied_prob_a / (implied_prob_a + implied_prob_b)
    stake_b = total_stake * implied_prob_b / (implied_prob_a + implied_prob_b)

    # Weighted outcome a bet (win on a, break-even on b)
    wa_stake_b = (total_stake + 0) / decimal_b
    wa_stake_a = total_stake - wa_stake_b

    # Weighted outcome b bet (win on b, break-even on a)
    wb_stake_a = (total_stake + 0) / decimal_a
    wb_stake_b = total_stake - wb_stake_a

    arb_data = {
        "arb": f"{round(-(arb_value - 1) * 100, 3)}%",
        "arb_amount": {
            "outcome_a": round(stake_a, 2),
            "outcome_b": round(stake_b, 2)
        },
        "weighted_amounts_a": {
            "outcome_a": round(wa_stake_a, 2),
            "outcome_b": round(wa_stake_b, 2)
        },
        "weighted_amounts_b": {
            "outcome_a": round(wb_stake_a, 2),
            "outcome_b": round(wb_stake_b, 2)
        }
    }

    return arb_value, arb_data

def format_arb_data(game_id, sport, market, home_team, away_team, commence_time, arb_data, best_odds, point=None):
    arb_info = {
        "game_id": game_id,
        "sport": sport,
        "market": market,
        "home_team": home_team,
        "away_team": away_team,
        "commence_time": commence_time,
        "arbitrage": arb_data,
        "outcome_a_details": {
            "bookmaker": best_odds["outcome_a"]["bookmaker"],
            "game_link": best_odds["outcome_a"]["game_link"],
            "game_sid": best_odds["outcome_a"]["game_sid"],
            "last_update": best_odds["outcome_a"]["last_update"],
            "odds": best_odds["outcome_a"]["odds"]
        },
        "outcome_b_details": {
            "bookmaker": best_odds["outcome_b"]["bookmaker"],
            "game_link": best_odds["outcome_b"]["game_link"],
            "game_sid": best_odds["outcome_b"]["game_sid"],
            "last_update": best_odds["outcome_b"]["last_update"],
            "odds": best_odds["outcome_b"]["odds"]
        }
    }
    if point:
        arb_info["point"] = point
    return arb_info
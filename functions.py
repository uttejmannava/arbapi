import requests
import json
from datetime import datetime

# works for ML (h2h)
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
                "bookmakers": []
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

                hook_lines = True
                
                if bookmaker["markets"]:
                    for outcome in bookmaker["markets"][0]["outcomes"]:
                        if "point" in outcome:
                            if not str(outcome["point"]).endswith(".5"):
                                hook_lines = False
                                break
                            bookmaker_data["odds"][outcome["name"]] = [outcome["price"], outcome["point"]]
                        else:
                            bookmaker_data["odds"][outcome["name"]] = [outcome["price"]]

                if hook_lines:
                    game_data["bookmakers"].append(bookmaker_data)
            
            formatted_data.append(game_data)

        # remaining requests - key rotation
        remaining_requests = response.headers.get('x-requests-remaining', 'Unknown')
        formatted_data.append({"remaining_requests": remaining_requests})
        formatted_data.append({"sport": sport,
                               "market": market,
                               "bookmakers": bookmakers
                               })

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
            "best_odds": {
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
        }

        for bookmaker in game["bookmakers"]:
            for outcome_name, outcome_details in bookmaker["odds"].items():

                outcome_type = None
                if outcome_name == game["home_team"]:
                    outcome_type = "outcome_a"
                elif outcome_name == game["away_team"]:
                    outcome_type = "outcome_b"
                elif outcome_name == "Over":
                    outcome_type = "outcome_a"
                elif outcome_name == "Under":
                    outcome_type = "outcome_b"
                

                if outcome_type and (game_best_odds["best_odds"][outcome_type]["odds"] is None or outcome_details[0] > game_best_odds["best_odds"][outcome_type]["odds"]):
                    game_best_odds["best_odds"][outcome_type]["odds"] = outcome_details[0]
                    if len(outcome_details) > 1:
                        game_best_odds["best_odds"][outcome_type]["point"] = outcome_details[1]
                    game_best_odds["best_odds"][outcome_type]["name"] = outcome_name
                    game_best_odds["best_odds"][outcome_type]["bookmaker"] = bookmaker["name"]
                    game_best_odds["best_odds"][outcome_type]["last_update"] = bookmaker["last_update"]
                    game_best_odds["best_odds"][outcome_type]["game_link"] = bookmaker["game_link"]
                    game_best_odds["best_odds"][outcome_type]["game_sid"] = bookmaker["game_sid"]

        # # Adjust for spreads: ensure the points for outcome_a and outcome_b are inverses
        # if market == "spreads":
        #     outcome_a = game_best_odds["best_odds"]["outcome_a"]
        #     outcome_b = game_best_odds["best_odds"]["outcome_b"]

        #     # Only pair spreads if both have valid points and are inverses
        #     if outcome_a["point"] is not None and outcome_b["point"] is not None:
        #         if outcome_a["point"] != -outcome_b["point"]:
        #             # Reset the unmatched side
        #             if abs(outcome_a["point"]) < abs(outcome_b["point"]):
        #                 game_best_odds["best_odds"]["outcome_b"] = {
        #                     "name": None,
        #                     "odds": None,
        #                     "point": None,
        #                     "bookmaker": None,
        #                     "last_update": None,
        #                     "game_link": None,
        #                     "game_sid": None,
        #                 }
        #             else:
        #                 game_best_odds["best_odds"]["outcome_a"] = {
        #                     "name": None,
        #                     "odds": None,
        #                     "point": None,
        #                     "bookmaker": None,
        #                     "last_update": None,
        #                     "game_link": None,
        #                     "game_sid": None,
        #                 }
        
        if not (game_best_odds["best_odds"]["outcome_a"]["odds"] == None and game_best_odds["best_odds"]["outcome_b"]["odds"] == None):
            best_odds.append(game_best_odds)
        
    best_odds.append(processed_odds[-2:])

    return best_odds


# find arb and low-hold pairs
def arb_pairs(best_odds: list, total_stake: float = 1000) -> dict:

    data = best_odds[:-1]

    pairs = {"arb_pairs": [],
             "low_hold_pairs": []
             }
    
    for game in data:

        decimal_a = game["best_odds"]["outcome_a"]["odds"]
        decimal_b = game["best_odds"]["outcome_b"]["odds"]

        implied_prob_a = 1 / decimal_a
        implied_prob_b = 1 / decimal_b

        arb_value = implied_prob_a + implied_prob_b

        # arb pair
        if arb_value < 1:

            # assuming $1000 total stake per arb
            stake_a = total_stake * implied_prob_a / (implied_prob_a + implied_prob_b)
            stake_b = total_stake * implied_prob_b / (implied_prob_a + implied_prob_b)

            # weighted outcome a bet (win on a, break-even on b)
            wa_stake_b = (total_stake + 0) / decimal_b
            wa_stake_a = total_stake - wa_stake_b

            # weighted outcome b bet (win on b, break-even on a)
            wb_stake_a = (total_stake + 0) / decimal_a
            wb_stake_b = total_stake - wb_stake_a

            game["arbitrage"] = {
                "arb_value": f"{round(-(arb_value - 1) * 100, 3)}%",
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

            pairs["arb_pairs"].append(game)

        # low-hold pair
        elif arb_value == 1:
            
            # assuming $1000 total stake per low-hold
            stake_a = 1000 * implied_prob_a / (implied_prob_a + implied_prob_b)
            stake_b = 1000 * implied_prob_b / (implied_prob_a + implied_prob_b)
            
            game["arbitrage"] = {
                "arb_value": f"{round(-(arb_value - 1) * 100, 3)}%",
                "arb_amount": {
                    "outcome_a": round(stake_a, 2),
                    "outcome_b": round(stake_b, 2)
                }
            }

            pairs["low_hold_pairs"].append(game)
    
    pairs["metadata"] = best_odds[-1:]

    return pairs
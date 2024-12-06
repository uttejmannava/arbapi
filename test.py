from functions import *
from dotenv import load_dotenv
import os

from constants import *

load_dotenv()

# raw = get_odds('basketball_nba', os.getenv("ODDS_API_KEY"), 'h2h', BOOKMAKERS)
# best = best_odds(raw)
# arb = arb_pairs(best)

# print(json.dumps(arb, indent=2))

api_keys = json.loads(os.environ["ODDS_KEY_LIST"])
print(api_keys)

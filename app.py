from flask import Flask, jsonify
import asyncio
import redis
import json
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor

from constants import *
from functions import get_odds, best_odds, arb_pairs

app = Flask(__name__)
executor = ThreadPoolExecutor()

redis_client = redis.Redis(host='localhost', port=6379, db=0)

# async function to offload get_odds
async def async_get_odds(sport):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, get_odds, sport)

@app.route('/odds/raw/<sport>', methods=['GET'])
async def get_raw_odds(sport):

    # raw_odds = await async_get_odds(sport)

    cached = redis_client.get('raw_odds_data')

    if cached:
        return jsonify(json.loads(cached))

    raw_odds = async_get_odds(sport)

    #dump raw_odds json into Redis cache
    redis_client.setex('raw_odds_data', timedelta(seconds=CACHE_TTL), json.dumps(raw_odds))

    return jsonify(raw_odds)


@app.route('/odds/best/<sport>', methods=['GET'])
async def get_best_odds(sport):
    
    raw = get_raw_odds(sport)

    return jsonify(best_odds(raw))


@app.route('/odds/arb/<sport>', methods=['GET'])
async def get_arb_pairs(sport):
    
    best = get_best_odds(sport)

    return jsonify(arb_pairs(best))


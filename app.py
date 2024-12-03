from flask import Flask, jsonify
import asyncio
import redis
import json
from datetime import timedelta, datetime
from concurrent.futures import ThreadPoolExecutor
import os

from constants import *
from functions import get_odds, best_odds, arb_pairs

app = Flask(__name__)
executor = ThreadPoolExecutor()

redis_client = redis.Redis(host='localhost', port=6379, db=0)

# async function to offload get_odds
async def async_get_odds(sport, market):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, get_odds, sport, os.getenv("ODDS_API_KEY"), market, BOOKMAKERS)

@app.route('/odds/raw/<sport>/<market>', methods=['GET'])
async def get_raw_odds(sport, market):
    cache_key = f'raw_odds_data_{sport}_{market}'
    timestamp_key = f'{cache_key}_timestamp'

    cached = redis_client.get(cache_key)
    timestamp = redis_client.get(timestamp_key)

    if cached:
        response = json.loads(cached)
        if isinstance(response, list):
            response = {"data": response}  # Wrap list in a dictionary
        timestamp = timestamp.decode('utf-8') if timestamp else None
        response['timestamp'] = timestamp
        return jsonify(response)

    raw_odds = await async_get_odds(sport, market)

    # Ensure raw_odds is a dictionary
    if isinstance(raw_odds, list):
        raw_odds = {"data": raw_odds}

    # Dump raw_odds json into Redis cache
    redis_client.setex(cache_key, timedelta(seconds=CACHE_TTL), json.dumps(raw_odds))
    current_timestamp = datetime.utcnow().isoformat()
    redis_client.setex(timestamp_key, timedelta(seconds=CACHE_TTL), current_timestamp)

    raw_odds['timestamp'] = current_timestamp
    return jsonify(raw_odds)


@app.route('/odds/best/<sport>/<market>', methods=['GET'])
async def get_best_odds(sport, market):
    raw_response = await get_raw_odds(sport, market)
    raw_data = raw_response.get_json()
    best_data = best_odds(raw_data["data"])  # Access the list from the dictionary
    best_data = {"data": best_data, "timestamp": raw_data.get('timestamp')}
    return jsonify(best_data)


@app.route('/odds/arb/<sport>/<market>', methods=['GET'])
async def get_arb_pairs(sport, market):
    best_response = await get_best_odds(sport, market)
    best_data = best_response.get_json()
    arb_data = arb_pairs(best_data["data"])  # Access the list from the dictionary
    arb_data = {"data": arb_data, "timestamp": best_data.get('timestamp')}
    return jsonify(arb_data)
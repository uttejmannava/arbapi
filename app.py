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

# Load API key list from environment
api_keys = json.loads(os.environ['ODDS_KEY_LIST'])
current_key_index_key = "current_api_key_index"

# Initialize the current API key index if not set
if not redis_client.exists(current_key_index_key):
    redis_client.set(current_key_index_key, 0)

def get_current_api_key():
    index = int(redis_client.get(current_key_index_key))
    return api_keys[index]

def rotate_api_key():
    current_index = int(redis_client.get(current_key_index_key))
    new_index = (current_index + 1) % len(api_keys)
    redis_client.set(current_key_index_key, new_index)
    print(f"Rotated API key to index {new_index}")

# async function to offload get_odds
async def async_get_odds(sport, market):
    loop = asyncio.get_event_loop()
    current_api_key = get_current_api_key()
    return await loop.run_in_executor(executor, get_odds, sport, current_api_key, market, BOOKMAKERS)


@app.route('/', methods=['GET'])
def index():
    return jsonify({"message": "Welcome to the Arb API!"})


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

    # Check remaining requests and rotate API key if necessary
    remaining_requests = raw_odds['data'][-2]["remaining_requests"]
    print(f"Remaining requests: {remaining_requests}")
    if remaining_requests == 0:
       rotate_api_key()

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
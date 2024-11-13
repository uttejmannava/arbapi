from flask import Flask, jsonify
import requests
import redis
import json
from datetime import timedelta

from constants import *

app = Flask(__name__)

# setup Redis client
redis_client = redis.Redis(host='localhost', port=6379, db=0)


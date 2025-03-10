# ArbAPI

ArbAPI identifies arbitrage, low-hold, and low-vig opportunities in sports betting markets. This project was created to streamline the process of analyzing betting odds across multiple bookmakers.

## Features

- **Real-time Odds Collection**: Fetches odds data for multiple Ontario bookmakers; supports any given sports league.
- **Arbitrage Detection**: Identifies arbitrage opportunities by comparing best odds across different bookmakers; currently supporting moneyline, game totals, and game spreads markets.
- **Low-Hold/Low-Vig**: Low-hold pairs = 0% arbitrage, good for getting VIP status. Low-vig opportunities are ~ -1% arbs that can be used for funneling new account creation/referral bonuses.
- **API Key Rotation**: Broke so I use a ton of free keys (shoutout The Odds API). Rotating to ensure continuous data access without exceeding request limits 🤫.
- **Redis Caching**: Utilizes Redis for caching odds data, improving response times. Pregame odds for game lines don't change too often, empirically found a TTL of 5 minutes to be sufficient.

## Stack

- **Backend**: Python, Flask
- **Data Fetching**: Requests for API calls, The Odds API for raw data
- **Asynchronous Processing**: Asyncio and ThreadPoolExecutor for non-blocking I/O operations
- **Caching**: Redis for caching odds data
- **Deployment**: ~~AWS Lambda with Zappa for serverless deployment~~ Render for API hosting, Upstash for Redis caching

~~## AWS Services Used~~

~~- **AWS Lambda**: Provides serverless compute to run the API without headache of servers.~~
~~- **Amazon ElastiCache for Redis**: Caching raw odds data (TTL = 5 min) for speed and API request management.~~
~~- **VPC**: Secure network environment; private subnets.~~
~~- **NAT Gateway**: Allows private subnets to access the internet; facilitates calls to underlying API for raw data.~~
~~- **CloudWatch Monitoring**: Monitors application performance and logs. My lifesaver in getting this API up and running 🙏.~~

-----------------------------------------------

Deployed at: https://arbapi.onrender.com/
Example: https://arbapi.onrender.com/odds/raw/icehockey_nhl/h2h
(may take ~1 min to spin up if API has been inactive for some time)
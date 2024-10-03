import dataclasses
import json
import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from fastapi import HTTPException, Request
from pytz import timezone
from redis.asyncio import Redis
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from app.infra import redis_vm

_redis_client: Redis | None = None  # Global redis client

# Load environment variables from .env file
load_dotenv()
ALLOW_LIST = os.getenv("ALLOW_LIST", "").split(",")
DAILY_REQUEST_LIMIT = 10


@dataclasses.dataclass
class RateLimitStatus:
    ip: str
    requests_made: int
    requests_remaining: int
    reset_time: str
    is_allow_listed: bool


async def initialize_rate_limiter():
    global _redis_client
    if _redis_client is not None:
        return
        # raise ValueError("Redis client already set up.")

    _redis_client = await redis_vm.redis_async()


async def _get_redis_client():
    global _redis_client
    if _redis_client is None:
        raise ValueError("Redis client not set up.")
    return _redis_client


async def _build_redis_key(ip: str) -> str:
    """Generate the Redis key for the current day and given IP."""
    pst = timezone("US/Pacific")
    current_day = datetime.now(pst).strftime("%Y-%m-%d")
    return f"rate_limit:{ip}:{current_day}"


async def _check_limits(ip: str):
    """Check Redis for rate limit data and return the current count and remaining."""
    client = await _get_redis_client()
    key = await _build_redis_key(ip)
    limit_data = await client.get(key)

    if limit_data:
        data = json.loads(limit_data)
        requests_made = data["requests_made"]
    else:
        requests_made = 0

    requests_remaining = DAILY_REQUEST_LIMIT - requests_made
    return requests_made, requests_remaining


async def _increment_request_count(ip: str):
    """Increment the request count for the IP in Redis."""
    client = await _get_redis_client()
    requests_made, _ = await _check_limits(ip)
    key = await _build_redis_key(ip)
    await client.set(
        key,
        json.dumps({"requests_made": requests_made + 1}),
        ex=int(timedelta(days=1).total_seconds()),  # Set expiry for 24 hours
    )


async def rate_limit(request: Request):
    """Rate limit logic for FastAPI dependency."""
    if request.client is None:
        raise HTTPException(
            status_code=HTTP_429_TOO_MANY_REQUESTS,
            detail="Client IP address not found.",
        )

    ip = request.client.host

    if ip in ALLOW_LIST:
        return True

    requests_made, requests_remaining = await _check_limits(ip)

    if requests_made >= DAILY_REQUEST_LIMIT:
        raise HTTPException(
            status_code=HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. You can make {DAILY_REQUEST_LIMIT} requests per day.",
        )

    await _increment_request_count(ip)
    return True


async def rate_limit_status_only(request: Request):
    """Return the rate limit status without limiting the request."""
    if request.client is None:
        raise HTTPException(
            status_code=HTTP_429_TOO_MANY_REQUESTS,
            detail="Client IP address not found.",
        )

    ip = request.client.host

    if ip in ALLOW_LIST:
        return RateLimitStatus(
            ip=ip,
            requests_made=-1,
            requests_remaining=-1,
            reset_time="N/A (Allow-listed IP)",
            is_allow_listed=True,
        )

    requests_made, requests_remaining = await _check_limits(ip)

    pst = timezone("US/Pacific")
    now_pst = datetime.now(pst)
    reset_time = datetime(
        now_pst.year, now_pst.month, now_pst.day, 23, 59, 59, tzinfo=pst
    )

    return RateLimitStatus(
        ip=ip,
        requests_made=requests_made,
        requests_remaining=requests_remaining,
        reset_time=reset_time.isoformat(),
        is_allow_listed=False,
    )


if __name__ == "__main__":
    import asyncio
    import sys

    async def run_commands():
        # Command To Run: python rate_limit.py ping
        if len(sys.argv) > 1 and sys.argv[1] == "ping":
            client = await _get_redis_client()
            print(f"PING: {await client.ping()}")

        # Command To Run: python rate_limit.py flush
        if len(sys.argv) > 1 and sys.argv[1] == "flush":
            client = await _get_redis_client()
            await client.flushall()
            print("Redis cache flushed.")

        # Command To Run: python rate_limit.py ssh
        if len(sys.argv) > 1 and sys.argv[1] == "ssh":
            redis_vm.ssh()

    asyncio.run(initialize_rate_limiter())
    asyncio.run(run_commands())

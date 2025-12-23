"""IP address extraction utilities."""

from fastapi import Request


def extract_client_ip(request: Request) -> str | None:
    """Extract client IP address from request headers.

    Checks headers in priority order:
    1. X-Real-IP - common proxy header
    2. X-Forwarded-For - standard proxy header (uses leftmost IP)
    3. CF-Connecting-IP - Cloudflare header
    4. request.client.host - fallback to direct connection

    Args:
        request: The incoming FastAPI/Starlette request

    Returns:
        IP address string, or None if unable to extract
    """
    if "x-real-ip" in request.headers:
        return request.headers["x-real-ip"]

    if "x-forwarded-for" in request.headers:
        forwarded_ips = request.headers["x-forwarded-for"].split(",")
        if forwarded_ips:
            return forwarded_ips[0].strip()

    if "cf-connecting-ip" in request.headers:
        return request.headers["cf-connecting-ip"]

    if request.client:
        return request.client.host

    return None

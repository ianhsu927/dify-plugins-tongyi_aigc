"""Use the same regional/workspace host for generation and task polling."""
from urllib.parse import urlsplit


def api_url(credentials, path):
    host = str(credentials.get("api_base_url") or "https://dashscope.aliyuncs.com").rstrip("/")
    parsed = urlsplit(host)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("API Base URL must be an HTTPS host without credentials")
    if parsed.path or parsed.query or parsed.fragment:
        raise ValueError("API Base URL must not include a path, query or fragment")
    # Only official endpoints may receive the provider API key.
    if not (parsed.hostname in {"dashscope.aliyuncs.com", "dashscope-intl.aliyuncs.com", "dashscope-us.aliyuncs.com"}
            or parsed.hostname.endswith(".maas.aliyuncs.com")):
        raise ValueError("API Base URL must be an official DashScope/MAAS endpoint")
    return host + path

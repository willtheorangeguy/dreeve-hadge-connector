"""Probe the real Dreeve web server from inside the isolated test network."""

import json
import sys
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

headers = {"Authorization": "Bearer drv_" + "1" * 64} if "--authenticated" in sys.argv else {}
request = Request("http://app:8080" + sys.argv[1], headers=headers)
opener = build_opener(ProxyHandler({}))
try:
    response = opener.open(request, timeout=15)
except HTTPError as exc:
    response = exc
with response:
    print(json.dumps({"status": response.status, "body": response.read().decode("utf-8")}))

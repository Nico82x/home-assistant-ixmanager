"""Cognito SRP and read-only GraphQL client. Tokens remain in memory."""
import asyncio
from functools import partial
import time

import aiohttp
import boto3
from botocore import UNSIGNED
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from pycognito.aws_srp import AWSSRP

from .const import API_URL, CLIENT_ID, REGION, USER_POOL_ID
from .models import SchemaError, parse_device
from .queries import DISCOVER, GET_DEVICE, LIVE_DATA

class ApiError(Exception):
    """Cloud request failed (messages never include server bodies or secrets)."""

class AuthError(ApiError):
    """Credentials rejected or authentication challenge unsupported."""

class NoDevicesError(ApiError):
    """No pool devices accessible to this account."""

_AUTH_CODES = {"NotAuthorizedException", "UserNotFoundException", "UserNotConfirmedException",
               "PasswordResetRequiredException"}

class IxmanagerApi:
    def __init__(self, session, executor, username, password, lang="de"):
        self.session = session
        self.executor = executor
        self.username = username
        self._password = password
        self.lang = lang
        self._client = None
        self._access_token = None
        self._refresh_token = None
        self._expires = 0
        self._auth_lock = asyncio.Lock()
        self.account_id = None

    def _sync_auth(self, force=False):
        if self._client is None:
            self._client = boto3.client("cognito-idp", region_name=REGION,
                config=Config(signature_version=UNSIGNED, connect_timeout=10,
                              read_timeout=20, retries={"max_attempts": 1}))
        if not force and self._access_token and time.monotonic() < self._expires:
            return self._access_token
        result = None
        if self._refresh_token:
            try:
                result = self._client.initiate_auth(AuthFlow="REFRESH_TOKEN_AUTH",
                    ClientId=CLIENT_ID, AuthParameters={"REFRESH_TOKEN": self._refresh_token})
            except ClientError as err:
                if err.response.get("Error", {}).get("Code") != "NotAuthorizedException":
                    raise
                self._refresh_token = None
        if result is None:
            # A fresh SRP ephemeral key is generated for every login.
            srp = AWSSRP(username=self.username, password=self._password,
                         pool_id=USER_POOL_ID, client_id=CLIENT_ID, client=self._client)
            params = srp.get_auth_params()
            result = self._client.initiate_auth(AuthFlow="USER_SRP_AUTH",
                ClientId=CLIENT_ID, AuthParameters=params)
            if result.get("ChallengeName") == "PASSWORD_VERIFIER":
                response = srp.process_challenge(result["ChallengeParameters"], params)
                extra = {"Session": result["Session"]} if result.get("Session") else {}
                result = self._client.respond_to_auth_challenge(ClientId=CLIENT_ID,
                    ChallengeName="PASSWORD_VERIFIER", ChallengeResponses=response, **extra)
        tokens = result.get("AuthenticationResult")
        if not tokens:
            raise AuthError("Additional login challenge required; use iXfield to resolve it")
        self._access_token = tokens["AccessToken"]
        self._refresh_token = tokens.get("RefreshToken", self._refresh_token)
        self._expires = time.monotonic() + max(0, int(tokens.get("ExpiresIn", 3600)) - 90)
        return self._access_token

    async def async_token(self, rejected_token=None):
        async with self._auth_lock:
            # Another request may have already refreshed the rejected token.
            force = rejected_token is not None and rejected_token == self._access_token
            try:
                return await self.executor(partial(self._sync_auth, force))
            except ClientError as err:
                if err.response.get("Error", {}).get("Code") in _AUTH_CODES:
                    raise AuthError("Cognito rejected authentication") from None
                raise ApiError("Cognito request failed") from None
            except BotoCoreError:
                raise ApiError("Cognito connection failed") from None
            except (KeyError, ValueError, TypeError):
                raise ApiError("Unexpected Cognito response") from None

    async def async_query(self, query, operation, variables):
        token = await self.async_token()
        for attempt in range(2):
            try:
                async with self.session.post(API_URL,
                    json={"query": query, "operationName": operation, "variables": variables},
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=aiohttp.ClientTimeout(total=30), allow_redirects=False) as response:
                    rejected = response.status in (401, 403)
                    if not rejected:
                        if response.status != 200:
                            raise ApiError(f"GraphQL HTTP {response.status}")
                        body = await response.json()
                        if not isinstance(body, dict):
                            raise ApiError("Invalid GraphQL response")
                        errors = body.get("errors") or []
                        rejected = any(isinstance(e, dict) and
                            (e.get("extensions") or {}).get("code") in
                            ("UNAUTHENTICATED", "UNAUTHORIZED") for e in errors)
                        if errors and not rejected:
                            raise ApiError("GraphQL returned errors")
                        if not rejected:
                            data = body.get("data")
                            if not isinstance(data, dict):
                                raise ApiError("Missing GraphQL data")
                            return data
            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
                raise ApiError("GraphQL connection or response failed") from None
            if attempt:
                raise AuthError("API authorization rejected after token renewal")
            token = await self.async_token(rejected_token=token)
        raise ApiError("GraphQL request failed")

    async def async_discover(self):
        devices = {}
        for page in range(1, 101):
            data = await self.async_query(DISCOVER, "GetUserDevices", {"pageNumber": page})
            me = data.get("me")
            if not isinstance(me, dict) or not isinstance(me.get("id"), str):
                raise ApiError("Missing account data")
            self.account_id = me["id"]
            rows = me.get("devices")
            if not isinstance(rows, list):
                raise ApiError("Missing device list")
            if not rows:
                if not devices:
                    raise NoDevicesError("No pool devices found")
                return list(devices)
            for row in rows:
                if not isinstance(row, dict) or not isinstance(row.get("id"), str):
                    raise ApiError("Invalid device discovery entry")
                if row["id"] in devices:
                    raise ApiError("Device pagination repeated a device")
                devices[row["id"]] = True
        raise ApiError("Device pagination limit exceeded")

    async def async_device(self, device_id, initial=False):
        data = await self.async_query(GET_DEVICE if initial else LIVE_DATA,
            "GetDevice" if initial else "deviceLiveData", {"id": device_id, "lang": self.lang})
        try:
            device = parse_device(data.get("device"))
            if device.id != device_id:
                raise SchemaError("Device ID mismatch")
            return device
        except SchemaError:
            raise ApiError("Unexpected device metadata; update integration") from None

    async def async_close(self):
        """Release the Cognito HTTP pool; HA owns the aiohttp session."""
        async with self._auth_lock:
            if self._client is not None:
                await self.executor(self._client.close)
                self._client = None
            self._access_token = self._refresh_token = None
            self._expires = 0

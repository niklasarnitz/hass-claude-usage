"""Claude Usage integration for Home Assistant."""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    ANTIGRAVITY_FETCH_MODELS_URL,
    ANTIGRAVITY_TOKEN_URL,
    API_BETA_HEADER,
    CODEX_USAGE_URL,
    CONF_ACCESS_TOKEN,
    CONF_ANTIGRAVITY_ACCESS_TOKEN,
    CONF_ANTIGRAVITY_CLIENT_ID,
    CONF_ANTIGRAVITY_CLIENT_SECRET,
    CONF_ANTIGRAVITY_EXPIRES_AT,
    CONF_ANTIGRAVITY_PROJECT_ID,
    CONF_ANTIGRAVITY_REFRESH_TOKEN,
    CONF_CODEX_ACCESS_TOKEN,
    CONF_CODEX_ACCOUNT_ID,
    CONF_EXPIRES_AT,
    CONF_PROVIDER,
    CONF_REFRESH_TOKEN,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    OAUTH_CLIENT_ID,
    OAUTH_TOKEN_URL,
    PROVIDER_ANTIGRAVITY,
    PROVIDER_CLAUDE,
    PROVIDER_CODEX,
    USAGE_API_URL,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]

type ClaudeUsageConfigEntry = ConfigEntry[DataUpdateCoordinator[dict[str, Any]]]


async def async_setup_entry(hass: HomeAssistant, entry: ClaudeUsageConfigEntry) -> bool:
    """Set up from a config entry."""
    provider = entry.data.get(CONF_PROVIDER, PROVIDER_CLAUDE)

    if provider == PROVIDER_CODEX:
        coordinator: DataUpdateCoordinator[dict[str, Any]] = CodexUsageCoordinator(hass, entry)
    elif provider == PROVIDER_ANTIGRAVITY:
        coordinator = AntigravityUsageCoordinator(hass, entry)
    else:
        coordinator = ClaudeUsageCoordinator(hass, entry)

    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ClaudeUsageConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(hass: HomeAssistant, entry: ClaudeUsageConfigEntry) -> None:
    """Handle options update."""
    coordinator = entry.runtime_data
    interval = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
    coordinator.update_interval = timedelta(seconds=interval)


class ClaudeUsageCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to fetch Claude usage data."""

    config_entry: ClaudeUsageConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ClaudeUsageConfigEntry) -> None:
        """Initialize the coordinator."""
        interval = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
            config_entry=entry,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch usage data from the API."""
        await self._ensure_valid_token()

        access_token = self.config_entry.data[CONF_ACCESS_TOKEN]
        headers = {
            "Authorization": f"Bearer {access_token}",
            "anthropic-beta": API_BETA_HEADER,
        }

        try:
            session = aiohttp_client.async_get_clientsession(self.hass)
            resp = await session.get(
                USAGE_API_URL, headers=headers, timeout=aiohttp.ClientTimeout(total=15)
            )
            if resp.status == 401:
                raise ConfigEntryAuthFailed("Authentication failed - token may be invalid")
            resp.raise_for_status()
            raw = await resp.json()
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error fetching usage data: {err}") from err

        return _parse_claude_usage(raw)

    async def _ensure_valid_token(self) -> None:
        """Refresh the access token if expired."""
        expires_at = self.config_entry.data.get(CONF_EXPIRES_AT, 0)
        if time.time() < expires_at - 60:
            return

        refresh_token = self.config_entry.data.get(CONF_REFRESH_TOKEN)
        if not refresh_token:
            raise UpdateFailed("No refresh token available")

        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": OAUTH_CLIENT_ID,
        }

        try:
            session = aiohttp_client.async_get_clientsession(self.hass)
            resp = await session.post(
                OAUTH_TOKEN_URL,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=aiohttp.ClientTimeout(total=15),
            )
            if not resp.ok:
                raise ConfigEntryAuthFailed(f"Token refresh failed ({resp.status})")
            token_data = await resp.json()
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Token refresh request failed: {err}") from err

        if "access_token" not in token_data:
            raise ConfigEntryAuthFailed("Token refresh response missing access_token")

        new_data = {
            **self.config_entry.data,
            CONF_ACCESS_TOKEN: token_data["access_token"],
            CONF_REFRESH_TOKEN: token_data.get("refresh_token", refresh_token),
            CONF_EXPIRES_AT: time.time() + token_data.get("expires_in", 3600),
        }
        self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)


class CodexUsageCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to fetch OpenAI Codex usage data."""

    config_entry: ClaudeUsageConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ClaudeUsageConfigEntry) -> None:
        """Initialize the coordinator."""
        interval = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_codex",
            update_interval=timedelta(seconds=interval),
            config_entry=entry,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch usage data from the Codex API."""
        token = self.config_entry.data[CONF_CODEX_ACCESS_TOKEN]
        account_id = self.config_entry.data.get(CONF_CODEX_ACCOUNT_ID)

        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": "CodexBar",
            "Accept": "application/json",
        }
        if account_id:
            headers["ChatGPT-Account-Id"] = account_id

        try:
            session = aiohttp_client.async_get_clientsession(self.hass)
            resp = await session.get(
                CODEX_USAGE_URL,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15),
            )
            if resp.status in (401, 403):
                raise ConfigEntryAuthFailed("Codex token expired or invalid")
            resp.raise_for_status()
            raw = await resp.json()
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error fetching Codex usage: {err}") from err

        return _parse_codex_usage(raw)


class AntigravityUsageCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to fetch Google Antigravity (Code Assist) usage data."""

    config_entry: ClaudeUsageConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ClaudeUsageConfigEntry) -> None:
        """Initialize the coordinator."""
        interval = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_antigravity",
            update_interval=timedelta(seconds=interval),
            config_entry=entry,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch usage data from the Antigravity API."""
        await self._ensure_valid_token()

        token = self.config_entry.data[CONF_ANTIGRAVITY_ACCESS_TOKEN]
        project_id = self.config_entry.data.get(CONF_ANTIGRAVITY_PROJECT_ID)

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "antigravity",
        }

        body: dict[str, Any] = {}
        if project_id:
            body["project"] = project_id

        try:
            session = aiohttp_client.async_get_clientsession(self.hass)
            resp = await session.post(
                ANTIGRAVITY_FETCH_MODELS_URL,
                headers=headers,
                json=body,
                timeout=aiohttp.ClientTimeout(total=15),
            )
            if resp.status == 401:
                raise ConfigEntryAuthFailed("Antigravity token expired or invalid")
            resp.raise_for_status()
            raw = await resp.json()
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error fetching Antigravity usage: {err}") from err

        return _parse_antigravity_usage(raw)

    async def _ensure_valid_token(self) -> None:
        """Refresh the Google access token if expired."""
        expires_at = self.config_entry.data.get(CONF_ANTIGRAVITY_EXPIRES_AT, 0)
        if time.time() < expires_at - 60:
            return

        refresh_token = self.config_entry.data.get(CONF_ANTIGRAVITY_REFRESH_TOKEN)
        client_id = self.config_entry.data.get(CONF_ANTIGRAVITY_CLIENT_ID)
        client_secret = self.config_entry.data.get(CONF_ANTIGRAVITY_CLIENT_SECRET)

        if not all([refresh_token, client_id, client_secret]):
            raise UpdateFailed("Missing Antigravity refresh credentials")

        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        }

        try:
            session = aiohttp_client.async_get_clientsession(self.hass)
            resp = await session.post(
                ANTIGRAVITY_TOKEN_URL,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=aiohttp.ClientTimeout(total=15),
            )
            if not resp.ok:
                raise ConfigEntryAuthFailed(f"Antigravity token refresh failed ({resp.status})")
            token_data = await resp.json()
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Antigravity token refresh failed: {err}") from err

        if "access_token" not in token_data:
            raise ConfigEntryAuthFailed("Antigravity token refresh response missing access_token")

        new_data = {
            **self.config_entry.data,
            CONF_ANTIGRAVITY_ACCESS_TOKEN: token_data["access_token"],
            CONF_ANTIGRAVITY_EXPIRES_AT: time.time() + token_data.get("expires_in", 3600),
        }
        self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)


def _parse_claude_usage(raw: dict[str, Any]) -> dict[str, Any]:
    """Parse raw Claude API response into flat sensor data dict."""
    data: dict[str, Any] = {}

    five_hour = raw.get("five_hour")
    if five_hour:
        data["session_usage_percent"] = five_hour.get("utilization")
        data["session_reset_time"] = five_hour.get("resets_at")

    seven_day = raw.get("seven_day")
    if seven_day:
        utilization = seven_day.get("utilization")
        reset_time = seven_day.get("resets_at")
        data["week_usage_percent"] = utilization
        data["week_reset_time"] = reset_time
        if utilization is not None and reset_time:
            try:
                reset_dt = datetime.fromisoformat(reset_time)
                now = datetime.now(UTC)
                week_seconds = 7 * 24 * 60 * 60
                elapsed = week_seconds - (reset_dt - now).total_seconds()
                percent_elapsed = (elapsed / week_seconds) * 100
                data["week_usage_pace"] = round(utilization - percent_elapsed, 1)
            except (ValueError, TypeError):
                pass

    seven_day_sonnet = raw.get("seven_day_sonnet")
    if seven_day_sonnet:
        data["week_sonnet_usage_percent"] = seven_day_sonnet.get("utilization")
        data["week_sonnet_reset_time"] = seven_day_sonnet.get("resets_at")

    extra = raw.get("extra_usage")
    if extra:
        data["extra_usage_enabled"] = extra.get("is_enabled", False)
        data["extra_usage_percent"] = extra.get("utilization")
        data["extra_usage_credits"] = (
            extra["used_credits"] / 100 if extra.get("used_credits") is not None else None
        )
        data["extra_usage_limit"] = (
            extra["monthly_limit"] / 100 if extra.get("monthly_limit") is not None else None
        )

    return data


def _parse_codex_usage(raw: dict[str, Any]) -> dict[str, Any]:
    """Parse raw Codex API response into flat sensor data dict."""
    data: dict[str, Any] = {}

    rate_limit = raw.get("rate_limit") or {}

    primary = rate_limit.get("primary_window")
    if primary:
        data["codex_primary_used_percent"] = primary.get("used_percent")
        reset_at = primary.get("reset_at")
        if reset_at is not None:
            data["codex_primary_reset_at"] = datetime.fromtimestamp(reset_at, tz=UTC).isoformat()

    secondary = rate_limit.get("secondary_window")
    if secondary:
        data["codex_secondary_used_percent"] = secondary.get("used_percent")
        reset_at = secondary.get("reset_at")
        if reset_at is not None:
            data["codex_secondary_reset_at"] = datetime.fromtimestamp(reset_at, tz=UTC).isoformat()

    plan_type = raw.get("plan_type")
    if plan_type is not None:
        data["codex_plan_type"] = plan_type

    credits = raw.get("credits") or {}
    balance = credits.get("balance")
    if balance is not None:
        data["codex_credits_balance"] = balance

    return data


def _parse_antigravity_usage(raw: dict[str, Any]) -> dict[str, Any]:
    """Parse raw Antigravity API response into per-model quota data."""
    models: dict[str, Any] = {}

    for model_id, model in (raw.get("models") or {}).items():
        quota_info = model.get("quotaInfo") or model.get("quota_info") or {}
        remaining = quota_info.get("remainingFraction") or quota_info.get("remaining_fraction")
        reset_time = quota_info.get("resetTime") or quota_info.get("reset_time")
        label = (
            model.get("displayName")
            or model.get("display_name")
            or model.get("label")
            or model_id
        )
        models[model_id] = {
            "label": label,
            "remaining_fraction": remaining,
            "reset_time": reset_time,
        }

    return {"models": models}

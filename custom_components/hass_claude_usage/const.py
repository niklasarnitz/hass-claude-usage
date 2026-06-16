"""Constants for Claude Usage integration."""

DOMAIN = "hass_claude_usage"

# Providers
CONF_PROVIDER = "provider"
PROVIDER_CLAUDE = "claude"
PROVIDER_CODEX = "codex"
PROVIDER_ANTIGRAVITY = "antigravity"

# OAuth (Claude)
OAUTH_CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
OAUTH_AUTHORIZE_URL = "https://claude.ai/oauth/authorize"
OAUTH_TOKEN_URL = "https://console.anthropic.com/v1/oauth/token"
OAUTH_REDIRECT_URI = "https://console.anthropic.com/oauth/code/callback"
OAUTH_SCOPES = "org:create_api_key user:profile user:inference"

# API (Claude)
USAGE_API_URL = "https://api.anthropic.com/api/oauth/usage"
PROFILE_API_URL = "https://api.anthropic.com/api/oauth/profile"
API_BETA_HEADER = "oauth-2025-04-20"

# API (Codex / OpenAI)
CODEX_USAGE_URL = "https://chatgpt.com/backend-api/wham/usage"

# API (Antigravity / Google Code Assist)
ANTIGRAVITY_BASE_URL = "https://cloudcode-pa.googleapis.com"
ANTIGRAVITY_LOAD_CODE_ASSIST_URL = f"{ANTIGRAVITY_BASE_URL}/v1internal:loadCodeAssist"
ANTIGRAVITY_FETCH_MODELS_URL = f"{ANTIGRAVITY_BASE_URL}/v1internal:fetchAvailableModels"
ANTIGRAVITY_RETRIEVE_QUOTA_URL = f"{ANTIGRAVITY_BASE_URL}/v1internal:retrieveUserQuota"
ANTIGRAVITY_TOKEN_URL = "https://oauth2.googleapis.com/token"

# Defaults
DEFAULT_UPDATE_INTERVAL = 300  # seconds

# Config keys (Claude)
CONF_ACCESS_TOKEN = "access_token"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_EXPIRES_AT = "expires_at"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_ACCOUNT_NAME = "account_name"
CONF_SUBSCRIPTION_LEVEL = "subscription_level"

# Config keys (Codex)
CONF_CODEX_ACCESS_TOKEN = "codex_access_token"
CONF_CODEX_ACCOUNT_ID = "codex_account_id"

# Config keys (Antigravity)
CONF_ANTIGRAVITY_ACCESS_TOKEN = "antigravity_access_token"
CONF_ANTIGRAVITY_REFRESH_TOKEN = "antigravity_refresh_token"
CONF_ANTIGRAVITY_CLIENT_ID = "antigravity_client_id"
CONF_ANTIGRAVITY_CLIENT_SECRET = "antigravity_client_secret"
CONF_ANTIGRAVITY_EXPIRES_AT = "antigravity_expires_at"
CONF_ANTIGRAVITY_PROJECT_ID = "antigravity_project_id"

# Sensor definitions: (key, name, unit, icon, device_class)
SENSOR_DEFINITIONS = [
    ("session_usage_percent", "Session Usage", "%", "mdi:timer-sand", None),
    (
        "session_reset_time",
        "Session Reset Time",
        None,
        "mdi:timer-refresh",
        "timestamp",
    ),
    ("week_usage_percent", "Week Usage", "%", "mdi:calendar-week", None),
    ("week_usage_pace", "Week Usage Pace", "%", "mdi:speedometer", None),
    ("week_reset_time", "Weekly Reset Time", None, "mdi:calendar-clock", "timestamp"),
    (
        "week_sonnet_usage_percent",
        "Weekly Sonnet Usage",
        "%",
        "mdi:calendar-week",
        None,
    ),
    (
        "week_sonnet_reset_time",
        "Weekly Sonnet Reset Time",
        None,
        "mdi:calendar-clock",
        "timestamp",
    ),
    ("extra_usage_enabled", "Extra Usage Enabled", None, "mdi:toggle-switch", None),
    ("extra_usage_percent", "Extra Usage", "%", "mdi:credit-card", None),
    (
        "extra_usage_credits",
        "Extra Usage Credits",
        "credits",
        "mdi:credit-card-outline",
        None,
    ),
    (
        "extra_usage_limit",
        "Extra Usage Limit",
        "credits",
        "mdi:credit-card-settings",
        None,
    ),
    ("api_error", "API Error", "errors", "mdi:alert-circle", None),
]

# Codex sensor definitions: (key, name, unit, icon, device_class)
CODEX_SENSOR_DEFINITIONS = [
    (
        "codex_primary_used_percent",
        "Session Used",
        "%",
        "mdi:timer-sand",
        None,
    ),
    (
        "codex_primary_reset_at",
        "Session Reset Time",
        None,
        "mdi:timer-refresh",
        "timestamp",
    ),
    (
        "codex_secondary_used_percent",
        "Weekly Used",
        "%",
        "mdi:calendar-week",
        None,
    ),
    (
        "codex_secondary_reset_at",
        "Weekly Reset Time",
        None,
        "mdi:calendar-clock",
        "timestamp",
    ),
    (
        "codex_plan_type",
        "Plan Type",
        None,
        "mdi:account-star",
        None,
    ),
    (
        "codex_credits_balance",
        "Credits Balance",
        "USD",
        "mdi:credit-card-outline",
        None,
    ),
    ("codex_api_error", "API Error", "errors", "mdi:alert-circle", None),
]

"""Constants of the quirk installer."""

from datetime import timedelta

DOMAIN = "xquirks"
TITLE = "xquirks"
# The service device's model: the integration page shows it under the device's name.
DESCRIPTION = "Extra quirks for ZHA"

ZHA_DOMAIN = "zha"
CONF_CUSTOM_QUIRKS_PATH = "custom_quirks_path"
# Options: the ids of the devices xquirks leaves alone.
CONF_EXCLUDED = "excluded"

STORAGE_KEY = f"{DOMAIN}.installed"
STORAGE_VERSION = 1

# Seconds to wait for more device registry changes before checking again.
REFRESH_COOLDOWN = 10

# A Tuya device that talks through the Tuya MCU cluster sends all its datapoints by itself only when
# it joins. A data query (a command without payload) makes it send them again. The quirk ZHA applies
# tells such a device: it puts zhaquirks' Tuya MCU cluster on it, which names this command query_data.
TUYA_CLUSTER = 0xEF00
TUYA_QUERY_DATA = 0x03

# The repository whose content-<n> tags carry the quirk files.
REPOSITORY = "jabla/xquirks"
TAGS_URL = f"https://api.github.com/repos/{REPOSITORY}/git/matching-refs/tags/content-"
# Files are read at the commit a tag points to, never by the tag's name: a branch of the same name
# must not stand in for the protected tag.
RAW_URL = f"https://raw.githubusercontent.com/{REPOSITORY}/{{commit}}/{{path}}"
CHECK_INTERVAL = timedelta(hours=6)
# How often to try again while no content state is in use.
RETRY_INTERVAL = timedelta(minutes=15)
FETCH_TIMEOUT = 30
# A quirk file or manifest larger than this is refused.
MAX_DOWNLOAD = 4 * 1024 * 1024

CONTENT_STORAGE_KEY = f"{DOMAIN}.content"
CONTENT_STORAGE_VERSION = 1

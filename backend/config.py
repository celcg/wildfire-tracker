"""Application configuration with no web or data-access responsibilities."""

import os
from pathlib import Path

from dotenv import load_dotenv


# Local development reads .env; Cloud Run continues to inject the same variable.
load_dotenv()

NASA_KEY = os.getenv("NASA_KEY")

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://project-d66d4e5f-ee28-4c77-845.web.app",
    "https://project-d66d4e5f-ee28-4c77-845.firebaseapp.com",
]

NASA_DATASET = "VIIRS_NOAA20_NRT"
IBERIAN_BOUNDS = "-10,35,5,44"
FIRE_COLUMNS = [
    "latitude",
    "longitude",
    "confidence",
    "acq_date",
    "acq_time",
    "satellite",
    "frp",
]

# NASA is never queried more than once per interval by the same API instance.
CACHE_TTL_SECONDS = 60 * 60
# A cold instance with no successful data retries sooner after NASA failures,
# while the cap prevents an outage from causing sustained upstream traffic.
NASA_BACKOFF_INITIAL_SECONDS = 60
NASA_BACKOFF_MAX_SECONDS = 15 * 60
# Anonymous clients are identified by an opaque browser-installation UUID. The
# HMAC secret keeps that identifier out of Firestore document names and logs.
IS_CLOUD_RUN = bool(os.getenv("K_SERVICE"))
CLIENT_ID_HASH_SECRET = os.getenv(
    "CLIENT_ID_HASH_SECRET",
    "wildfire-local-development-only" if not IS_CLOUD_RUN else "",
)
APP_CHECK_REQUIRED = os.getenv(
    "APP_CHECK_REQUIRED",
    "true" if IS_CLOUD_RUN else "false",
).lower() in {"1", "true", "yes", "on"}
# This switch exists only to support a zero-downtime rollout from older clients.
# Production keeps it enabled after the updated frontend has been published.
CLIENT_ID_REQUIRED = os.getenv(
    "CLIENT_ID_REQUIRED",
    "true" if IS_CLOUD_RUN else "false",
).lower() in {"1", "true", "yes", "on"}
RATE_LIMIT_BACKEND = os.getenv(
    "RATE_LIMIT_BACKEND",
    "firestore" if IS_CLOUD_RUN else "memory",
).lower()
FIRESTORE_PROJECT_ID = os.getenv("FIRESTORE_PROJECT_ID")
TOKEN_BUCKET_CAPACITY = int(os.getenv("TOKEN_BUCKET_CAPACITY", "5"))
TOKEN_BUCKET_REFILL_SECONDS = float(
    os.getenv("TOKEN_BUCKET_REFILL_SECONDS", "12")
)
TOKEN_BUCKET_STATE_TTL_SECONDS = int(
    os.getenv("TOKEN_BUCKET_STATE_TTL_SECONDS", str(24 * 60 * 60))
)
# A wider process-local guard absorbs repeated clicks and protects Firestore
# during outages; the shared token bucket remains the authoritative limit.
LOCAL_GUARD_CAPACITY = int(os.getenv("LOCAL_GUARD_CAPACITY", "20"))
LOCAL_GUARD_REFILL_SECONDS = float(
    os.getenv("LOCAL_GUARD_REFILL_SECONDS", "3")
)

# Local logs are useful during development, while Cloud Run should write only
# to stdout because its writable filesystem is ephemeral and consumes memory.
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_TO_FILE = os.getenv(
    "LOG_TO_FILE",
    "false" if os.getenv("K_SERVICE") else "true",
).lower() in {"1", "true", "yes", "on"}
LOG_FILE_PATH = os.getenv(
    "LOG_FILE_PATH",
    str(Path(__file__).resolve().parent / "logs" / "wildfire-api.log"),
)
LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", str(5 * 1024 * 1024)))
# One active 5 MiB file plus 19 backups bounds local logs to about 100 MiB.
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "19"))

# Clusters link detections only when they are close in both space and time.
# Keeping these server-owned avoids presenting arbitrary tuning as user choice.
CLUSTER_RADIUS_KM = 2
CLUSTER_TIME_WINDOW_HOURS = 24

# A small context margin turns one- and two-point groups into visible areas.
# It is a visualization envelope, not an estimated burned-area perimeter.
CLUSTER_ENVELOPE_BUFFER_KM = 1

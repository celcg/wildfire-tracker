"""Application configuration with no web or data-access responsibilities."""

import os

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

# These conservative in-memory limits reduce upstream requests per instance.
CACHE_TTL_SECONDS = 15 * 60
RATE_LIMIT_REQUESTS = 10
RATE_LIMIT_WINDOW_SECONDS = 60

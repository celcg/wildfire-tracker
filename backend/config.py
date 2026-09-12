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

# NASA is never queried more than once per interval by the same API instance.
CACHE_TTL_SECONDS = 60 * 60
RATE_LIMIT_REQUESTS = 10
RATE_LIMIT_WINDOW_SECONDS = 60

# Clusters link detections only when they are close in both space and time.
# Keeping these server-owned avoids presenting arbitrary tuning as user choice.
CLUSTER_RADIUS_KM = 2
CLUSTER_TIME_WINDOW_HOURS = 12

# A small context margin turns one- and two-point groups into visible areas.
# It is a visualization envelope, not an estimated burned-area perimeter.
CLUSTER_ENVELOPE_BUFFER_KM = 1

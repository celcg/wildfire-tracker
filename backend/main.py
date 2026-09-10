import os
from typing import Annotated

import pandas as pd

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware


load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://project-d66d4e5f-ee28-4c77-845.web.app",
        "https://project-d66d4e5f-ee28-4c77-845.firebaseapp.com",
    ],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Accept", "Content-Type"],
)

NASA_KEY = os.getenv("NASA_KEY")
FIRE_COLUMNS = [
    "latitude",
    "longitude",
    "confidence",
    "acq_date",
    "acq_time",
    "satellite",
    "frp",
]


def fetch_fires(days: int) -> pd.DataFrame:
    if not NASA_KEY:
        raise HTTPException(status_code=503, detail="NASA_KEY is not configured")

    url = (
        "https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
        f"{NASA_KEY}/"
        "VIIRS_NOAA20_NRT/"
        "-10,35,5,44/"
        f"{days}"
    )

    try:
        return pd.read_csv(url)[FIRE_COLUMNS]
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="NASA FIRMS data is temporarily unavailable",
        ) from exc


@app.get("/")
def home():
    return {"message": "Wildfire API working"}


@app.get("/fires")
def fires(days: Annotated[int, Query(ge=1, le=10)] = 1):
    return fetch_fires(days).to_dict(orient="records")


@app.get("/stats")
def stats(days: Annotated[int, Query(ge=1, le=10)] = 1):
    df = fetch_fires(days)
    frp = pd.to_numeric(df["frp"], errors="coerce").dropna()

    return {
        "days": days,
        "total_detections": len(df),
        "average_frp": round(float(frp.mean()), 2) if not frp.empty else 0,
        "maximum_frp": round(float(frp.max()), 2) if not frp.empty else 0,
        "detections_by_satellite": df["satellite"].value_counts().to_dict(),
    }

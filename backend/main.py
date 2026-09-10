import os
import pandas as pd

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://project-d66d4e5f-ee28-4c77-845.web.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

NASA_KEY = os.getenv("NASA_KEY")


@app.get("/")
def home():
    return {"message": "Wildfire API working"}


@app.get("/fires")
def fires():
    url = (
        "https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
        f"{NASA_KEY}/"
        "VIIRS_NOAA20_NRT/"
        "-10,35,5,44/"
        "1"
    )

    df = pd.read_csv(url)

    return df[
        [
            "latitude",
            "longitude",
            "confidence",
            "acq_date",
            "acq_time",
            "satellite",
            "frp",
        ]
    ].to_dict(orient="records")
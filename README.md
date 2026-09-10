# Wildfire Tracker

## Introduction

Wildfire Tracker is a full-stack geospatial web application that displays recent satellite-detected fire activity across the Iberian Peninsula. It combines a React map interface with a FastAPI service that retrieves near-real-time observations from NASA FIRMS.

The project demonstrates API design, third-party data integration, cloud deployment, CORS configuration, asynchronous UI state, and interactive geospatial visualization.

## Deployed URLs

- **Web application:** [Firebase Hosting](https://project-d66d4e5f-ee28-4c77-845.web.app/)
- **REST API:** [Google Cloud Run](https://wildfire-api-440479996053.europe-west1.run.app/)
- **Interactive API documentation:** [Swagger UI](https://wildfire-api-440479996053.europe-west1.run.app/docs)

## Features

- Interactive Leaflet map centered on the Iberian Peninsula
- Recent wildfire detections sourced from NASA FIRMS
- Detection details including date, time, satellite, confidence, and fire radiative power
- Responsive React interface hosted on Firebase
- REST API hosted as a containerized service on Google Cloud Run
- Configurable observation window and aggregate statistics

## Architecture

```text
User selects a time window
          |
          v
React + React Leaflet (Firebase Hosting)
          |
          | HTTPS / JSON
          v
FastAPI REST API (Google Cloud Run)
          |
          | CSV data request
          v
NASA FIRMS API
```

The frontend and API are deployed independently. FastAPI acts as a small backend-for-frontend layer: it protects the NASA API key, defines a stable JSON contract, and keeps external data-processing concerns out of the browser.

## Tech Stack + Why

- **React:** component-driven UI and predictable state updates when users change the observation window.
- **Vite:** fast local development and a lightweight optimized production build.
- **React Leaflet / Leaflet:** mature, open-source tools for interactive geospatial visualization.
- **FastAPI:** typed query validation, automatic OpenAPI documentation, and concise REST endpoint development.
- **Pandas:** convenient parsing and transformation of the CSV responses returned by NASA FIRMS.
- **NASA FIRMS:** authoritative near-real-time satellite fire-detection data.
- **Firebase Hosting:** simple, globally distributed hosting for the static frontend.
- **Google Cloud Run:** managed, scalable hosting for the Python API with environment-based secret configuration.

## Local Development

Create `backend/.env` and provide a valid NASA FIRMS key:

```env
NASA_KEY=your_nasa_firms_key
```

Start the API:

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

Start the frontend in a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

## API Overview

```http
GET /
GET /fires?days=1
GET /fires?days=3
GET /fires?days=5
GET /stats
```

Using a `days` query parameter keeps the resource-oriented API extensible and avoids creating separate endpoints for every supported time window.


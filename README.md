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
- Explainable spatiotemporal grouping into possible fire clusters
- Switchable detection and cluster layers with aggregate FRP insights
- Persistent browser cache with an explicit manual refresh action
- Fifteen-minute API cache and a conservative 10-request-per-minute limit per client

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
          | CSV data request + explainable clustering
          v
NASA FIRMS API
```

The frontend and API are deployed independently. FastAPI acts as a small backend-for-frontend layer: it protects the NASA API key, defines a stable JSON contract, and keeps external data-processing concerns out of the browser. The browser reuses cached results until the user requests a refresh, while each Cloud Run instance keeps a short-lived shared cache to reduce repeated NASA calls.

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
GET /fires?days=3&refresh=true
GET /stats?days=1
GET /incidents?days=3
GET /incidents?days=3&refresh=true
```

Using a `days` query parameter keeps the resource-oriented API extensible and avoids creating separate endpoints for every supported time window.

Setting `refresh=true` explicitly bypasses the API cache. Data endpoints are limited to 10 requests per minute per client and return `429 Too Many Requests` with a `Retry-After` header when that limit is exceeded. The lightweight limiter and server cache are process-local, so a production system that scales to many Cloud Run instances should move both to a shared store such as Redis.

## Intelligent Fire Clustering

The optional cluster layer turns nearby satellite observations into possible
fire areas. Two detections are connected when they occur within **3 km** and
**12 hours** of one another; transitive connections form one component. The
implementation uses the Haversine distance and a Union-Find data structure, so
the method remains lightweight and explainable without adding a machine-learning
runtime to the Cloud Run image.

Each possible cluster reports its geographic center, detection count, aggregate
and peak FRP, observation span, dominant confidence category, and a simple FRP
trend. Stable identifiers are derived from source observations, allowing clients
to track the same group when response ordering changes.

The cluster response also includes the exact source detections used by each
group and a convex observation envelope with a 1 km context buffer. The frontend
draws that translucent envelope behind the original FRP-sized points, so no
synthetic centroid replaces or obscures the underlying observations. The
envelope is an explainable visualization aid, not a measured burned perimeter.

Clusters, severity colors, and trends are analytical aids. They are **not
confirmed wildfire incidents, emergency classifications, or forecasts**.

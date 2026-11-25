# SkyWatch — Weather Forecast & Alert Application

A Python weather monitoring demo with live city search, five-day forecasts, configurable weather alerts, downloadable reports, a FastAPI backend, and a Plotly-powered Streamlit dashboard. Simulation scenarios work offline and exercise each alert type.

> **Safety note:** Thresholds are examples for learning and are not official warnings or safety advice. Follow local meteorological services for important decisions.

## Overview

Weather affects travel, outdoor events, farming, deliveries, and daily planning. SkyWatch collects weather for a named city, turns API JSON into a consistent forecast model, checks configurable thresholds, and presents the results through an API and dashboard. The same Python service powers CLI reports, FastAPI, and Streamlit.

### Features

- Open-Meteo geocoding and live current conditions plus a five-day daily forecast
- Hourly temperature, feels-like temperature, humidity, precipitation probability, rain amount, wind, and weather codes
- Severity-tagged high temperature, humidity, rain probability, wind, and thunderstorm alerts
- Six deterministic offline simulation choices: normal and one scenario per alert family
- FastAPI JSON routes with query validation and clear HTTP status codes
- Streamlit dashboard that calls FastAPI over HTTP, with Plotly charts, location map, and CSV/JSON downloads
- Timestamp-unique JSON and CSV report snapshots in `outputs/`
- Missing values handled safely; network requests use timeouts

## Technology

Python 3.10+, `requests`, Open-Meteo Forecast and Geocoding APIs, FastAPI, Uvicorn, Streamlit, Plotly, and Pandas. No API key is needed for Open-Meteo's public endpoints.

## Architecture

```text
Streamlit dashboard ──HTTP──> FastAPI (/weather)
                                   │
                                   v
                      Shared weather service
                        /                 \
                sample JSON        Open-Meteo APIs
                        \                 /
                         normalize + alert engine
                                   │
                       JSON/CSV reports in outputs/
```

## Project structure

```text
├── data/sample_weather.json     # synthetic offline sample and five-day summary
├── src/weather_app.py           # fetch, normalize, alerts, reports, CLI
├── src/api.py                   # FastAPI HTTP interface
├── src/dashboard.py             # Streamlit HTTP client and charts
├── tests/test_weather_app.py    # service and API checks
├── outputs/                     # generated unique CSV/JSON reports (gitignored)
├── images/screenshots/          # place genuine screenshots here
├── docs/implementation-plan.md
├── main.py
├── requirements.txt
├── .env.example
└── .gitignore
```

## Install

Use Python 3.10 or newer. From the project root, create and activate a virtual environment.

**macOS/Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

**Windows PowerShell**

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

No secret is needed with Open-Meteo. `.env.example` is a safe template for future providers that require credentials. Never commit `.env`, tokens, or private credentials.

## Run

### Offline simulation CLI

```bash
python main.py
python main.py --mode simulation --scenario thunderstorm
```

Scenarios: `normal`, `high_temperature`, `heavy_rain`, `high_humidity`, `strong_wind`, `thunderstorm`.

### Live CLI

```bash
python main.py --mode live --city "Mumbai"
```

Live mode requires internet access. A city is first resolved to coordinates by Open-Meteo Geocoding, then the forecast endpoint supplies current, hourly, and daily values.

### Start FastAPI

In terminal 1:

```bash
uvicorn src.api:app --reload
```

The API is at `http://127.0.0.1:8000`; Swagger UI is at `http://127.0.0.1:8000/docs`.

### Start the Streamlit dashboard

In terminal 2, from the same project root and with the environment activated:

```bash
streamlit run src/dashboard.py
```

Open `http://localhost:8501`. The dashboard calls the FastAPI service at `http://127.0.0.1:8000`. To use another backend address, set `WEATHER_API_URL` before starting Streamlit. Use the sidebar to choose a city, source, simulation scenario, and thresholds; click **Refresh weather** to submit the request. The dashboard provides overview, five-day forecast, and alert pages, interactive temperature/rain/wind charts, a location map, and report downloads.

## API reference

| Method and path | Purpose |
|---|---|
| `GET /` | Service name and route hints |
| `GET /health` | Health status |
| `GET /weather?city=London&mode=live` | Weather, alerts, forecast, report metadata |

`/weather` also accepts `mode=simulation`, `scenario=normal|high_temperature|heavy_rain|high_humidity|strong_wind|thunderstorm`, and thresholds `heat_c`, `humidity_percent`, `rain_probability_percent`, `wind_kmh`. Invalid parameters return `422`; unknown live city returns `404`; provider/network errors return `502`.

Example:

```bash
curl "http://127.0.0.1:8000/weather?mode=simulation&scenario=heavy_rain"
```

## Alert rules

Default thresholds: temperature `35 °C`, relative humidity `85%`, hourly rain probability `70%`, and wind `50 km/h`. Each rule creates at most one alert for the forecast and marks it `warning` or `critical` based on how far it crosses the threshold. WMO thunderstorm weather codes `95`, `96`, and `99` produce a critical alert. Missing values are skipped. Set thresholds in the dashboard sidebar or API query. Tune them for demonstration only; they are not official hazard criteria.

## Reports and sample outputs

Every service request writes a uniquely named CSV and JSON file under `outputs/`. JSON includes city/country, location, mode/source, generation time, current conditions, five-day and hourly forecasts, thresholds, and alerts. CSV contains one row per hourly forecast with location fields. The dashboard also provides download buttons for the current result. The normal simulation is calm; choose an alert scenario to see corresponding messages.

## Data attribution

Live data is provided by [Open-Meteo](https://open-meteo.com/). This project attributes the provider in its response and dashboard. Review [Open-Meteo's terms](https://open-meteo.com/en/terms) before public or commercial deployment. Simulation values are synthetic and are clearly labeled.

## Tests

Run the offline service/API test suite:

```bash
python -m unittest discover -s tests -v
```

Coverage includes all simulation scenarios, missing-value behavior, report generation, root/health/weather routes, invalid mode validation, and unknown-city handling. Live requests need internet and are not required for the offline test suite.

## Screenshots

Save genuine application captures in `images/screenshots/`: dashboard overview, current weather and alerts, five-day view and charts, simulation scenario, and FastAPI `/docs`. Do not represent mockups as running software or include private credentials/account details.

## GitHub submission

Recommended repository: `weather-forecast-alert-application`  
Description: `Python weather dashboard with Open-Meteo, FastAPI, configurable alerts, and offline simulation.`  
Topics: `python`, `weather-api`, `fastapi`, `streamlit`, `plotly`, `data-visualization`.

```bash
git init
git add README.md .gitignore .env.example requirements.txt main.py src data tests docs images
git status
git commit -m "Build weather forecast and alert dashboard"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/weather-forecast-alert-application.git
git push -u origin main
```

Generated reports, `.env`, `.venv`, bytecode, and local IDE files are excluded by `.gitignore`. Add selected screenshots to `images/screenshots/` before committing.

## Future improvements

Add unit-aware local alert profiles, optional air-quality integration, persistent history, caching, scheduled refresh, deployed hosting, and tested opt-in notifications.

## Learning outcomes

This project demonstrates HTTP API integration, geocoding, JSON normalization, error handling, Python service design, configurable analysis, FastAPI route validation, Streamlit-to-API communication, Plotly charts, report generation, offline simulation, testing, and GitHub documentation.

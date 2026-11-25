"""FastAPI HTTP interface for the shared weather and alert service."""
from fastapi import FastAPI, HTTPException, Query
from src.weather_app import get_report

app = FastAPI(
    title="Weather Forecast & Alert API", version="2.0.0",
    description="Five-day Open-Meteo forecasts, simulated scenarios, and configurable threshold alerts.",
)


@app.get("/", tags=["info"])
def home():
    return {"name": "Weather Forecast & Alert API", "status": "ready", "docs": "/docs",
            "weather_endpoint": "/weather?city=London&mode=simulation"}


@app.get("/health", tags=["info"])
def health():
    return {"status": "ok"}


@app.get("/weather", tags=["weather"])
def weather(
    city: str = Query("London", min_length=1, max_length=100),
    mode: str = Query("simulation", pattern="^(simulation|live)$"),
    scenario: str = Query("normal", pattern="^(normal|high_temperature|heavy_rain|high_humidity|strong_wind|thunderstorm)$"),
    heat_c: float = Query(35, gt=-80, lt=70),
    humidity_percent: float = Query(85, gt=0, le=100),
    rain_probability_percent: float = Query(70, gt=0, le=100),
    wind_kmh: float = Query(50, gt=0, le=500),
):
    try:
        return get_report(city, mode, scenario, {
            "temperature_c": heat_c, "humidity_percent": humidity_percent,
            "rain_probability_percent": rain_probability_percent, "wind_kmh": wind_kmh,
        })
    except ValueError as exc:
        status = 404 if "No location found" in str(exc) else 422
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    except (RuntimeError, KeyError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

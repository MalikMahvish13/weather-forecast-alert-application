"""Shared weather provider, normalization, alert, and report services."""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:  # simulation and report generation can run without network dependencies
    requests = None  # type: ignore[assignment]

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_FILE = ROOT / "data" / "sample_weather.json"
OUTPUT_DIR = ROOT / "outputs"
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
SCENARIOS = ("normal", "high_temperature", "heavy_rain", "high_humidity", "strong_wind", "thunderstorm")
DEFAULT_THRESHOLDS: dict[str, float] = {
    "temperature_c": 35.0, "humidity_percent": 85.0,
    "rain_probability_percent": 70.0, "wind_kmh": 50.0,
}
WEATHER_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog", 51: "Light drizzle", 53: "Moderate drizzle",
    55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 80: "Rain showers",
    81: "Moderate rain showers", 82: "Violent rain showers", 95: "Thunderstorm",
    96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail",
}


def weather_description(code: Any) -> str:
    try:
        return WEATHER_CODES.get(int(code), "Conditions unavailable")
    except (TypeError, ValueError):
        return "Conditions unavailable"


def _number(value: Any) -> float | None:
    """Convert finite numeric values while treating missing and invalid data safely."""
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def load_sample(scenario: str = "normal") -> dict[str, Any]:
    """Load the checked-in offline sample and apply one deterministic test scenario."""
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown simulation scenario '{scenario}'. Choose from: {', '.join(SCENARIOS)}")
    with SAMPLE_FILE.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    payload["scenario"] = scenario
    if scenario == "normal":
        return payload
    current = payload["current"]
    row = payload["hourly"][0]
    if scenario == "high_temperature":
        current["temperature_c"] = row["temperature_c"] = 39.0
        current["feels_like_c"] = row["feels_like_c"] = 41.0
        payload["daily"][0]["temperature_max_c"] = 39.0
        payload["daily"][0]["feels_like_max_c"] = 41.0
    elif scenario == "heavy_rain":
        current["precipitation_probability_percent"] = 92
        row["precipitation_probability_percent"] = 92
        current["precipitation_mm"] = row["precipitation_mm"] = 9.0
        payload["daily"][0]["precipitation_probability_max_percent"] = 92
        payload["daily"][0]["precipitation_sum_mm"] = 9.0
    elif scenario == "high_humidity":
        current["humidity_percent"] = row["humidity_percent"] = 94
    elif scenario == "strong_wind":
        current["wind_kmh"] = row["wind_kmh"] = 72.0
        payload["daily"][0]["wind_max_kmh"] = 72.0
    elif scenario == "thunderstorm":
        current["weather_code"] = row["weather_code"] = 95
        current["condition"] = "Thunderstorm"
        row["condition"] = "Thunderstorm"
        current["precipitation_probability_percent"] = 88
        row["precipitation_probability_percent"] = 88
        payload["daily"][0]["weather_code"] = 95
        payload["daily"][0]["precipitation_probability_max_percent"] = 88
    return payload


def fetch_live(city: str) -> dict[str, Any]:
    """Geocode a city and request current plus five-day weather from Open-Meteo."""
    city = city.strip()
    if not city:
        raise ValueError("Enter a city name.")
    if requests is None:
        raise RuntimeError("Live mode requires the 'requests' package. Install project dependencies with `uv pip install -r requirements.txt`.")
    try:
        place = requests.get(GEOCODING_URL, params={"name": city, "count": 1, "language": "en", "format": "json"}, timeout=12)
        place.raise_for_status()
        results = place.json().get("results") or []
        if not results:
            raise ValueError(f"No location found for '{city}'. Check the spelling and try again.")
        location = results[0]
        params = {
            "latitude": location["latitude"], "longitude": location["longitude"],
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
            "hourly": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,precipitation_probability,wind_speed_10m,weather_code",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,apparent_temperature_max,precipitation_probability_max,precipitation_sum,wind_speed_10m_max",
            "forecast_days": 5, "timezone": "auto",
        }
        response = requests.get(FORECAST_URL, params=params, timeout=20)
        response.raise_for_status()
        payload = response.json()
        payload["location"] = {
            "name": location.get("name", city), "country": location.get("country", ""),
            "latitude": location.get("latitude"), "longitude": location.get("longitude"),
            "timezone": payload.get("timezone", ""),
        }
        payload["source"] = "Open-Meteo live forecast"
        return payload
    except requests.Timeout as exc:
        raise RuntimeError("The weather service timed out. Please try again.") from exc
    except requests.RequestException as exc:
        raise RuntimeError(f"Could not reach the weather service: {exc}") from exc
    except (ValueError, KeyError) as exc:
        if isinstance(exc, ValueError) and str(exc).startswith("No location found"):
            raise
        raise RuntimeError(f"The weather service returned an invalid response: {exc}") from exc


def normalize(payload: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Map live Open-Meteo or sample JSON into safe, stable application records."""
    is_simulation = payload.get("source") == "simulation"
    if is_simulation:
        current_raw = payload.get("current") or {}
        hourly_raw = payload.get("hourly") or []
        daily_raw = payload.get("daily") or []
        location = payload.get("location", {})
        current = {
            "time": current_raw.get("time"), "temperature_c": _number(current_raw.get("temperature_c")),
            "feels_like_c": _number(current_raw.get("feels_like_c", current_raw.get("temperature_c"))),
            "humidity_percent": _number(current_raw.get("humidity_percent")),
            "precipitation_mm": _number(current_raw.get("precipitation_mm")),
            "precipitation_probability_percent": _number(current_raw.get("precipitation_probability_percent")),
            "wind_kmh": _number(current_raw.get("wind_kmh")), "weather_code": current_raw.get("weather_code"),
        }
        hours = [{
            "time": r.get("time"), "temperature_c": _number(r.get("temperature_c")),
            "feels_like_c": _number(r.get("feels_like_c", r.get("temperature_c"))),
            "humidity_percent": _number(r.get("humidity_percent")), "precipitation_mm": _number(r.get("precipitation_mm")),
            "precipitation_probability_percent": _number(r.get("precipitation_probability_percent")),
            "wind_kmh": _number(r.get("wind_kmh")), "weather_code": r.get("weather_code"),
        } for r in hourly_raw]
        days = daily_raw
    else:
        current_raw = payload.get("current") or {}
        hourly_raw = payload.get("hourly") or {}
        current = {
            "time": current_raw.get("time"), "temperature_c": _number(current_raw.get("temperature_2m")),
            "feels_like_c": _number(current_raw.get("apparent_temperature")),
            "humidity_percent": _number(current_raw.get("relative_humidity_2m")),
            "precipitation_mm": _number(current_raw.get("precipitation")),
            "precipitation_probability_percent": None,
            "wind_kmh": _number(current_raw.get("wind_speed_10m")), "weather_code": current_raw.get("weather_code"),
        }
        hour_keys = {
            "time": "time", "temperature_c": "temperature_2m", "feels_like_c": "apparent_temperature",
            "humidity_percent": "relative_humidity_2m", "precipitation_mm": "precipitation",
            "precipitation_probability_percent": "precipitation_probability", "wind_kmh": "wind_speed_10m",
            "weather_code": "weather_code",
        }
        times = hourly_raw.get("time") or []
        hours = []
        for i, timestamp in enumerate(times):
            row: dict[str, Any] = {"time": timestamp}
            for key, api_key in hour_keys.items():
                if key == "time":
                    continue
                values = hourly_raw.get(api_key) or []
                row[key] = _number(values[i]) if i < len(values) else None
            hours.append(row)
        daily_raw = payload.get("daily") or {}
        days = []
        for i, date in enumerate(daily_raw.get("time") or []):
            def daily_value(key: str) -> float | None:
                vals = daily_raw.get(key) or []
                return _number(vals[i]) if i < len(vals) else None
            days.append({
                "date": date, "weather_code": daily_value("weather_code"),
                "temperature_max_c": daily_value("temperature_2m_max"), "temperature_min_c": daily_value("temperature_2m_min"),
                "feels_like_max_c": daily_value("apparent_temperature_max"),
                "precipitation_probability_max_percent": daily_value("precipitation_probability_max"),
                "precipitation_sum_mm": daily_value("precipitation_sum"), "wind_max_kmh": daily_value("wind_speed_10m_max"),
            })
        location = payload.get("location", {})
    return current, hours, days, location


def make_alerts(current: dict[str, Any], hours: list[dict[str, Any]], days: list[dict[str, Any]] | None = None,
                thresholds: dict[str, float] | None = None) -> list[dict[str, str]]:
    """Create one alert per condition, with severity and missing-value-safe checks."""
    limits = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    series = [current, *hours]
    alerts: list[dict[str, str]] = []

    def maximum(key: str) -> float | None:
        values = [_number(row.get(key)) for row in series]
        valid = [v for v in values if v is not None]
        return max(valid) if valid else None

    checks = [
        ("high_temperature", "Temperature", "temperature_c", limits["temperature_c"], "°C", "High temperature detected"),
        ("high_humidity", "Humidity", "humidity_percent", limits["humidity_percent"], "%", "High humidity detected"),
        ("high_rain_probability", "Rain probability", "precipitation_probability_percent", limits["rain_probability_percent"], "%", "High chance of rain"),
        ("high_wind", "Wind speed", "wind_kmh", limits["wind_kmh"], "km/h", "Strong winds forecast"),
    ]
    for code, label, key, threshold, unit, message in checks:
        value = maximum(key)
        if value is not None and value >= threshold:
            severity = "critical" if value >= threshold * 1.25 else "warning"
            alerts.append({"code": code, "severity": severity, "title": message,
                           "message": f"{label} may reach {value:g}{unit} (alert threshold: {threshold:g}{unit})."})
    storm = any(str(row.get("weather_code")) in {"95", "96", "99"} for row in series)
    storm = storm or any(str(day.get("weather_code")) in {"95", "96", "99"} for day in (days or []))
    if storm:
        alerts.append({"code": "thunderstorm", "severity": "critical", "title": "Thunderstorm possible",
                       "message": "Thunderstorm conditions appear in the forecast. Check local official guidance."})
    return alerts


def _safe_name(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", value.strip()).strip("_").lower() or "weather"


def save_report(report: dict[str, Any]) -> tuple[Path, Path]:
    """Write unique JSON and flattened hourly CSV reports for dashboard downloads."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    prefix = f"{_safe_name(report['city'])}_{stamp}"
    csv_path, json_path = OUTPUT_DIR / f"{prefix}.csv", OUTPUT_DIR / f"{prefix}.json"
    csv_fields = ["city", "country", "mode", "source", "report_generated_at_utc", "weather_time",
                  "current_temperature_c", "current_feels_like_c", "current_humidity_percent",
                  "current_precipitation_mm", "current_rain_probability_percent", "current_wind_kmh",
                  "current_condition", "alerts", "date", "time", "temperature_c", "feels_like_c",
                  "humidity_percent", "precipitation_mm", "precipitation_probability_percent",
                  "wind_kmh", "weather_code", "condition"]
    current = report["current"]
    common = {
        "city": report["city"], "country": report["country"], "mode": report["mode"],
        "source": report["source"], "report_generated_at_utc": report["generated_at_utc"],
        "weather_time": current.get("time"), "current_temperature_c": current.get("temperature_c"),
        "current_feels_like_c": current.get("feels_like_c"), "current_humidity_percent": current.get("humidity_percent"),
        "current_precipitation_mm": current.get("precipitation_mm"),
        "current_rain_probability_percent": current.get("precipitation_probability_percent"),
        "current_wind_kmh": current.get("wind_kmh"), "current_condition": current.get("condition"),
        "alerts": json.dumps(report["alerts"], ensure_ascii=False),
    }
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields)
        writer.writeheader()
        for row in report["forecast_hours"]:
            writer.writerow({**common, "date": (row.get("time") or "")[:10], **row})
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return csv_path, json_path


def get_report(city: str = "London", mode: str = "simulation", scenario: str = "normal",
               thresholds: dict[str, float] | None = None) -> dict[str, Any]:
    """Fetch/normalize weather, evaluate alerts, and save a report snapshot."""
    if mode == "simulation":
        payload = load_sample(scenario)
        city = payload.get("location", {}).get("name", "Sample City")
    elif mode == "live":
        payload = fetch_live(city)
    else:
        raise ValueError("mode must be 'simulation' or 'live'")
    current, hours, days, location = normalize(payload)
    current["condition"] = weather_description(current.get("weather_code"))
    for row in hours:
        row["condition"] = weather_description(row.get("weather_code"))
    for day in days:
        day["condition"] = weather_description(day.get("weather_code"))
    # A five-day daily summary is derived from hourly values when sample data lacks daily rows.
    if not days and hours:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in hours:
            grouped.setdefault((row.get("time") or "")[:10], []).append(row)
        for date, rows in grouped.items():
            temps = [r["temperature_c"] for r in rows if r["temperature_c"] is not None]
            feels = [r["feels_like_c"] for r in rows if r["feels_like_c"] is not None]
            probs = [r["precipitation_probability_percent"] for r in rows if r["precipitation_probability_percent"] is not None]
            winds = [r["wind_kmh"] for r in rows if r["wind_kmh"] is not None]
            days.append({"date": date, "temperature_max_c": max(temps) if temps else None,
                         "temperature_min_c": min(temps) if temps else None,
                         "feels_like_max_c": max(feels) if feels else None,
                         "precipitation_probability_max_percent": max(probs) if probs else None,
                         "precipitation_sum_mm": sum((r["precipitation_mm"] or 0) for r in rows),
                         "wind_max_kmh": max(winds) if winds else None,
                         "weather_code": next((r["weather_code"] for r in rows if r["weather_code"] is not None), None)})
    if len(days) > 5:
        days = days[:5]
    alerts = make_alerts(current, hours, days, thresholds)
    report = {
        "city": location.get("name", city) if isinstance(location, dict) else str(location),
        "country": location.get("country", "") if isinstance(location, dict) else "",
        "location": location if isinstance(location, dict) else {"name": str(location)},
        "mode": mode, "source": payload.get("source", "Open-Meteo live forecast"),
        "scenario": scenario if mode == "simulation" else None,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "current": current, "forecast_days": days, "forecast_hours": hours,
        "alerts": alerts, "thresholds": {**DEFAULT_THRESHOLDS, **(thresholds or {})},
        "attribution": "Weather data by Open-Meteo.com" if mode == "live" else "Synthetic demonstration data",
    }
    csv_path, json_path = save_report(report)
    report["csv_report"] = str(csv_path.relative_to(ROOT))
    report["json_report"] = str(json_path.relative_to(ROOT))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Weather forecast and threshold alert demo")
    parser.add_argument("--mode", choices=["simulation", "live"], default="simulation")
    parser.add_argument("--city", default="London")
    parser.add_argument("--scenario", choices=SCENARIOS, default="normal")
    args = parser.parse_args()
    try:
        report = get_report(args.city, args.mode, args.scenario)
    except (RuntimeError, ValueError, KeyError) as exc:
        parser.error(str(exc))
    current = report["current"]
    print(f"\nWeather Forecast & Alert Application — {report['city']}, {report['country']} [{report['mode']}]")
    print(f"Now: {current['temperature_c']}°C | feels like {current['feels_like_c']}°C | humidity {current['humidity_percent']}% | wind {current['wind_kmh']} km/h")
    print("\nAlerts:")
    for alert in report["alerts"]:
        print(f"  [{alert['severity'].upper()}] {alert['title']}: {alert['message']}")
    if not report["alerts"]:
        print("  No threshold alerts.")
    print(f"\nReports: {report['csv_report']} and {report['json_report']}")


if __name__ == "__main__":
    main()

import asyncio
import unittest
import json
from unittest.mock import patch
from pathlib import Path

import httpx

from src.api import app
from src.weather_app import SCENARIOS, get_report, make_alerts


class WeatherServiceTests(unittest.TestCase):
    def test_all_simulation_scenarios_are_offline_and_five_day(self):
        expected = {
            "normal": set(), "high_temperature": {"high_temperature"},
            "heavy_rain": {"high_rain_probability"}, "high_humidity": {"high_humidity"},
            "strong_wind": {"high_wind"}, "thunderstorm": {"high_rain_probability", "thunderstorm"},
        }
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario):
                report = get_report(mode="simulation", scenario=scenario)
                codes = {alert["code"] for alert in report["alerts"]}
                self.assertTrue(expected[scenario].issubset(codes))
                self.assertEqual(report["mode"], "simulation")
                self.assertEqual(len(report["forecast_days"]), 5)
                self.assertTrue(report["csv_report"].endswith(".csv"))
                self.assertTrue(report["json_report"].endswith(".json"))
                self.assertTrue((Path(__file__).resolve().parents[1] / report["csv_report"]).is_file())
                saved = json.loads((Path(__file__).resolve().parents[1] / report["json_report"]).read_text())
                self.assertIn("alerts", saved)
                self.assertIn("generated_at_utc", saved)

    def test_missing_values_do_not_create_false_alerts_or_crash(self):
        self.assertEqual(make_alerts({}, [{"temperature_c": None, "humidity_percent": None,
                                          "precipitation_probability_percent": None, "wind_kmh": None,
                                          "weather_code": None}]), [])


class WeatherApiTests(unittest.TestCase):
    def setUp(self):
        self.transport = httpx.ASGITransport(app=app)

    def request(self, path):
        async def make_request():
            async with httpx.AsyncClient(transport=self.transport, base_url="http://test") as client:
                return await client.get(path)
        return asyncio.run(make_request())

    def test_root_health_and_simulation_weather(self):
        self.assertEqual(self.request("/").status_code, 200)
        self.assertEqual(self.request("/health").json()["status"], "ok")
        result = self.request("/weather?mode=simulation&scenario=thunderstorm")
        self.assertEqual(result.status_code, 200)
        self.assertIn("thunderstorm", {item["code"] for item in result.json()["alerts"]})

    def test_invalid_mode_is_rejected(self):
        self.assertEqual(self.request("/weather?mode=other").status_code, 422)

    @patch("src.weather_app.requests.get")
    def test_live_city_not_found_is_404(self, mock_get):
        mock_get.return_value.json.return_value = {"results": []}
        mock_get.return_value.raise_for_status.return_value = None
        response = self.request("/weather?mode=live&city=NoSuchCityName")
        self.assertEqual(response.status_code, 404)

    @patch("src.weather_app.requests.get", side_effect=__import__("requests").ConnectionError("offline"))
    def test_live_service_failure_is_502(self, _mock_get):
        response = self.request("/weather?mode=live&city=London")
        self.assertEqual(response.status_code, 502)


if __name__ == "__main__":
    unittest.main()

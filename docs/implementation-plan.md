# Implementation plan

| Phase | Work and reason | Expected output | Common beginner mistake |
|---|---|---|---|
| 1. Setup | Install Python 3.10+ and Git; check versions | Working terminal | Using a different interpreter than the IDE |
| 2. Folders | Keep data, source, output, docs separate | Clear project tree | Running commands from the wrong folder |
| 3. API setup | Open-Meteo is keyless; optional providers need private local secrets | No-key live source or simulation | Committing `.env` or putting keys in code |
| 4. Fetch | Geocode a city then request forecast JSON | API payload | Not using timeouts or checking HTTP errors |
| 5. Parse | Map JSON fields into `WeatherHour` records | Consistent data | Treating a list of hourly values as a single value |
| 6. Analyze | Review next 72 hourly samples | Forecast summary | Assuming all providers use the same units |
| 7. Alerts | Compare values with editable thresholds | Rain/heat/humidity/wind notices | Treating demo thresholds as official warnings |
| 8. Visualize | Plot temperature with Matplotlib / Streamlit | PNG or dashboard plot | Charting timestamps in the wrong local timezone |
| 9. Report | Save CSV plus JSON snapshot | Reproducible report | Overwriting results or including credentials |
| 10. GitHub | Commit code, docs, sample and safe screenshots | Portfolio repository | Uploading `.env`, personal data, or generated clutter |

## Data flow

`City + thresholds → Streamlit HTTP client → FastAPI → sample JSON or Open-Meteo geocoding/forecast → normalized current/hourly/five-day records → severity alert rules → JSON/CSV reports + dashboard charts`

The command-line entry point calls the same service directly for quick offline or live demonstrations.

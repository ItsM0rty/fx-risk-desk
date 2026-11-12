# FX Risk Desk

A local research desk for comparing hedge policies on a hypothetical EUR and JPY book. It reports daily P&L net of a stated hedge cost, rolling historical VaR and expected shortfall, statistical backtests, walk-forward EUR/USD quantiles, and a European FX option scenario. A separate USD/NPR panel illustrates a payout for a US to Nepal remittance operator.

## Browser demo

[Open the live demo](https://www.suyashbhattarai.com.np/demo-fx-risk-desk) · [Read the case study](https://www.suyashbhattarai.com.np/work-fx-risk-desk)

The portfolio demo serves a saved run with derived P&L, backtests and forecasts. Its option controls select from 72 scenarios computed by the Python pricer. The full React dashboard and FastAPI service accept custom option inputs locally. To rebuild the browser data after generating a local run, use the command below and serve the output alongside the files in portfolio-demo.

```powershell
.venv/Scripts/python.exe -m riskdesk.export_demo --output .cache/portfolio-demo/run.json
```


## Run it on Windows

Use PowerShell 7, Python 3.13, Git and Node 22. Run these commands from the project root.

```powershell
pwsh -File scripts/setup-python.ps1
pwsh -File scripts/fetch-public.ps1
.venv/Scripts/python.exe -m riskdesk.run
npm ci
npm run build
.venv/Scripts/python.exe -m uvicorn riskdesk.api:app --host 127.0.0.1 --port 8000
```

Open [the desk](http://127.0.0.1:8000/) or [the API docs](http://127.0.0.1:8000/docs). For frontend development, run `npm run dev` in a second terminal while the API is running. The Vite proxy routes API requests to port 8000.

The fetch script caches the ECB ZIP and the paginated NRB USD quotes under `data/raw`. The risk command writes an atomic snapshot to `data/runs/latest.json`. Both source hashes are included in the run. An existing snapshot is reused until you regenerate it. Use `--raw` and `--output` on the risk command to keep separate runs. Set `FX_RISK_RUN` to serve a different snapshot.

## Model conventions

- The book holds +EUR 1m and −JPY 90m. ECB rates supply USD per EUR and USD per JPY. The latter is derived by dividing the two EUR-based rates. Reference marks are modeled as available at 17:00 Europe/Berlin on the observation day. The next day in the model means the next available ECB observation.
- The desk compares five hedge ratios on the EUR leg. The hedge offsets the selected fraction of the EUR spot P&L and charges 0.15 bps per observation on the prior covered USD notional. The JPY leg remains open. This is a daily offset proxy with zero carry and basis.
- Each daily 99% VaR/ES forecast uses the preceding 250 daily P&Ls of the same policy. Profit is positive. A breach occurs when the day’s loss exceeds the forecast VaR. The coverage tests score the hypothetical book and display p-values with observed breach counts.
- The XGBoost model uses lagged EUR and JPY return features known at the close of the forecast origin. The training set expands each year and ends before that year's first target. The baseline uses the preceding 250 observed EUR/USD returns. The 2025 holdout is reported separately, and raw crossings are counted before sorting predictions for evaluation.
- The Garman–Kohlhagen option scenario uses hypothetical USD/EUR rates and flat volatility. Scenario shocks reprice the same option at fixed expiry. Its Greeks and premiums use the stated quote currency and notional.
- The NRB panel preserves both sides of the reference quote. A hypothetical operator selling USD to fund an NPR payout uses the bank’s USD buy rate. The midpoint is included for comparison.
- Historical FX order-book replay is pending public order-level data. The dashboard covers daily reference-rate risk.

## Contract and verification

```powershell
.venv/Scripts/python.exe -m pytest -q --basetemp .cache/pytest
.venv/Scripts/python.exe -m riskdesk.export_schema --check
npm run check:schema
npm run build
.venv/Scripts/python.exe -m scripts.check_client_package
```

After an intentional API schema change, run `.venv/Scripts/python.exe -m riskdesk.export_schema` and `npm run generate -w @itsm0rty/fx-risk-desk-client`. The client exports typed methods generated from the checked-in schema and uses openapi-fetch for HTTP. Install the client with `npm install @itsm0rty/fx-risk-desk-client`.

[ECB reference rates](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html) · [Nepal Rastra Bank FX API](https://www.nrb.org.np/api-docs-v1/)

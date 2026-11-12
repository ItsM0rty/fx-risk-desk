# FX Risk Desk client

An ESM TypeScript client for the local FX Risk Desk API.

```sh
npm install @itsm0rty/fx-risk-desk-client
```

```ts
import { createRiskDeskClient } from "@itsm0rty/fx-risk-desk-client";

const client = createRiskDeskClient("http://127.0.0.1:8000");
const { data, error } = await client.GET("/api/v1/runs/latest/risk", {
  params: { query: { hedge_pct: "75", limit: 252 } },
});
```

The API must have a locally generated risk run. The package carries the typed HTTP client and its generated declarations.

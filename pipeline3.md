# Security & Weather Architecture Documentation (`pipeline3.md`)

This document details the security layers implemented inside the `FastAPI/security` folder and describes how the weather forecasting integration operates in both the Logistics and Courier dashboards.

---

## 🔒 1. Security Folder Features & Usage

The application features a dedicated security context module located in the [security](file:///c:/Users/GauryJithesh/Desktop/aarushi/IntelliSupply/FastAPI/security) folder. Here is how each module works and where it is applied:

### A. Rate Limiting (`rate_limit.py`)
- **What it does**: Exposes an in-memory, thread-safe request rate limiter (`InMemoryRateLimiter`) mapped by the client's IP address. It throws a `429 Too Many Requests` HTTP error if the threshold is exceeded.
- **Where it is used**:
  - [voice.py](file:///c:/Users/GauryJithesh/Desktop/aarushi/IntelliSupply/FastAPI/routers/voice.py#L39): Restricts voice recording processing to `10 requests per 60 seconds`.
  - [copilot.py](file:///c:/Users/GauryJithesh/Desktop/aarushi/IntelliSupply/FastAPI/routers/copilot.py#L45): Restricts LLM Copilot queries to `20 requests per 60 seconds`.
  - [copilot.py](file:///c:/Users/GauryJithesh/Desktop/aarushi/IntelliSupply/FastAPI/routers/copilot.py#L74): Restricts debug agent requests to `20 requests per 60 seconds`.
  - [auth.py](file:///c:/Users/GauryJithesh/Desktop/aarushi/IntelliSupply/FastAPI/routers/auth.py#L126): Restricts email-password login submissions to `5 requests per 60 seconds`.
  - [auth.py](file:///c:/Users/GauryJithesh/Desktop/aarushi/IntelliSupply/FastAPI/routers/auth.py#L147): Restricts user profile registrations to `5 requests per 60 seconds`.
  - [auth.py](file:///c:/Users/GauryJithesh/Desktop/aarushi/IntelliSupply/FastAPI/routers/auth.py#L191): Restricts Google OAuth logins to `5 requests per 60 seconds`.

### B. Prompt Injection Prevention (`injection.py`)
- **What it does**: Uses regex checks (`check_prompt_injection`) to identify prompt injection bypass vectors (e.g. *"ignore all previous instructions"*, *"system override"*) and dangerous stacked query database commands (e.g. `; DROP`, `UNION SELECT`, `OR 1=1`).
- **Where it is used**:
  - [copilot.py](file:///c:/Users/GauryJithesh/Desktop/aarushi/IntelliSupply/FastAPI/routers/copilot.py#L61): Rejects query processing in `/orders/copilot/query` if a threat is flagged.
  - [copilot.py](file:///c:/Users/GauryJithesh/Desktop/aarushi/IntelliSupply/FastAPI/routers/copilot.py#L90): Rejects query processing in `/orders/copilot/debug` if a threat is flagged.

### C. PII Masking (`pii.py`)
- **What it does**: Scans textual inputs using regex to identify and strip common Personally Identifiable Information (PII) including emails, phone numbers, credit card numbers, and Social Security Numbers (SSN), replacing them with generic tags (e.g. `[MASKED_EMAIL]`).
- **Where it is used**:
  - [logging.py](file:///c:/Users/GauryJithesh/Desktop/aarushi/IntelliSupply/FastAPI/security/logging.py#L2): Referenced to mask logging context items.
  - [copilot.py](file:///c:/Users/GauryJithesh/Desktop/aarushi/IntelliSupply/FastAPI/routers/copilot.py#L52): Automatically sanitizes chatbot messages to prevent leakage of client details to external AI providers.
  - [copilot.py](file:///c:/Users/GauryJithesh/Desktop/aarushi/IntelliSupply/FastAPI/routers/copilot.py#L81): Sanitizes debug agent messages.

### D. Secure Audit Logging (`logging.py`)
- **What it does**: Defines a custom logging filter (`PIIMaskingFilter`) which catches all logging events and passes their text and message arguments through `mask_pii()`. This prevents sensitive coordinates, phone numbers, or emails from leaking into server terminal logs.
- **Where it is used**:
  - [main.py](file:///c:/Users/GauryJithesh/Desktop/aarushi/IntelliSupply/FastAPI/main.py#L20): Registers `setup_secure_logging()` on app initialization to secure the root system logger.

### E. LLM Input Payload Validation (`validation.py`)
- **What it does**: Enforces length constraints (minimum 1, maximum 5000 characters) on prompt inputs via Pydantic model validation (`LLMInputPayload`) to mitigate resource exhaustion or denial-of-service threats.
- **Where it is used**:
  - [copilot.py](file:///c:/Users/GauryJithesh/Desktop/aarushi/IntelliSupply/FastAPI/routers/copilot.py#L56): Validates inputs in `/orders/copilot/query`.
  - [copilot.py](file:///c:/Users/GauryJithesh/Desktop/aarushi/IntelliSupply/FastAPI/routers/copilot.py#L85): Validates inputs in `/orders/copilot/debug`.

---

## ⛅ 2. Weather Forecasting Integration

### API Service Provider
The dashboards call the public **Open-Meteo Forecast API** directly:
- **API URL**: `https://api.open-meteo.com/v1/forecast`
- **Query Parameters**:
  - `latitude` & `longitude`: Geolocation coordinates of the hub or stop.
  - `current`: Requests actual temperature (`temperature_2m`), apparent temperature (`apparent_temperature`), relative humidity, WMO weather code, and wind speed.
  - `hourly`: Requests temperature projections and rain probability over time (`precipitation_probability`).
  - `daily`: Requests daily minimum and maximum temperatures.
  - `timezone`: Set to `auto` to resolve correct local times.

### Code Mechanics & Features (Frontend)

#### Coordinate Resolution (Single Lat/Lng on Routes vs. Individual Stops)
Depending on which dashboard is open, the weather forecasting interface retrieves coordinates using different granularities:
1. **Logistics Dashboard ([Home.tsx](file:///c:/Users/GauryJithesh/Desktop/aarushi/IntelliSupply/frontend/app/src/pages/Home.tsx))**:
   - The weather panel presents a representative forecast for the overall route's area.
   - When a courier's route (`routeResult`) is loaded, it fetches weather using a **single coordinate pair** (latitude/longitude):
     - **Primary source**: The courier's starting hub coordinate (`routeResult.courier_start.lat` and `.lng`).
     - **Fallback source**: If no start coordinate is specified, it uses the coordinates of the first stop in the sequence (`stops[0].from_lat` / `.lat_wgs84` and `stops[0].from_lng` / `.lon_wgs84`).
     - **Secondary Fallback**: If no route is loaded, it defaults to the coordinates of the first operational hub (`hubLocations[0]`).
2. **Courier Dashboard ([Courier.tsx](file:///c:/Users/GauryJithesh/Desktop/aarushi/IntelliSupply/frontend/app/src/pages/Courier.tsx))**:
   - The courier views weather on a **per-shipment/stop basis**.
   - When a specific stop is highlighted (`highlightedOrderId`), the dashboard retrieves the exact latitude and longitude of that stop (`chosenStop.lat_wgs84`, `chosenStop.lon_wgs84`) and makes a target weather query.
   - This ensures the courier gets real-time weather alerts and comfort stats specific to their next immediate delivery point, rather than a generic city or route-wide forecast.

- **Automatic Coordination Hooks**: In [Home.tsx](file:///c:/Users/GauryJithesh/Desktop/aarushi/IntelliSupply/frontend/app/src/pages/Home.tsx) and [Courier.tsx](file:///c:/Users/GauryJithesh/Desktop/aarushi/IntelliSupply/frontend/app/src/pages/Courier.tsx), an effect hook watches coordinate changes. When a courier route or hub map location is selected, the application queries Open-Meteo for coordinates.
- **Simplified Metrics View**: Shows actual temperatures, comfort level descriptions, conditions, high/low ranges, and the hourly scrollable list. Apparent temperature details cards and key legends are hidden to declutter dashboard workspaces.
- **12-Hour Rain Probability Sparkline**:
  - Scaled viewport: Width set to `240%` to display exactly 5 columns at a time, making elements legible and horizontal scrolling natural.
  - SVG graphic: An inline `<svg viewBox="0 0 1200 32" preserveAspectRatio="none">` plots coordinates dynamically calculated as `y = 28 - (rainChance / 100) * 24` at `i * 100 + 50` horizontal steps. It renders a high-contrast blue polyline with filled path gradients and circular nodes.
- **Condition Emoji Config**: Resolves WMO codes to matching native emojis:
  - `0`: Clear / Sunny ☀️
  - `1-3`: Partly Cloudy 🌤️
  - `45-48`: Foggy / Hazy 🌫️
  - `51-67, 80-82`: Rainy 🌧️
  - `71-77, 85-86`: Snowy 🌨️
  - `95-99`: Thunderstorm ⛈️
- **Comfort Scale configuration**: Map temperatures to comfort levels:
  - `<10°C`: Chilly ❄️
  - `10-18°C`: Cool 🍃
  - `18-27°C`: Pleasant 🍃
  - `27-35°C`: Warm ☀️
  - `>35°C`: Hot 🔥
- **Security-Minded Courier Toggle**:
  - A pill toggle button `⛅ Show Weather` / `☁️ Hide Weather` is featured in the Optimized Sequence card on [Courier.tsx](file:///c:/Users/GauryJithesh/Desktop/aarushi/IntelliSupply/frontend/app/src/pages/Courier.tsx).
  - Validation check:
    ```typescript
    const chosenStop = routeResult.stops.find(s => s.order_id === highlightedOrderId);
    const isAssigned = shipments.some(s => s.order_id === highlightedOrderId);
    if (chosenStop && isAssigned && user?.role === 'courier') { ... }
    ```
    This stops couriers from fetching weather details unless the selected shipment resides within their verified, assigned sequence stops, adhering to data confidentiality standards.

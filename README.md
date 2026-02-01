# TradingView to IBKR IB Gateway Middleman

A FastAPI application that acts as a middleman between TradingView webhook alerts and Interactive Brokers (IBKR) IB Gateway. This allows you to automatically execute trades on IBKR based on alerts from TradingView.

## Features

- Receives webhook alerts from TradingView
- Connects to IB Gateway or TWS (Trader Workstation)
- Executes market, limit, and stop orders
- Supports both paper trading and live trading
- RESTful API with health checks and status endpoints
- Comprehensive logging

## Quick Start (Using ngrok)

1. **Install ngrok**: `brew install ngrok/ngrok/ngrok` (or download from ngrok.com)
2. **Configure ngrok**: Get your authtoken from [ngrok dashboard](https://dashboard.ngrok.com/get-started/your-authtoken) and run `ngrok config add-authtoken YOUR_TOKEN`
3. **Start FastAPI server**: `python app.py` (in one terminal)
4. **Start ngrok**: `ngrok http 8000` (in another terminal)
5. **Copy the HTTPS URL** from ngrok (e.g., `https://abc123.ngrok-free.app`)
6. **Use in TradingView**: Set webhook URL to `https://abc123.ngrok-free.app/webhook`

Or use the helper script: `./ngrok_setup.sh`

## Prerequisites

1. **Interactive Brokers Account**: You need an IBKR account with API access enabled
2. **IB Gateway or TWS**: Install and run IB Gateway or TWS on your machine
3. **Python 3.8+**: Required to run the FastAPI application
4. **TradingView Account**: For creating alerts that send webhooks
5. **ngrok** (optional but recommended): For exposing your local server to the internet

## Installation

1. Clone or navigate to this directory:
```bash
cd /Users/bbognar/PycharmProjects/trading_automation
```

2. Create a virtual environment (recommended):
```bash
python3 -m venv venv
```

3. Activate the virtual environment:
   - **macOS/Linux**:
     ```bash
     source venv/bin/activate
     ```
   - **Windows**:
     ```bash
     venv\Scripts\activate
     ```

4. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables (optional):
```bash
cp .env.example .env
# Edit .env with your settings
```

## Configuration

### IB Gateway/TWS Setup

1. **Enable API Access**:
   - Open IB Gateway or TWS
   - Go to Configure → API → Settings
   - Enable "Enable ActiveX and Socket Clients"
   - Set "Socket port" (default: 7497 for paper, 7496 for live, 4002 for IB Gateway live)
   - Add your IP address to "Trusted IPs" (or use 127.0.0.1 for local)
   - **IMPORTANT**: Uncheck "Read-Only API" or disable "Read-Only Mode" to allow trading
   - Enable "Download Open Orders on Connection" (recommended)

2. **Port Configuration**:
   - **Paper Trading**: 
     - TWS: 7497
     - IB Gateway: 4001
   - **Live Trading**:
     - TWS: 7496
     - IB Gateway: 4002

### Environment Variables

You can configure the application using environment variables:

- `IB_HOST`: IB Gateway host (default: 127.0.0.1)
- `IB_PORT`: IB Gateway port (default: 7497)
- `IB_CLIENT_ID`: Client ID for IB connection (default: 1)
- `FLASK_PORT`: FastAPI server port (default: 8000)
- `FLASK_DEBUG`: Enable auto-reload mode (default: False)
- `FLASK_HOST`: Server host (default: 0.0.0.0)
- `WEBHOOK_SECRET`: Optional secret for webhook validation

## Usage

### Starting the Server

**Option 1: Using the app directly**
```bash
python app.py
```

**Option 2: Using uvicorn directly (recommended for production)**
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

The server will start on `http://0.0.0.0:8000` by default.

**Note**: FastAPI automatically provides interactive API documentation:
- **Swagger UI**: `http://localhost:8000/docs` - Interactive API explorer
- **ReDoc**: `http://localhost:8000/redoc` - Alternative API documentation

### Making Your Server Publicly Accessible with ngrok

Since TradingView needs to send webhooks to your server from the internet, you'll need to expose your local server. **ngrok** is a popular tool for this.

#### Step 1: Install ngrok

**macOS (using Homebrew)**:
```bash
brew install ngrok/ngrok/ngrok
```

**Or download directly**:
1. Visit [ngrok.com](https://ngrok.com/) and sign up for a free account
2. Download ngrok for your platform
3. Extract and add to your PATH, or use the full path

**macOS/Linux (manual)**:
```bash
# Download ngrok
curl -O https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-darwin-amd64.zip
unzip ngrok-v3-stable-darwin-amd64.zip
sudo mv ngrok /usr/local/bin/
```

#### Step 2: Get Your ngrok Auth Token

1. Sign up at [ngrok.com](https://dashboard.ngrok.com/signup) (free account)
2. Get your authtoken from the [dashboard](https://dashboard.ngrok.com/get-started/your-authtoken)
3. Configure ngrok:
```bash
ngrok config add-authtoken YOUR_AUTH_TOKEN
```

#### Step 3: Start Your FastAPI Server

In one terminal, start your FastAPI server:
```bash
python app.py
# or
uvicorn app:app --host 0.0.0.0 --port 8000
```

#### Step 4: Start ngrok

In another terminal, expose your local server:
```bash
ngrok http 8000
```

You'll see output like:
```
Forwarding  https://abc123.ngrok-free.app -> http://localhost:8000
```

**Copy the HTTPS URL** (e.g., `https://abc123.ngrok-free.app`)

#### Step 5: Configure TradingView Webhook

In TradingView, create an alert and use the ngrok URL:
```
https://abc123.ngrok-free.app/webhook
```

**Important Notes**:
- The free ngrok URL changes each time you restart ngrok (unless you have a paid plan with a static domain)
- Keep both your FastAPI server and ngrok running
- The ngrok web interface is available at `http://127.0.0.1:4040` to inspect requests

#### Alternative: Using ngrok with a Static Domain (Paid)

If you have a paid ngrok plan, you can use a static domain:
```bash
ngrok http 8000 --domain=your-static-domain.ngrok-free.app
```

### TradingView Webhook Setup

In TradingView, create an alert and use one of the following webhook URLs:

**Using ngrok (recommended for local development)**:
```
https://your-ngrok-url.ngrok-free.app/webhook
```

**Using a public server**:
```
http://your-server-ip:8000/webhook
```

### Webhook Payload Format

TradingView should send a POST request with the following JSON format:

```json
{
  "action": "BUY",
  "symbol": "AAPL",
  "quantity": 100,
  "orderType": "MARKET",
  "exchange": "SMART"
}
```

**Required Fields**:
- `action`: "BUY" or "SELL"
- `symbol`: Stock symbol (e.g., "AAPL", "TSLA")
- `quantity`: Number of shares

**Optional Fields**:
- `orderType`: "MARKET" (default), "LIMIT", or "STOP"
- `limitPrice`: Required for LIMIT orders
- `stopPrice`: Required for STOP orders
- `exchange`: Exchange (default: "SMART")

**Example Payloads**:

Market Order:
```json
{
  "action": "BUY",
  "symbol": "AAPL",
  "quantity": 100,
  "orderType": "MARKET"
}
```

Limit Order:
```json
{
  "action": "SELL",
  "symbol": "TSLA",
  "quantity": 50,
  "orderType": "LIMIT",
  "limitPrice": 250.00
}
```

Stop Order:
```json
{
  "action": "SELL",
  "symbol": "AAPL",
  "quantity": 100,
  "orderType": "STOP",
  "stopPrice": 145.00
}
```

## API Endpoints

### POST `/webhook`
Receives TradingView webhook alerts and executes trades.

**Response**:
```json
{
  "success": true,
  "order_id": 12345,
  "symbol": "AAPL",
  "action": "BUY",
  "quantity": 100,
  "order_type": "MARKET",
  "status": "Submitted",
  "message": "Order 12345 submitted successfully"
}
```

### GET `/health`
Health check endpoint.

**Response**:
```json
{
  "status": "healthy",
  "ib_connected": true,
  "timestamp": "2024-01-01T12:00:00"
}
```

### GET `/status`
Get IB Gateway connection status.

**Response**:
```json
{
  "connected": true,
  "host": "127.0.0.1",
  "port": 7497,
  "client_id": 1
}
```

### POST `/connect`
Manually connect to IB Gateway.

### POST `/disconnect`
Manually disconnect from IB Gateway.

## Testing

### Test Locally

You can test the webhook endpoint using curl:

```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "action": "BUY",
    "symbol": "AAPL",
    "quantity": 1,
    "orderType": "MARKET"
  }'
```

### Test with ngrok

Once ngrok is running, test using the public URL:

```bash
curl -X POST https://your-ngrok-url.ngrok-free.app/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "action": "BUY",
    "symbol": "AAPL",
    "quantity": 1,
    "orderType": "MARKET"
  }'
```

**Tip**: You can also use the ngrok web interface at `http://127.0.0.1:4040` to:
- See all incoming requests
- Replay requests
- Inspect request/response details

## Security Considerations

1. **Network Security**: 
   - When using ngrok, your server is publicly accessible - anyone with the URL can send requests
   - Consider implementing webhook secret validation (see below)
   - Use ngrok's IP restrictions if available on your plan
2. **Webhook Validation**: Consider implementing webhook secret validation to verify requests are from TradingView
3. **Rate Limiting**: Add rate limiting to prevent abuse
4. **Paper Trading First**: Always test with paper trading before using live trading
5. **Error Handling**: Monitor logs for failed orders
6. **ngrok Security**: 
   - Free ngrok URLs are publicly discoverable - consider using a paid plan for better security
   - Monitor the ngrok web interface at `http://127.0.0.1:4040` to see incoming requests
   - Consider using ngrok's request inspection feature to verify webhook payloads

## Troubleshooting

### Connection Issues

- Ensure IB Gateway/TWS is running
- Check that API access is enabled in IB Gateway/TWS settings
- Verify the port number matches your configuration
- Check firewall settings

### Order Execution Issues

- Verify you have sufficient buying power
- Check that the symbol is valid and tradeable
- Ensure market hours if using market orders
- Review IB Gateway/TWS logs for errors

## License

This project is provided as-is for educational and personal use. Use at your own risk.

## Disclaimer

Trading involves substantial risk of loss. This software is provided for educational purposes only. Always test thoroughly with paper trading before using real money. The authors are not responsible for any financial losses.


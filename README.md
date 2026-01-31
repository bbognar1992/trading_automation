# TradingView to IBKR IB Gateway Middleman

A Flask application that acts as a middleman between TradingView webhook alerts and Interactive Brokers (IBKR) IB Gateway. This allows you to automatically execute trades on IBKR based on alerts from TradingView.

## Features

- Receives webhook alerts from TradingView
- Connects to IB Gateway or TWS (Trader Workstation)
- Executes market, limit, and stop orders
- Supports both paper trading and live trading
- RESTful API with health checks and status endpoints
- Comprehensive logging

## Prerequisites

1. **Interactive Brokers Account**: You need an IBKR account with API access enabled
2. **IB Gateway or TWS**: Install and run IB Gateway or TWS on your machine
3. **Python 3.8+**: Required to run the Flask application
4. **TradingView Account**: For creating alerts that send webhooks

## Installation

1. Clone or navigate to this directory:
```bash
cd /Users/bbognar/PycharmProjects/trading_automation
```

2. Install dependencies:
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
   - Set "Socket port" (default: 7497 for paper, 7496 for live)
   - Add your IP address to "Trusted IPs" (or use 127.0.0.1 for local)

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
- `FLASK_PORT`: Flask server port (default: 5000)
- `FLASK_DEBUG`: Enable debug mode (default: False)
- `WEBHOOK_SECRET`: Optional secret for webhook validation

## Usage

### Starting the Server

```bash
python app.py
```

The server will start on `http://0.0.0.0:5000` by default.

### TradingView Webhook Setup

In TradingView, create an alert and use the following webhook URL:
```
http://your-server-ip:5000/webhook
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

You can test the webhook endpoint using curl:

```bash
curl -X POST http://localhost:5000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "action": "BUY",
    "symbol": "AAPL",
    "quantity": 1,
    "orderType": "MARKET"
  }'
```

## Security Considerations

1. **Network Security**: Expose the Flask server only on trusted networks or use a VPN
2. **Webhook Validation**: Consider implementing webhook secret validation
3. **Rate Limiting**: Add rate limiting to prevent abuse
4. **Paper Trading First**: Always test with paper trading before using live trading
5. **Error Handling**: Monitor logs for failed orders

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


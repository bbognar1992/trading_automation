"""
Flask application that acts as a middleman between TradingView alerts and IBKR IB Gateway.
Receives webhook alerts from TradingView and executes trades via Interactive Brokers.
"""

from flask import Flask, request, jsonify
from ib_insync import IB, Stock, MarketOrder, LimitOrder, StopOrder
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# IB Gateway connection settings (can be overridden by environment variables)
IB_HOST = os.getenv('IB_HOST', '127.0.0.1')
IB_PORT = int(os.getenv('IB_PORT', 7497))  # 7497 for TWS paper trading, 4001 for IB Gateway paper
IB_CLIENT_ID = int(os.getenv('IB_CLIENT_ID', 1))

# Initialize IB connection
ib = IB()

# Global flag to track connection status
ib_connected = False


def connect_ib():
    """Connect to IB Gateway/TWS."""
    global ib_connected
    try:
        if not ib.isConnected():
            ib.connect(IB_HOST, IB_PORT, clientId=IB_CLIENT_ID)
            ib_connected = True
            logger.info(f"Connected to IB Gateway at {IB_HOST}:{IB_PORT}")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to IB Gateway: {e}")
        ib_connected = False
        return False


def disconnect_ib():
    """Disconnect from IB Gateway/TWS."""
    global ib_connected
    try:
        if ib.isConnected():
            ib.disconnect()
            ib_connected = False
            logger.info("Disconnected from IB Gateway")
    except Exception as e:
        logger.error(f"Error disconnecting from IB Gateway: {e}")


def parse_tradingview_alert(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parse TradingView webhook alert data.
    
    Expected format from TradingView:
    {
        "action": "BUY" or "SELL",
        "symbol": "AAPL",
        "quantity": 100,
        "orderType": "MARKET" or "LIMIT" or "STOP",
        "limitPrice": 150.00 (optional, for LIMIT orders),
        "stopPrice": 145.00 (optional, for STOP orders),
        "exchange": "SMART" (optional, defaults to SMART)
    }
    """
    try:
        # Handle both JSON body and form data
        if isinstance(data, str):
            data = json.loads(data)
        
        action = data.get('action', '').upper()
        symbol = data.get('symbol', '').upper()
        quantity = int(data.get('quantity', 0))
        order_type = data.get('orderType', 'MARKET').upper()
        limit_price = data.get('limitPrice')
        stop_price = data.get('stopPrice')
        exchange = data.get('exchange', 'SMART')
        
        if not action or not symbol or quantity <= 0:
            raise ValueError("Missing required fields: action, symbol, or quantity")
        
        if action not in ['BUY', 'SELL']:
            raise ValueError(f"Invalid action: {action}. Must be BUY or SELL")
        
        if order_type not in ['MARKET', 'LIMIT', 'STOP']:
            raise ValueError(f"Invalid orderType: {order_type}")
        
        if order_type == 'LIMIT' and not limit_price:
            raise ValueError("limitPrice required for LIMIT orders")
        
        if order_type == 'STOP' and not stop_price:
            raise ValueError("stopPrice required for STOP orders")
        
        return {
            'action': action,
            'symbol': symbol,
            'quantity': quantity,
            'order_type': order_type,
            'limit_price': limit_price,
            'stop_price': stop_price,
            'exchange': exchange
        }
    except Exception as e:
        logger.error(f"Error parsing TradingView alert: {e}")
        return None


def execute_trade(order_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a trade through IB Gateway.
    
    Args:
        order_params: Parsed order parameters from TradingView alert
        
    Returns:
        Dictionary with execution result
    """
    if not ib.isConnected():
        if not connect_ib():
            return {
                'success': False,
                'error': 'Not connected to IB Gateway'
            }
    
    try:
        # Create contract
        contract = Stock(
            order_params['symbol'],
            exchange=order_params['exchange']
        )
        
        # Create order based on type
        if order_params['order_type'] == 'MARKET':
            order = MarketOrder(
                order_params['action'],
                order_params['quantity']
            )
        elif order_params['order_type'] == 'LIMIT':
            order = LimitOrder(
                order_params['action'],
                order_params['quantity'],
                order_params['limit_price']
            )
        elif order_params['order_type'] == 'STOP':
            order = StopOrder(
                order_params['action'],
                order_params['quantity'],
                order_params['stop_price']
            )
        
        # Place order
        trade = ib.placeOrder(contract, order)
        ib.sleep(1)  # Wait for order to be submitted
        
        logger.info(f"Order placed: {order_params['action']} {order_params['quantity']} "
                   f"{order_params['symbol']} ({order_params['order_type']})")
        
        return {
            'success': True,
            'order_id': trade.order.orderId,
            'symbol': order_params['symbol'],
            'action': order_params['action'],
            'quantity': order_params['quantity'],
            'order_type': order_params['order_type'],
            'status': trade.orderStatus.status,
            'message': f"Order {trade.order.orderId} submitted successfully"
        }
    except Exception as e:
        logger.error(f"Error executing trade: {e}")
        return {
            'success': False,
            'error': str(e)
        }


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'ib_connected': ib.isConnected(),
        'timestamp': datetime.now().isoformat()
    })


@app.route('/webhook', methods=['POST'])
def tradingview_webhook():
    """
    Endpoint to receive TradingView webhook alerts.
    
    Accepts POST requests with order details in JSON format.
    """
    try:
        # Get data from request
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
        
        logger.info(f"Received TradingView alert: {data}")
        
        # Parse the alert
        order_params = parse_tradingview_alert(data)
        if not order_params:
            return jsonify({
                'success': False,
                'error': 'Failed to parse alert data'
            }), 400
        
        # Execute the trade
        result = execute_trade(order_params)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/connect', methods=['POST'])
def connect():
    """Manually connect to IB Gateway."""
    if connect_ib():
        return jsonify({
            'success': True,
            'message': f'Connected to IB Gateway at {IB_HOST}:{IB_PORT}'
        }), 200
    else:
        return jsonify({
            'success': False,
            'error': 'Failed to connect to IB Gateway'
        }), 500


@app.route('/disconnect', methods=['POST'])
def disconnect():
    """Manually disconnect from IB Gateway."""
    disconnect_ib()
    return jsonify({
        'success': True,
        'message': 'Disconnected from IB Gateway'
    }), 200


@app.route('/status', methods=['GET'])
def status():
    """Get connection status."""
    return jsonify({
        'connected': ib.isConnected(),
        'host': IB_HOST,
        'port': IB_PORT,
        'client_id': IB_CLIENT_ID
    }), 200


if __name__ == '__main__':
    # Run Flask app
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting Flask server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)


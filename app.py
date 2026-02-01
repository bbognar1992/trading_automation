"""
FastAPI application that acts as a middleman between TradingView alerts and IBKR IB Gateway.
Receives webhook alerts from TradingView and executes trades via Interactive Brokers.
"""

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from ib_insync import IB, Stock, MarketOrder, LimitOrder, StopOrder
from ib_insync import util
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
import uvicorn
import asyncio
from concurrent.futures import ThreadPoolExecutor
from config import Config

# Thread pool for IB operations to avoid blocking the main event loop
# This runs IB operations in a separate thread with its own event loop
ib_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ib_")

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# IB Gateway connection settings (from Config class)
IB_HOST = Config.IB_HOST
IB_PORT = Config.IB_PORT
IB_CLIENT_ID = Config.IB_CLIENT_ID

# Initialize IB connection - will be created in thread with event loop
_ib_instance = None

def _get_ib():
    """Get or create IB instance in the current thread."""
    global _ib_instance
    
    # Ensure we have an event loop in this thread
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Create IB instance if it doesn't exist
    if _ib_instance is None:
        _ib_instance = IB()
    
    return _ib_instance


def connect_ib():
    """Connect to IB Gateway/TWS (runs in thread with event loop)."""
    try:
        # Ensure event loop exists and is set for this thread
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Start the loop in a way that ib_insync can use it
        # util.startLoop() starts the loop in a background thread
        # But we're already in a thread, so we need to run the loop ourselves
        ib = _get_ib()
        if not ib.isConnected():
            # Use ib.run() which properly handles the event loop
            # This is the recommended way when using ib_insync in threads
            ib.run(ib.connectAsync(IB_HOST, IB_PORT, clientId=IB_CLIENT_ID))
            logger.info(f"Connected to IB Gateway at {IB_HOST}:{IB_PORT}")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to IB Gateway: {e}")
        return False


def disconnect_ib():
    """Disconnect from IB Gateway/TWS (runs in thread with event loop)."""
    try:
        ib = _get_ib()
        if ib.isConnected():
            ib.disconnect()
            logger.info("Disconnected from IB Gateway")
    except Exception as e:
        logger.error(f"Error disconnecting from IB Gateway: {e}")


def is_ib_connected():
    """Check if IB is connected (runs in thread with event loop)."""
    try:
        ib = _get_ib()
        return ib.isConnected()
    except:
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Starting FastAPI application...")
    # Optionally connect on startup
    # loop = asyncio.get_event_loop()
    # await loop.run_in_executor(ib_executor, connect_ib)
    yield
    # Shutdown
    logger.info("Shutting down FastAPI application...")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(ib_executor, disconnect_ib)


# Initialize FastAPI app (after lifespan is defined)
app = FastAPI(
    title="TradingView-IBKR Middleman",
    description="Middleman between TradingView alerts and IBKR IB Gateway",
    version="1.0.0",
    lifespan=lifespan
)


# Pydantic models for request/response validation
class TradingViewAlert(BaseModel):
    """TradingView webhook alert model."""
    action: str = Field(..., description="BUY or SELL")
    symbol: str = Field(..., description="Stock symbol (e.g., AAPL)")
    quantity: int = Field(..., gt=0, description="Number of shares")
    orderType: Optional[str] = Field("MARKET", description="MARKET, LIMIT, or STOP")
    limitPrice: Optional[float] = Field(None, description="Limit price for LIMIT orders")
    stopPrice: Optional[float] = Field(None, description="Stop price for STOP orders")
    exchange: Optional[str] = Field("SMART", description="Exchange (default: SMART)")
    secret: Optional[str] = Field(None, description="Webhook secret for authentication (optional)")

    class Config:
        json_schema_extra = {
            "example": {
                "action": "BUY",
                "symbol": "AAPL",
                "quantity": 100,
                "orderType": "MARKET",
                "exchange": "SMART"
            }
        }


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    ib_connected: bool
    timestamp: str


class StatusResponse(BaseModel):
    """Status response model."""
    connected: bool
    host: str
    port: int
    client_id: int


class MessageResponse(BaseModel):
    """Generic message response model."""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None


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


def _execute_trade_sync(order_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a trade through IB Gateway (synchronous, runs in thread).
    
    Args:
        order_params: Parsed order parameters from TradingView alert
        
    Returns:
        Dictionary with execution result
    """
    ib = _get_ib()
    
    if not ib.isConnected():
        if not connect_ib():
            return {
                'success': False,
                'error': 'Not connected to IB Gateway'
            }
    
    try:
        # Create contract - specify currency for US stocks (default to USD)
        # For international stocks, you may need to specify different currencies
        contract = Stock(
            order_params['symbol'],
            exchange=order_params['exchange'],
            currency='USD'  # Specify currency to avoid ambiguity
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
        
        # Wait for order status update (give it time to process)
        ib.sleep(2)  # Wait 2 seconds for order to be processed
        
        # Check order status - wait for it to move from PendingSubmit
        max_wait = 5
        waited = 0
        while waited < max_wait and trade.orderStatus.status in ['PendingSubmit', 'PreSubmitted']:
            ib.sleep(0.5)
            waited += 0.5
        
        # Get the current order status
        order_status = trade.orderStatus.status
        order_id = trade.order.orderId
        
        # Check for order rejection or errors
        if order_status in ['Cancelled', 'Inactive']:
            error_msg = f"Order {order_id} was {order_status.lower()}"
            # Check for error messages in trade log
            if hasattr(trade, 'log') and trade.log:
                last_log = trade.log[-1]
                if hasattr(last_log, 'message') and last_log.message:
                    error_msg += f": {last_log.message}"
            logger.error(error_msg)
            return {
                'success': False,
                'order_id': order_id,
                'status': order_status,
                'error': error_msg
            }
        
        # Check if connection is still alive
        if not ib.isConnected():
            logger.warning("Connection lost after placing order, but order was submitted")
            return {
                'success': True,
                'order_id': order_id,
                'symbol': order_params['symbol'],
                'action': order_params['action'],
                'quantity': order_params['quantity'],
                'order_type': order_params['order_type'],
                'status': order_status,
                'warning': 'Connection lost after submission. Please verify order status in IB Gateway.',
                'message': f"Order {order_id} submitted (status: {order_status})"
            }
        
        logger.info(f"Order placed: {order_params['action']} {order_params['quantity']} "
                   f"{order_params['symbol']} ({order_params['order_type']}) - Status: {order_status}")
        
        return {
            'success': True,
            'order_id': order_id,
            'symbol': order_params['symbol'],
            'action': order_params['action'],
            'quantity': order_params['quantity'],
            'order_type': order_params['order_type'],
            'status': order_status,
            'message': f"Order {order_id} submitted successfully (status: {order_status})"
        }
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error executing trade: {e}")
        
        # Check if order was already placed before the error
        # If we get a socket disconnect but the order was submitted, it's still a success
        if 'Broken pipe' in error_msg or 'Socket disconnect' in error_msg or 'disconnect' in error_msg.lower():
            logger.warning("Connection lost, but order may have been submitted. Check IB Gateway for order status.")
            return {
                'success': True,
                'warning': 'Connection lost after order submission. Please verify order status in IB Gateway.',
                'error': error_msg
            }
        
        return {
            'success': False,
            'error': error_msg
        }


async def execute_trade(order_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a trade through IB Gateway (async wrapper).
    
    Args:
        order_params: Parsed order parameters from TradingView alert
        
    Returns:
        Dictionary with execution result
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(ib_executor, _execute_trade_sync, order_params)


@app.get('/health', response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    loop = asyncio.get_event_loop()
    connected = await loop.run_in_executor(ib_executor, is_ib_connected)
    return {
        'status': 'healthy',
        'ib_connected': connected,
        'timestamp': datetime.now().isoformat()
    }


@app.post('/webhook', tags=["Trading"])
async def tradingview_webhook(
    alert: TradingViewAlert, 
    request: Request,
    x_webhook_secret: Optional[str] = Header(None, alias="X-Webhook-Secret")
):
    """
    Endpoint to receive TradingView webhook alerts.
    
    Accepts POST requests with order details in JSON format.
    
    Webhook Secret Validation:
    - If WEBHOOK_SECRET is configured, the request must include the secret
    - Secret can be provided via:
      1. X-Webhook-Secret header (recommended)
      2. 'secret' field in the JSON body
    """
    try:
        # Validate webhook secret if configured
        if Config.WEBHOOK_SECRET:
            # Check header first
            secret = x_webhook_secret
            
            # If not in header, check request body
            if not secret:
                try:
                    body = await request.json()
                    secret = body.get('secret')
                except:
                    pass
            
            # Validate secret
            if not secret or secret != Config.WEBHOOK_SECRET:
                logger.warning(f"Invalid or missing webhook secret from {request.client.host}")
                raise HTTPException(
                    status_code=401,
                    detail='Invalid or missing webhook secret'
                )
            logger.debug("Webhook secret validated successfully")
        
        logger.info(f"Received TradingView alert: {alert.model_dump()}")
        
        # Convert Pydantic model to dict
        data = alert.model_dump()
        
        # Remove secret from data if present (don't process it as order data)
        data.pop('secret', None)
        
        # Parse the alert (for validation)
        order_params = parse_tradingview_alert(data)
        if not order_params:
            raise HTTPException(
                status_code=400,
                detail='Failed to parse alert data'
            )
        
        # Execute the trade
        result = await execute_trade(order_params)
        
        if result['success']:
            return result
        else:
            raise HTTPException(
                status_code=500,
                detail=result.get('error', 'Unknown error executing trade')
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.post('/connect', response_model=MessageResponse, tags=["Connection"])
async def connect():
    """Manually connect to IB Gateway."""
    loop = asyncio.get_event_loop()
    success = await loop.run_in_executor(ib_executor, connect_ib)
    if success:
        return {
            'success': True,
            'message': f'Connected to IB Gateway at {IB_HOST}:{IB_PORT}'
        }
    else:
        raise HTTPException(
            status_code=500,
            detail='Failed to connect to IB Gateway'
        )


@app.post('/disconnect', response_model=MessageResponse, tags=["Connection"])
async def disconnect():
    """Manually disconnect from IB Gateway."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(ib_executor, disconnect_ib)
    return {
        'success': True,
        'message': 'Disconnected from IB Gateway'
    }


@app.get('/status', response_model=StatusResponse, tags=["Connection"])
async def status():
    """Get connection status."""
    loop = asyncio.get_event_loop()
    connected = await loop.run_in_executor(ib_executor, is_ib_connected)
    return {
        'connected': connected,
        'host': IB_HOST,
        'port': IB_PORT,
        'client_id': IB_CLIENT_ID
    }


def _get_open_orders_sync():
    """Get all open orders (runs in thread)."""
    try:
        ib = _get_ib()
        if not ib.isConnected():
            return []
        
        # Request open orders
        ib.reqAllOpenOrders()
        ib.sleep(1)  # Wait for orders to be retrieved
        
        # Get open trades
        open_trades = ib.openTrades()
        orders = []
        for trade in open_trades:
            orders.append({
                'order_id': trade.order.orderId,
                'symbol': trade.contract.symbol,
                'action': trade.order.action,
                'quantity': trade.order.totalQuantity,
                'order_type': trade.order.orderType,
                'status': trade.orderStatus.status,
                'filled': trade.orderStatus.filled,
                'remaining': trade.orderStatus.remaining,
                'avg_fill_price': trade.orderStatus.avgFillPrice
            })
        return orders
    except Exception as e:
        logger.error(f"Error getting open orders: {e}")
        return []


@app.get('/orders', tags=["Trading"])
async def get_open_orders():
    """Get all open orders from IB Gateway."""
    loop = asyncio.get_event_loop()
    orders = await loop.run_in_executor(ib_executor, _get_open_orders_sync)
    return {
        'success': True,
        'orders': orders,
        'count': len(orders)
    }




if __name__ == '__main__':
    # Run FastAPI app with uvicorn (using Config class)
    logger.info(f"Starting FastAPI server on {Config.FLASK_HOST}:{Config.FLASK_PORT}")
    uvicorn.run(
        "app:app",
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        reload=Config.FLASK_DEBUG,
        log_level="info"
    )

import asyncio
import websockets
import json
import logging
import os
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def handle_connection(websocket, path):
    """Simple WebSocket handler for testing"""
    logger.info(f"New connection established at {datetime.now()}")
    
    try:
        # Send initial test message
        initial_message = {
            "status": "connected",
            "message": "WebSocket server is working!",
            "timestamp": datetime.now().isoformat()
        }
        await websocket.send(json.dumps(initial_message))
        logger.info("Sent initial test message")
        
        # Listen for messages
        async for message in websocket:
            logger.info(f"Received: {message}")
            
            # Echo back the message
            response = {
                "echo": message,
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send(json.dumps(response))
            
    except websockets.exceptions.ConnectionClosed:
        logger.info("Connection closed")
    except Exception as e:
        logger.error(f"Error: {e}")

async def main():
    """Main server function"""
    host = "0.0.0.0"
    port = int(os.getenv("PORT", 8080))
    
    logger.info(f"Starting test WebSocket server on {host}:{port}")
    
    # Start the WebSocket server
    server = await websockets.serve(
        handle_connection,
        host,
        port,
        ping_interval=30,
        ping_timeout=10
    )
    
    logger.info("WebSocket server started successfully")
    logger.info(f"Server listening on ws://{host}:{port}")
    
    # Keep the server running
    await server.wait_closed()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Server error: {e}")
    

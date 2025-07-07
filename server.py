import asyncio
import websockets
import json
import logging
from datetime import datetime
from mistralai.client import MistralClient
import os
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RetellMistralServer:
    def __init__(self):
        # Initialize Mistral client
        self.mistral_client = MistralClient(
            api_key=os.getenv("MISTRAL_API_KEY", "your-mistral-api-key-here")
        )
        
        # Your fine-tuned model ID from Mistral console
        self.model_id = "6TcdJZMB27yANAbVT3MBpQvp5iPR97vZ"
        
        # Store conversation context
        self.conversations: Dict[str, List[Dict]] = {}
        
    async def handle_connection(self, websocket, path):
        """Handle incoming WebSocket connections from Retell AI"""
        logger.info(f"New connection established at {datetime.now()}")
        
        try:
            # Send initial message when connection is established
            initial_message = {
                "response_type": "response",
                "response_id": 0,
                "content": "Hello! I'm your AI assistant. How can I help you today?",
                "content_complete": True,
                "end_call": False
            }
            await websocket.send(json.dumps(initial_message))
            logger.info("Sent initial greeting message")
            
            # Listen for messages from Retell AI
            async for message in websocket:
                await self.process_message(websocket, message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info("Connection closed")
        except Exception as e:
            logger.error(f"Error in connection handler: {e}")
    
    async def process_message(self, websocket, message: str):
        """Process incoming messages from Retell AI"""
        try:
            data = json.loads(message)
            logger.info(f"Received message: {data}")
            
            interaction_type = data.get("interaction_type")
            
            if interaction_type == "response_required":
                await self.handle_response_required(websocket, data)
            elif interaction_type == "update_only":
                await self.handle_update_only(data)
            else:
                logger.warning(f"Unknown interaction type: {interaction_type}")
                
        except json.JSONDecodeError:
            logger.error("Failed to decode JSON message")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    async def handle_response_required(self, websocket, data: Dict[str, Any]):
        """Handle when Retell AI requires a response"""
        try:
            # Extract conversation data
            call_id = data.get("call_id", "unknown")
            response_id = data.get("response_id", 0)
            transcript = data.get("transcript", [])
            
            # Get the latest user message
            user_message = ""
            if transcript:
                # Find the last user message
                for entry in reversed(transcript):
                    if entry.get("role") == "user":
                        user_message = entry.get("content", "")
                        break
            
            logger.info(f"Processing user message: {user_message}")
            
            # Prepare conversation context for Mistral
            conversation_history = self.prepare_conversation_context(call_id, transcript)
            
            # Call your fine-tuned Mistral model
            response_content = await self.call_mistral_model(conversation_history, user_message)
            
            # Send response back to Retell AI
            response_message = {
                "response_type": "response",
                "response_id": response_id,
                "content": response_content,
                "content_complete": True,
                "end_call": False
            }
            
            await websocket.send(json.dumps(response_message))
            logger.info(f"Sent response: {response_content[:100]}...")
            
        except Exception as e:
            logger.error(f"Error handling response required: {e}")
            # Send error response
            error_response = {
                "response_type": "response",
                "response_id": data.get("response_id", 0),
                "content": "I apologize, but I'm having trouble processing your request. Could you please try again?",
                "content_complete": True,
                "end_call": False
            }
            await websocket.send(json.dumps(error_response))
    
    async def handle_update_only(self, data: Dict[str, Any]):
        """Handle update-only messages (transcript updates)"""
        # You can log or store transcript updates here
        logger.info("Received transcript update")
        pass
    
    def prepare_conversation_context(self, call_id: str, transcript: List[Dict]) -> List[Dict]:
        """Prepare conversation context for Mistral API"""
        messages = []
        
        # Add system message if needed
        messages.append({
            "role": "system",
            "content": "You are a helpful AI assistant. Provide clear, concise, and helpful responses."
        })
        
        # Convert transcript to Mistral format
        for entry in transcript:
            role = entry.get("role")
            content = entry.get("content", "")
            
            if role == "user":
                messages.append({"role": "user", "content": content})
            elif role == "assistant":
                messages.append({"role": "assistant", "content": content})
        
        return messages
    
    async def call_mistral_model(self, conversation_history: List[Dict], user_message: str) -> str:
        """Call your fine-tuned Mistral model"""
        try:
            # Make sure we have the user message in the conversation
            if user_message and (not conversation_history or conversation_history[-1]["content"] != user_message):
                conversation_history.append({"role": "user", "content": user_message})
            
            # Call Mistral API
            response = self.mistral_client.chat(
                model=self.model_id,
                messages=conversation_history,
                max_tokens=500,  # Adjust as needed
                temperature=0.7,  # Adjust as needed
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error calling Mistral API: {e}")
            return "I apologize, but I'm experiencing technical difficulties. Please try again."

# Server configuration
SERVER_HOST = "0.0.0.0"
SERVER_PORT = int(os.getenv("PORT", 8080))

async def main():
    """Main server function"""
    server = RetellMistralServer()
    
    logger.info(f"Starting Retell-Mistral WebSocket server on {SERVER_HOST}:{SERVER_PORT}")
    
    # Start the WebSocket server
    start_server = websockets.serve(
        server.handle_connection,
        SERVER_HOST,
        SERVER_PORT,
        ping_interval=30,  # Send ping every 30 seconds
        ping_timeout=10,   # Wait 10 seconds for pong
    )
    
    await start_server
    logger.info("WebSocket server started successfully")
    
    # Keep the server running
    await asyncio.Future()  # Run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Server error: {e}")

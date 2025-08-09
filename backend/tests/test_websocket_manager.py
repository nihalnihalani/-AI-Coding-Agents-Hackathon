import pytest
import json
import asyncio
from datetime import datetime
from fastapi.testclient import TestClient
from fastapi import WebSocket
from unittest.mock import AsyncMock, MagicMock

from app.services.websocket_manager import websocket_manager, ConnectionState
from app.services.notification_service import NotificationType, NotificationPriority
from app.core.auth import auth_service


class TestWebSocketManager:
    """Test WebSocket manager functionality."""
    
    @pytest.fixture
    async def mock_websocket(self):
        """Create a mock WebSocket connection."""
        websocket = AsyncMock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.receive_text = AsyncMock()
        websocket.client = MagicMock()
        websocket.client.host = "127.0.0.1"
        return websocket
    
    @pytest.fixture
    def valid_token(self):
        """Create a valid JWT token for testing."""
        user = auth_service.authenticate_user("demo@aura.ai", "demo123")
        return auth_service.create_access_token(
            data={"sub": user["email"], "role": user["role"]}
        )
    
    async def test_websocket_connect_without_auth(self, mock_websocket):
        """Test WebSocket connection without authentication."""
        session_id = "test-session-123"
        
        await websocket_manager.connect(mock_websocket, session_id)
        
        # Should accept connection
        mock_websocket.accept.assert_called_once()
        
        # Should be in connections but not authenticated
        assert session_id in websocket_manager.active_connections
        assert session_id not in websocket_manager.authenticated_sessions
        
        # Should send connection confirmation
        mock_websocket.send_text.assert_called()
        sent_message = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_message["data"]["type"] == "connection_established"
        assert sent_message["data"]["authentication_required"] is True
        
        # Clean up
        await websocket_manager.disconnect(session_id)
    
    async def test_websocket_connect_with_auth(self, mock_websocket, valid_token):
        """Test WebSocket connection with authentication."""
        session_id = "test-session-auth"
        client_info = {"user_agent": "TestClient/1.0"}
        
        await websocket_manager.connect(
            mock_websocket, 
            session_id, 
            token=valid_token,
            client_info=client_info
        )
        
        # Should be connected and authenticated
        assert session_id in websocket_manager.active_connections
        assert session_id in websocket_manager.authenticated_sessions
        
        # Should have user data
        user_data = websocket_manager.session_users.get(session_id)
        assert user_data is not None
        assert user_data["email"] == "demo@aura.ai"
        
        # Should have connection metadata
        metadata = websocket_manager.connection_metadata.get(session_id)
        assert metadata is not None
        assert metadata["state"] == ConnectionState.AUTHENTICATED
        assert metadata["client_info"] == client_info
        
        # Clean up
        await websocket_manager.disconnect(session_id)
    
    async def test_websocket_authentication_failure(self, mock_websocket):
        """Test WebSocket authentication with invalid token."""
        session_id = "test-session-invalid"
        invalid_token = "invalid-token-123"
        
        await websocket_manager.connect(mock_websocket, session_id, token=invalid_token)
        
        # Should be connected but not authenticated
        assert session_id in websocket_manager.active_connections
        assert session_id not in websocket_manager.authenticated_sessions
        
        # Should send authentication failure message
        calls = mock_websocket.send_text.call_args_list
        auth_failure_sent = False
        for call in calls:
            message = json.loads(call[0][0])
            if message.get("data", {}).get("type") == "authentication_failed":
                auth_failure_sent = True
                break
        
        assert auth_failure_sent
        
        # Clean up
        await websocket_manager.disconnect(session_id)
    
    async def test_send_message_authenticated(self, mock_websocket, valid_token):
        """Test sending message to authenticated connection."""
        session_id = "test-send-auth"
        
        # Connect and authenticate
        await websocket_manager.connect(mock_websocket, session_id, token=valid_token)
        
        # Send message
        message = {"type": "test_message", "data": {"content": "Hello"}}
        result = await websocket_manager.send_message(session_id, message, require_auth=True)
        
        assert result is True
        
        # Verify message was sent
        calls = [call for call in mock_websocket.send_text.call_args_list 
                 if "test_message" in str(call)]
        assert len(calls) > 0
        
        sent_message = json.loads(calls[0][0][0])
        assert sent_message["type"] == "test_message"
        assert sent_message["data"]["content"] == "Hello"
        assert "message_id" in sent_message
        
        # Clean up
        await websocket_manager.disconnect(session_id)
    
    async def test_send_message_unauthenticated(self, mock_websocket):
        """Test sending message to unauthenticated connection."""
        session_id = "test-send-unauth"
        
        # Connect without authentication
        await websocket_manager.connect(mock_websocket, session_id)
        
        # Try to send message requiring auth
        message = {"type": "test_message", "data": {"content": "Hello"}}
        result = await websocket_manager.send_message(session_id, message, require_auth=True)
        
        assert result is False
        
        # Clean up
        await websocket_manager.disconnect(session_id)
    
    async def test_send_system_message(self, mock_websocket):
        """Test sending system message (no auth required)."""
        session_id = "test-system"
        
        # Connect without authentication
        await websocket_manager.connect(mock_websocket, session_id)
        
        # Send system message
        data = {"type": "system_alert", "message": "System maintenance"}
        result = await websocket_manager.send_system_message(session_id, data)
        
        assert result is True
        
        # Clean up
        await websocket_manager.disconnect(session_id)
    
    async def test_broadcast_message(self, mock_websocket, valid_token):
        """Test broadcasting message to multiple connections."""
        session_ids = ["broadcast-1", "broadcast-2", "broadcast-3"]
        websockets = []
        
        # Create multiple connections
        for i, session_id in enumerate(session_ids):
            ws = AsyncMock(spec=WebSocket)
            ws.accept = AsyncMock()
            ws.send_text = AsyncMock()
            ws.client = MagicMock()
            ws.client.host = f"127.0.0.{i+1}"
            websockets.append(ws)
            
            # Connect and authenticate
            await websocket_manager.connect(ws, session_id, token=valid_token)
        
        # Broadcast message
        message = {"type": "broadcast_test", "data": {"message": "Hello everyone"}}
        results = await websocket_manager.broadcast_message(message, require_auth=True)
        
        # All should receive the message
        assert len(results) == 3
        assert all(results.values())
        
        # Verify all websockets received the message
        for ws in websockets:
            broadcast_calls = [call for call in ws.send_text.call_args_list 
                             if "broadcast_test" in str(call)]
            assert len(broadcast_calls) > 0
        
        # Clean up
        for session_id in session_ids:
            await websocket_manager.disconnect(session_id)
    
    async def test_handle_incoming_message_ping(self, mock_websocket, valid_token):
        """Test handling ping message."""
        session_id = "test-ping"
        
        await websocket_manager.connect(mock_websocket, session_id, token=valid_token)
        
        # Handle ping message
        ping_message = json.dumps({"type": "ping"})
        await websocket_manager.handle_incoming_message(session_id, ping_message)
        
        # Should send pong response
        pong_calls = [call for call in mock_websocket.send_text.call_args_list 
                     if "pong" in str(call)]
        assert len(pong_calls) > 0
        
        pong_message = json.loads(pong_calls[0][0][0])
        assert pong_message["data"]["type"] == "pong"
        
        # Clean up
        await websocket_manager.disconnect(session_id)
    
    async def test_handle_incoming_message_authentication(self, mock_websocket, valid_token):
        """Test handling authentication message."""
        session_id = "test-auth-msg"
        
        # Connect without initial auth
        await websocket_manager.connect(mock_websocket, session_id)
        
        # Should not be authenticated initially
        assert session_id not in websocket_manager.authenticated_sessions
        
        # Send authentication message
        auth_message = json.dumps({
            "type": "authenticate",
            "token": valid_token
        })
        await websocket_manager.handle_incoming_message(session_id, auth_message)
        
        # Should now be authenticated
        assert session_id in websocket_manager.authenticated_sessions
        
        # Should receive authentication success message
        success_calls = [call for call in mock_websocket.send_text.call_args_list 
                        if "authentication_success" in str(call)]
        assert len(success_calls) > 0
        
        # Clean up
        await websocket_manager.disconnect(session_id)
    
    async def test_handle_incoming_message_subscribe(self, mock_websocket, valid_token):
        """Test handling subscription update message."""
        session_id = "test-subscribe"
        
        await websocket_manager.connect(mock_websocket, session_id, token=valid_token)
        
        # Send subscription message
        subscribe_message = json.dumps({
            "type": "subscribe",
            "notification_types": ["chat_message", "task_update"]
        })
        await websocket_manager.handle_incoming_message(session_id, subscribe_message)
        
        # Should update subscriptions
        subscriptions = websocket_manager.session_subscriptions.get(session_id, set())
        assert NotificationType.CHAT_MESSAGE in subscriptions
        assert NotificationType.TASK_UPDATE in subscriptions
        
        # Should receive subscription confirmation
        confirm_calls = [call for call in mock_websocket.send_text.call_args_list 
                        if "subscriptions_updated" in str(call)]
        assert len(confirm_calls) > 0
        
        # Clean up
        await websocket_manager.disconnect(session_id)
    
    async def test_handle_incoming_message_invalid_json(self, mock_websocket, valid_token):
        """Test handling invalid JSON message."""
        session_id = "test-invalid-json"
        
        await websocket_manager.connect(mock_websocket, session_id, token=valid_token)
        
        # Send invalid JSON
        await websocket_manager.handle_incoming_message(session_id, "invalid json {")
        
        # Should receive error message
        error_calls = [call for call in mock_websocket.send_text.call_args_list 
                      if "error" in str(call) and "Invalid JSON" in str(call)]
        assert len(error_calls) > 0
        
        # Clean up
        await websocket_manager.disconnect(session_id)
    
    async def test_get_connection_info(self, mock_websocket, valid_token):
        """Test getting connection information."""
        session_id = "test-info"
        client_info = {"user_agent": "TestClient/1.0", "version": "1.0"}
        
        await websocket_manager.connect(
            mock_websocket, 
            session_id, 
            token=valid_token,
            client_info=client_info
        )
        
        # Get connection info
        info = websocket_manager.get_connection_info(session_id)
        
        assert info is not None
        assert info["session_id"] == session_id
        assert info["state"] == ConnectionState.AUTHENTICATED
        assert info["authenticated"] is True
        assert info["user_info"]["email"] == "demo@aura.ai"
        assert info["client_info"] == client_info
        assert info["ip_address"] == "127.0.0.1"
        
        # Clean up
        await websocket_manager.disconnect(session_id)
    
    async def test_get_service_stats(self, mock_websocket, valid_token):
        """Test getting service statistics."""
        session_id = "test-stats"
        
        # Get initial stats
        initial_stats = websocket_manager.get_service_stats()
        initial_active = initial_stats["active_connections"]
        
        # Connect a session
        await websocket_manager.connect(mock_websocket, session_id, token=valid_token)
        
        # Get updated stats
        updated_stats = websocket_manager.get_service_stats()
        
        assert updated_stats["active_connections"] == initial_active + 1
        assert updated_stats["authenticated_connections"] == 1
        assert updated_stats["service_health"] == "healthy"
        assert "timestamp" in updated_stats
        
        # Clean up
        await websocket_manager.disconnect(session_id)
    
    async def test_disconnect_cleanup(self, mock_websocket, valid_token):
        """Test proper cleanup on disconnect."""
        session_id = "test-disconnect"
        
        # Connect and authenticate
        await websocket_manager.connect(mock_websocket, session_id, token=valid_token)
        
        # Verify connection exists
        assert session_id in websocket_manager.active_connections
        assert session_id in websocket_manager.authenticated_sessions
        assert session_id in websocket_manager.session_users
        assert session_id in websocket_manager.connection_metadata
        
        # Disconnect
        await websocket_manager.disconnect(session_id)
        
        # Verify cleanup
        assert session_id not in websocket_manager.active_connections
        assert session_id not in websocket_manager.authenticated_sessions
        assert session_id not in websocket_manager.session_users
        assert session_id not in websocket_manager.connection_metadata
    
    async def test_cleanup_inactive_connections(self, mock_websocket):
        """Test cleanup of inactive connections."""
        session_id = "test-cleanup"
        
        # Connect
        await websocket_manager.connect(mock_websocket, session_id)
        
        # Manually set old connection time
        if session_id in websocket_manager.connection_metadata:
            old_time = datetime.now().replace(year=2020).isoformat()
            websocket_manager.connection_metadata[session_id]["connected_at"] = old_time
        
        # Run cleanup
        cleaned_count = await websocket_manager.cleanup_inactive_connections(max_age_hours=1)
        
        # Should have cleaned up the old connection
        assert cleaned_count == 1
        assert session_id not in websocket_manager.active_connections
    
    def test_websocket_integration_with_client(self, client: TestClient, valid_token):
        """Test WebSocket integration with FastAPI test client."""
        # Note: This is a basic integration test
        # Full WebSocket testing would require a more sophisticated setup
        
        with client.websocket_connect(f"/chat/stream/test-integration?token={valid_token}") as websocket:
            # Should connect successfully
            data = websocket.receive_json()
            
            # Should receive connection established message
            assert data["category"] == "system"
            assert data["data"]["type"] == "connection_established"
            
            # Send a ping
            websocket.send_json({"type": "ping"})
            
            # Should receive pong
            pong_response = websocket.receive_json()
            assert pong_response["category"] == "system"
            assert pong_response["data"]["type"] == "pong"
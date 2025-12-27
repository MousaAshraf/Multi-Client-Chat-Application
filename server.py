"""
Multi-Client Chat Server
Team: Mousa & Shahd (Server Architecture)

Requirements Implemented:
1. Server-Client Architecture ✓
2. Multithreading ✓
3. Private Messaging ✓
4. Group Messaging ✓
5. Connection Management ✓
6. Scalability (100 clients) ✓
7. Wired + Wireless Support ✓
"""

import socket
import threading
import time
from datetime import datetime
from typing import Dict, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('server.log'),
        logging.StreamHandler()
    ]
)

# Network Configuration - WIRED + WIRELESS SUPPORT
HOST = "0.0.0.0"  # Binds to all network interfaces (Ethernet + Wi-Fi)
PORT = 5000
MAX_CLIENTS = 100  # Scalability requirement

class ChatServer:
    """
    Multi-Client Chat Server Architecture
    Handles: Server-Client Architecture, Multithreading, Connection Management, Scalability
    """
    
    def __init__(self):
        # Client management
        self.clients: Dict[str, socket.socket] = {}
        self.clients_lock = threading.Lock()
        self.active_connections = 0
        
        # Connection tracking
        self.connection_count = 0
        self.max_concurrent = 0
        
        logging.info("[OK] Server initialized")
    
    # ==================== CONNECTION MANAGEMENT ====================
    
    def add_client(self, username: str, client_socket: socket.socket) -> bool:
        """
        Add client to active connections with thread safety
        Returns: True if added successfully, False if username taken
        """
        with self.clients_lock:
            if username in self.clients:
                return False
            
            self.clients[username] = client_socket
            self.active_connections += 1
            self.connection_count += 1
            
            # Track maximum concurrent connections
            if self.active_connections > self.max_concurrent:
                self.max_concurrent = self.active_connections
            
            logging.info(f">> {username} connected (Active: {self.active_connections}/{MAX_CLIENTS})")
            return True
    
    def remove_client(self, username: str, notify: bool = True):
        """
        Remove client and handle cleanup gracefully
        Implements: Connection Management requirement
        """
        with self.clients_lock:
            if username in self.clients:
                try:
                    # Notify client before closing
                    if notify:
                        disconnect_msg = "[SERVER] Connection closed"
                        try:
                            self.clients[username].send(disconnect_msg.encode())
                        except:
                            pass
                    
                    self.clients[username].close()
                except Exception as e:
                    logging.error(f"Error closing socket for {username}: {e}")
                
                del self.clients[username]
                self.active_connections -= 1
                
                logging.info(f"<< {username} disconnected (Active: {self.active_connections})")
                
                # Notify other users
                if notify:
                    self.broadcast(f"[SERVER] {username} left the chat", sender=username)
    
    def get_online_users(self) -> list:
        """Get list of currently connected users"""
        with self.clients_lock:
            return list(self.clients.keys())
    
    # ==================== MESSAGE ROUTING ====================
    
    def broadcast(self, message: str, sender: Optional[str] = None):
        """
        Group Messaging: Broadcast to all connected clients
        Implements: Group Messaging requirement
        """
        with self.clients_lock:
            disconnected = []
            
            for username, client_socket in self.clients.items():
                if username != sender:  # Don't send back to sender
                    try:
                        client_socket.send(message.encode())
                    except Exception as e:
                        logging.warning(f"Failed to send to {username}: {e}")
                        disconnected.append(username)
            
            # Remove disconnected clients
            for username in disconnected:
                self.remove_client(username, notify=False)
    
    def private_message(self, target_user: str, message: str, sender: str):
        """
        Private Messaging: Send message to specific user only
        Implements: Private Messaging requirement
        """
        with self.clients_lock:
            # Check if target user is online
            if target_user in self.clients:
                try:
                    # Send to target
                    private_msg = f"[PRIVATE] {sender}: {message}"
                    self.clients[target_user].send(private_msg.encode())
                    
                    # Confirm to sender
                    confirmation = f"[SENT] Private message to {target_user}"
                    self.clients[sender].send(confirmation.encode())
                    
                    logging.info(f"Private: {sender} -> {target_user}")
                    
                except Exception as e:
                    logging.error(f"Failed to send private message: {e}")
                    error_msg = f"[ERROR] Could not deliver message to {target_user}"
                    try:
                        self.clients[sender].send(error_msg.encode())
                    except:
                        pass
            else:
                # User not found
                error_msg = f"[ERROR] User '{target_user}' is not online"
                try:
                    self.clients[sender].send(error_msg.encode())
                except:
                    pass
    
    # ==================== CLIENT HANDLER ====================
    
    def handle_client(self, client_socket: socket.socket, addr):
        """
        Handle individual client connection
        Implements: Multithreading, Connection Management
        """
        username = None
        ip_address = addr[0]
        
        try:
            # Step 1: Receive username
            username = client_socket.recv(1024).decode().strip()
            
            if not username:
                raise ValueError("Empty username received")
            
            # Step 2: Add client (check for duplicate username)
            if not self.add_client(username, client_socket):
                error_msg = "[ERROR] Username already taken. Please try another."
                client_socket.send(error_msg.encode())
                client_socket.close()
                logging.warning(f"Duplicate username rejected: {username}")
                return
            
            # Step 3: Send welcome message
            welcome = f"[SERVER] Welcome {username}! You are connected."
            client_socket.send(welcome.encode())
            
            # Step 4: Notify others
            self.broadcast(f"[SERVER] {username} joined the chat", sender=username)
            
            # Step 5: Send available commands
            commands = (
                "\n--- Available Commands ---\n"
                "/private <username> <message> - Send private message\n"
                "/users - List online users\n"
                "/help - Show this help\n"
                "Type normally for group chat\n"
                "--------------------------\n"
            )
            client_socket.send(commands.encode())
            
            # Step 6: Main message loop
            while True:
                try:
                    # Receive message with timeout for connection checking
                    client_socket.settimeout(300)  # 5 minute timeout
                    msg = client_socket.recv(1024).decode().strip()
                    
                    if not msg:
                        # Empty message = client disconnected
                        break
                    
                    # Parse and route message
                    self.route_message(username, msg)
                    
                except socket.timeout:
                    # Check if connection is still alive
                    try:
                        client_socket.send(b'')  # Ping
                    except:
                        logging.warning(f"Connection timeout for {username}")
                        break
                
                except ConnectionResetError:
                    logging.warning(f"Connection reset by {username}")
                    break
                
                except Exception as e:
                    logging.error(f"Error receiving from {username}: {e}")
                    break
        
        except Exception as e:
            logging.error(f"Error handling client {username or 'unknown'}: {e}")
        
        finally:
            # Cleanup: Always remove client on disconnect
            if username:
                self.remove_client(username, notify=True)
                logging.info(f"Connection closed for {username} from {ip_address}")
            else:
                try:
                    client_socket.close()
                except:
                    pass
    
    def route_message(self, username: str, message: str):
        """
        Route message based on type (command, private, or group)
        """
        # Command: /private
        if message.startswith("/private"):
            parts = message.split(" ", 2)
            if len(parts) >= 3:
                _, target, msg_content = parts
                self.private_message(target, msg_content, username)
            else:
                error = "[ERROR] Usage: /private <username> <message>"
                self.clients[username].send(error.encode())
        
        # Command: /users
        elif message == "/users":
            users = self.get_online_users()
            response = f"[SERVER] Online users ({len(users)}): {', '.join(users)}"
            self.clients[username].send(response.encode())
        
        # Command: /help
        elif message == "/help":
            help_text = (
                "\n--- Available Commands ---\n"
                "/private <username> <message> - Send private message\n"
                "/users - List online users\n"
                "/help - Show this help\n"
                "Type normally for group chat\n"
                "--------------------------\n"
            )
            self.clients[username].send(help_text.encode())
        
        # Group message
        else:
            group_msg = f"{username}: {message}"
            self.broadcast(group_msg, sender=username)
            logging.info(f"Group: {username}: {message[:50]}...")
    
    # ==================== SERVER LIFECYCLE ====================
    
    def start(self):
        """
        Start the server and accept connections
        Implements: Server-Client Architecture, Scalability, Wired+Wireless
        """
        # Create TCP socket
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Allow port reuse
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            # Bind to all interfaces (0.0.0.0)
            server_socket.bind((HOST, PORT))
            
            # Listen with backlog = MAX_CLIENTS (scalability)
            server_socket.listen(MAX_CLIENTS)
            
            # Server info
            logging.info("=" * 70)
            logging.info(f"[START] MULTI-CLIENT CHAT SERVER STARTED")
            logging.info(f"[NET] Network: Wired (Ethernet) + Wireless (Wi-Fi) Support")
            logging.info(f"[HOST] Listening on: {HOST}:{PORT}")
            logging.info(f"[CAPACITY] Maximum Clients: {MAX_CLIENTS}")
            logging.info(f"[ARCH] Architecture: Multi-threaded Server")
            logging.info(f"[TEAM] Team: Mousa & Shahd (Server Architecture)")
            logging.info("=" * 70)
            
            # Accept connections loop
            while True:
                try:
                    # Accept new connection
                    client_socket, addr = server_socket.accept()
                    
                    # Check if server is at capacity
                    if self.active_connections >= MAX_CLIENTS:
                        error = "[ERROR] Server is full. Please try again later."
                        client_socket.send(error.encode())
                        client_socket.close()
                        logging.warning(f"Connection rejected from {addr} - Server full")
                        continue
                    
                    # Create new thread for client (multithreading requirement)
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, addr),
                        daemon=True
                    )
                    client_thread.start()
                    
                    logging.info(f"New connection from {addr[0]}:{addr[1]}")
                
                except KeyboardInterrupt:
                    logging.info("\n[STOP] Server shutting down...")
                    break
                
                except Exception as e:
                    logging.error(f"Error accepting connection: {e}")
        
        except Exception as e:
            logging.error(f"Failed to start server: {e}")
        
        finally:
            # Cleanup
            self.shutdown(server_socket)
    
    def shutdown(self, server_socket):
        """Graceful server shutdown"""
        logging.info("Closing all client connections...")
        
        with self.clients_lock:
            for username, client_socket in list(self.clients.items()):
                try:
                    client_socket.send(b"[SERVER] Server is shutting down")
                    client_socket.close()
                except:
                    pass
        
        server_socket.close()
        
        # Statistics
        logging.info("=" * 70)
        logging.info(f"[STATS] SERVER STATISTICS")
        logging.info(f"Total connections handled: {self.connection_count}")
        logging.info(f"Max concurrent connections: {self.max_concurrent}")
        logging.info("=" * 70)
        logging.info("[OK] Server stopped successfully")


# ==================== MAIN ENTRY POINT ====================

if __name__ == "__main__":
    server = ChatServer()
    server.start()
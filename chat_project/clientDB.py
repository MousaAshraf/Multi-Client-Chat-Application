"""
Multi-Client Chat Client
Connects to the Multi-Client Chat Server

Usage:
1. Run server first: python server.py
2. Run client(s): python client.py
3. Enter username and start chatting

Commands:
- /private <username> <message> - Send private message
- /users - List online users
- /help - Show commands
- Type normally for group chat
"""

import socket
import threading
import sys

# Server Configuration
HOST = "127.0.0.1"  # Change to server IP for LAN testing
                     # Example: "192.168.1.100" for wired/wireless LAN
PORT = 5000

class ChatClient:
    def __init__(self):
        self.client_socket = None
        self.connected = False
        self.username = None
    
    def receive_messages(self):
        """
        Continuously receive messages from server
        Runs in separate thread
        """
        import sys
        while self.connected:
            try:
                # Use larger buffer to handle history messages
                message = self.client_socket.recv(8192).decode()
                if message:
                    # Clear the current input line if user is typing
                    # Then print the received message
                    sys.stdout.write('\r' + ' ' * 100 + '\r')  # Clear line
                    sys.stdout.write(message)
                    if not message.endswith('\n'):
                        sys.stdout.write('\n')
                    sys.stdout.flush()
                    
                    # Show input prompt again if still connected
                    if self.connected and self.username:
                        sys.stdout.write(f"{self.username}: ")
                        sys.stdout.flush()
                else:
                    # Empty message means server closed connection
                    print("\n[ERROR] Server closed the connection")
                    self.connected = False
                    break
            except ConnectionResetError:
                print("\n[ERROR] Connection lost to server")
                self.connected = False
                break
            except Exception as e:
                if self.connected:
                    print(f"\n[ERROR] Error receiving message: {e}")
                break
    
    def connect(self):
        """
        Connect to the chat server
        """
        try:
            # Create socket
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # Connect to server
            print(f"Connecting to {HOST}:{PORT}...")
            self.client_socket.connect((HOST, PORT))
            
            # Get username
            self.username = input("Enter username: ").strip()
            
            if not self.username:
                print("[ERROR] Username cannot be empty")
                return False
            
            # Send username to server first
            self.client_socket.send(self.username.encode())
            
            # Set connected flag and start receive thread
            # This will handle all incoming messages including welcome and history
            self.connected = True
            receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
            receive_thread.start()
            
            # Small delay to let receive thread start and receive initial messages
            import time
            time.sleep(0.3)
            
            return True
            
        except ConnectionRefusedError:
            print(f"[ERROR] Could not connect to server at {HOST}:{PORT}")
            print("Make sure the server is running!")
            return False
        except Exception as e:
            print(f"[ERROR] Connection error: {e}")
            return False
    
    def send_message(self, message: str):
        """
        Send message to server
        """
        try:
            if self.connected:
                self.client_socket.send(message.encode())
        except Exception as e:
            print(f"[ERROR] Failed to send message: {e}")
            self.connected = False
    
    def start(self):
        """
        Start the chat client
        """
        print("=" * 60)
        print("MULTI-CLIENT CHAT APPLICATION")
        print("=" * 60)
        
        # Connect to server
        if not self.connect():
            return
        
        print(f"\n[OK] Connected! Type your messages below.")
        print("Type '/help' for commands or 'quit' to exit\n")
        
        # Main input loop
        try:
            while self.connected:
                # Get user input
                message = input(f"{self.username}: ").strip()
                
                # Handle quit command
                if message.lower() in ['quit', 'exit', '/quit', '/exit']:
                    print("Disconnecting...")
                    break
                
                # Send non-empty messages
                if message:
                    self.send_message(message)
        
        except KeyboardInterrupt:
            print("\n\nDisconnecting...")
        
        finally:
            self.disconnect()
    
    def disconnect(self):
        """
        Disconnect from server
        """
        self.connected = False
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
        print("[OK] Disconnected from server")


# ==================== MAIN ENTRY POINT ====================

if __name__ == "__main__":
    client = ChatClient()
    client.start()
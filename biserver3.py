import asyncio
import os
import sys
import aioconsole
from collections import defaultdict

HOST = '0.0.0.0'  # Listen on all interfaces
PORT = 12345
BUFFER_SIZE = 65536

# Dictionary to store active clients {username: (reader, writer, client_id, vector_clock)}
active_clients = {}

class VectorClock:
    def __init__(self, client_id):
        self.clock = defaultdict(int)
        self.client_id = client_id

    def increment(self):
        self.clock[self.client_id] += 1
        print(f"VectorClock after increment: {self}")

    def update(self, other_clock):
        for client, timestamp in other_clock.items():
            self.clock[client] = max(self.clock[client], timestamp)
        print(f"VectorClock after update: {self}")

    def get_clock(self):
        return dict(self.clock)

    def __str__(self):
        return str(dict(self.clock))

async def handle_client(reader, writer):
    """Handles communication with a connected client asynchronously."""
    addr = writer.get_extra_info('peername')
    client_id = f"{addr[0]}:{addr[1]}"
    print(f"New connection from {client_id}")
    
    # Wait for client to send their username
    data = await reader.readline()
    if not data:
        print(f"Client {client_id} disconnected before sending username")
        return
    
    message = data.decode().strip()
    if message.startswith("NAME:"):
        username = message[5:]
        # Check if username is already taken
        if username in active_clients:
            print(f"Username '{username}' already taken. Connection rejected.")
            writer.write(b"ERROR: Username already taken\n")
            await writer.drain()
            writer.close()
            await writer.wait_closed()
            return
        
        print(f"Client {client_id} identified as '{username}'")
        vector_clock = VectorClock(client_id)
        active_clients[username] = (reader, writer, client_id, vector_clock)
    else:
        print(f"Client {client_id} did not properly identify. Connection rejected.")
        writer.close()
        await writer.wait_closed()
        return

    async def send_file(filename, target_username):
        """Send a file to the specific client in chunks."""
        if target_username not in active_clients:
            print(f"Client '{target_username}' is no longer connected")
            return
            
        _, target_writer, _, target_clock = active_clients[target_username]
        
        if os.path.exists(filename):
            target_clock.increment()
            target_writer.write(f"FILE:{filename}:{target_clock.get_clock()}".encode() + b'\n')
            await target_writer.drain()
            
            with open(filename, "rb") as f:
                while chunk := f.read(BUFFER_SIZE):
                    target_writer.write(chunk)
                    await target_writer.drain()
            
            # Signal end of file with special marker
            target_writer.write(b'ENDOFFILE\n')
            await target_writer.drain()
            
            print(f"Sent file '{filename}' to '{target_username}'")
        else:
            print("File not found.")

    async def list_clients():
        """Display a list of all connected clients."""
        if not active_clients:
            print("No clients connected.")
            return
            
        print("\nConnected clients:")
        for i, (name, _) in enumerate(active_clients.items(), 1):
            print(f"{i}. {name}")
        print()

    async def sender():
        """Handle sending messages to clients."""
        try:
            while True:
                action = await aioconsole.ainput(
                    "\nActions:\n1. List clients\n2. Send message\n3. Send file\n4. Disconnect client\n5. Exit\nChoose action (1-5): "
                )
                
                if action == "1":  # List clients
                    await list_clients()
                    continue
                
                elif action == "2" or action == "3":  # Send message or file
                    # First list available clients
                    await list_clients()
                    if not active_clients:
                        continue
                        
                    targets = await aioconsole.ainput(
                        "Enter client username(s) to send to (separate multiple with commas, or type 'all'): "
                    )
                    
                    # Determine target clients
                    target_usernames = []
                    if targets.lower() == 'all':
                        target_usernames = list(active_clients.keys())
                    else:
                        target_usernames = [name.strip() for name in targets.split(',')]
                        # Filter out invalid usernames
                        target_usernames = [name for name in target_usernames if name in active_clients]
                    
                    if not target_usernames:
                        print("No valid clients selected.")
                        continue
                    
                    if action == "2":  # Send message
                        message = await aioconsole.ainput("Enter message: ")
                        for username in target_usernames:
                            if username in active_clients:
                                _, target_writer, _, target_clock = active_clients[username]
                                target_clock.increment()
                                target_writer.write(f"MSG:{message}:{target_clock.get_clock()}".encode() + b'\n')
                                await target_writer.drain()
                                print(f"Message sent to '{username}'")
                            
                    elif action == "3":  # Send file
                        filename = await aioconsole.ainput("Enter filename to send: ")
                        for username in target_usernames:
                            if username in active_clients:
                                await send_file(filename, username)
                
                elif action == "4":  # Disconnect client
                    await list_clients()
                    if not active_clients:
                        continue
                        
                    username = await aioconsole.ainput("Enter username to disconnect: ")
                    if username in active_clients:
                        _, target_writer, _, _ = active_clients[username]
                        target_writer.write(b"Server closed the connection\n")
                        await target_writer.drain()
                        print(f"Disconnected '{username}'")
                    else:
                        print(f"Client '{username}' not found")
                
                elif action == "5":  # Exit server
                    print("Shutting down server...")
                    # Notify all clients
                    for name, (_, client_writer, _, _) in active_clients.items():
                        try:
                            client_writer.write(b"Server shutting down\n")
                            await client_writer.drain()
                        except:
                            pass
                    break
                
                else:
                    print("Invalid option. Please choose 1-5.")
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Error in sender: {e}")

    async def receiver():
        """Handle receiving messages from this client."""
        try:
            while True:
                data = await reader.readline()
                if not data:
                    username = next((name for name, (r, w, _, _) in active_clients.items() if r is reader), None)
                    if username:
                        print(f"Client '{username}' disconnected")
                        del active_clients[username]
                    break
                
                message = data.decode().strip()
                
                if message.startswith("FILE:"):
                    parts = message.split(':', 2)
                    filename = parts[1]
                    sender_clock = eval(parts[2])
                    username = next((name for name, (r, w, _, _) in active_clients.items() if r is reader), None)
                    print(f"\nReceiving file from '{username}': {filename}")
                    with open("received_" + filename, "wb") as f:
                        while True:
                            chunk = await reader.readuntil(b'ENDOFFILE\n')
                            if chunk.endswith(b'ENDOFFILE\n'):
                                f.write(chunk[:-10])  # Remove the ENDOFFILE marker
                                break
                            f.write(chunk)
                    print(f"Received file: received_{filename} from '{username}'")
                    active_clients[username][3].update(sender_clock)
                
                elif message.startswith("MSG:"):
                    parts = message.split(':', 2)
                    msg = parts[1]
                    sender_clock = eval(parts[2])
                    username = next((name for name, (r, w, _, _) in active_clients.items() if r is reader), None)
                    print(f"\n{username}: {msg}")
                    active_clients[username][3].update(sender_clock)
        
        except asyncio.CancelledError:
            pass
        except Exception as e:
            username = next((name for name, (r, w, _, _) in active_clients.items() if r is reader), None)
            print(f"Error in receiver for '{username}': {e}")
            if username in active_clients:
                del active_clients[username]

    # Create tasks for sending and receiving
    send_task = asyncio.create_task(sender())
    receive_task = asyncio.create_task(receiver())
    
    try:
        # Wait for either task to finish
        await asyncio.gather(send_task, receive_task, return_exceptions=True)
    finally:
        send_task.cancel()
        receive_task.cancel()
        username = next((name for name, (r, w, _, _) in active_clients.items() if r is reader), None)
        if username in active_clients:
            del active_clients[username]
        writer.close()
        await writer.wait_closed()
        print(f"Connection with '{username}' closed")

async def main():
    """Main function to start the asynchronous server."""
    server = await asyncio.start_server(handle_client, HOST, PORT)
    addr = server.sockets[0].getsockname()
    print(f"Server running on {addr}...")

    async with server:
        await server.serve_forever()

# Run the server
if __name__ == "__main__":
    asyncio.run(main())
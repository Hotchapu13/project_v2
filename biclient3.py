import asyncio
import os
import sys
import aioconsole
from collections import defaultdict

SERVER_IP = '172.16.13.89'
PORT = 12345
BUFFER_SIZE = 65536

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

async def send_file(writer, filename, vector_clock):
    """Send a file to the server in chunks."""
    if os.path.exists(filename):
        vector_clock.increment()
        writer.write(f"FILE:{filename}:{vector_clock.get_clock()}".encode() + b'\n')
        await writer.drain()
        
        with open(filename, "rb") as f:
            while chunk := f.read(BUFFER_SIZE):
                writer.write(chunk)
                await writer.drain()
        
        # Signal end of file with special marker
        writer.write(b'ENDOFFILE\n')
        await writer.drain()
        
        print(f"Sent file: {filename}")
    else:
        print("File not found.")

async def sender(writer, vector_clock):
    """Handle sending messages and files to the server."""
    try:
        while True:
            message = await aioconsole.ainput("Enter message (or 'send file' to transfer a file, 'exit' to quit): ")
            
            if message.lower() == "send file":
                filename = await aioconsole.ainput("Enter filename to send: ")
                await send_file(writer, filename, vector_clock)
            else:
                vector_clock.increment()
                writer.write(f"MSG:{message}:{vector_clock.get_clock()}".encode() + b'\n')
                await writer.drain()

            if message.lower() == "exit":
                break

    except asyncio.CancelledError:
        pass

async def receiver(reader, vector_clock):
    """Handle receiving messages and files from the server."""
    try:
        while True:
            data = await reader.readline()
            if not data:
                print("Connection closed by server")
                break
                
            message = data.decode().strip()
            
            if message.startswith("FILE:"):
                parts = message.split(':', 2)
                filename = parts[1]
                sender_clock = eval(parts[2])
                print(f"\nReceiving file: {filename}")
                with open("received_" + filename, "wb") as f:
                    while True:
                        chunk = await reader.readuntil(b'ENDOFFILE\n')
                        if chunk.endswith(b'ENDOFFILE\n'):
                            f.write(chunk[:-10])  # Remove the ENDOFFILE marker
                            break
                        f.write(chunk)
                print(f"Received file: received_{filename}")
                vector_clock.update(sender_clock)
            
            elif message.startswith("MSG:"):
                parts = message.split(':', 2)
                msg = parts[1]
                sender_clock = eval(parts[2])
                print(f"\nServer: {msg}")
                vector_clock.update(sender_clock)
            
            elif message.startswith("ERROR:"):
                print(f"\nServer Error: {message[6:]}")
                return  # Exit if there's an error
                
            elif message == "Server shutting down" or message == "Server closed the connection":
                print(f"\n{message}")
                return  # Exit if server is shutting down
                
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"Error in receiver: {e}")

async def client():
    """Run the client with separate tasks for sending and receiving."""
    try:
        reader, writer = await asyncio.open_connection(SERVER_IP, PORT)
        print(f"Connected to {SERVER_IP}:{PORT}")
        
        # First send a username to the server
        username = await aioconsole.ainput("Enter your username: ")
        writer.write(f"NAME:{username}".encode() + b'\n')
        await writer.drain()
        
        # Initialize vector clock
        vector_clock = VectorClock(username)
        
        # Wait briefly to see if there's an error response
        await asyncio.sleep(0.5)
        
        send_task = asyncio.create_task(sender(writer, vector_clock))
        receive_task = asyncio.create_task(receiver(reader, vector_clock))

        try:
            # Wait for either task to finish (like when the user types 'exit')
            await asyncio.gather(send_task, receive_task, return_exceptions=True)
        finally:
            send_task.cancel()
            receive_task.cancel()
            writer.close()
            await writer.wait_closed()
            print("Connection closed")
            
    except ConnectionRefusedError:
        print(f"Error: Could not connect to server at {SERVER_IP}:{PORT}")
    except Exception as e:
        print(f"Error connecting: {e}")

# Run the client
if __name__ == "__main__":
    asyncio.run(client())
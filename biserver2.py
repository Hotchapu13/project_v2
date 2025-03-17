import asyncio
import os
import sys
import aioconsole

HOST = '0.0.0.0'  # Listen on all interfaces
PORT = 12345
BUFFER_SIZE = 65536

async def handle_client(reader, writer):
    """Handles communication with a connected client asynchronously."""
    addr = writer.get_extra_info('peername')
    print(f"New connection from {addr}")
    client_id = f"{addr[0]}:{addr[1]}"

    async def send_file(filename):
        """Send a file to the client in chunks."""
        if os.path.exists(filename):
            writer.write(f"FILE:{filename}".encode() + b'\n')
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

    async def sender():
        """Handle sending messages to this client."""
        try:
            while True:
                message = await aioconsole.ainput(f"[To {client_id}] Enter message (or 'send file' to transfer file, 'exit' to disconnect client): ")
                
                if message.lower() == "send file":
                    filename = await aioconsole.ainput("Enter filename to send: ")
                    await send_file(filename)
                elif message.lower() == "exit":
                    writer.write(b"Server closed the connection\n")
                    await writer.drain()
                    break
                else:
                    writer.write(f"MSG:{message}".encode() + b'\n')
                    await writer.drain()
        except asyncio.CancelledError:
            pass

    async def receiver():
        """Handle receiving messages from this client."""
        try:
            while True:
                data = await reader.readline()
                if not data:
                    print(f"Client {client_id} disconnected")
                    break
                
                message = data.decode().strip()
                
                if message.startswith("FILE:"):
                    filename = message[5:]
                    print(f"\nReceiving file from {client_id}: {filename}")
                    with open("received_" + filename, "wb") as f:
                        while True:
                            chunk = await reader.readuntil(b'ENDOFFILE\n')
                            if chunk.endswith(b'ENDOFFILE\n'):
                                f.write(chunk[:-10])  # Remove the ENDOFFILE marker
                                break
                            f.write(chunk)
                    print(f"Received file: received_{filename}")
                
                elif message.startswith("MSG:"):
                    print(f"\n{client_id}: {message[4:]}")
        
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Error in receiver for {client_id}: {e}")

    # Create tasks for sending and receiving
    send_task = asyncio.create_task(sender())
    receive_task = asyncio.create_task(receiver())
    
    try:
        # Wait for either task to finish
        await asyncio.gather(send_task, receive_task, return_exceptions=True)
    finally:
        send_task.cancel()
        receive_task.cancel()
        writer.close()
        await writer.wait_closed()
        print(f"Connection with {client_id} closed")

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
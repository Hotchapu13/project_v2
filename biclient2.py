import asyncio
import os
import sys
import aioconsole

SERVER_IP = '192.168.242.58'
PORT = 12345
BUFFER_SIZE = 65536

async def send_file(writer, filename):
    """Send a file to the server in chunks."""
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

async def sender(writer):
    """Handle sending messages and files to the server."""
    try:
        while True:
            message = await aioconsole.ainput("Enter message (or 'send file' to transfer a file, 'exit' to quit): ")
            
            if message.lower() == "send file":
                filename = await aioconsole.ainput("Enter filename to send: ")
                await send_file(writer, filename)
            else:
                writer.write(f"MSG:{message}".encode() + b'\n')
                await writer.drain()

            if message.lower() == "exit":
                break

    except asyncio.CancelledError:
        pass

async def receiver(reader):
    """Handle receiving messages and files from the server."""
    try:
        while True:
            data = await reader.readline()
            if not data:
                print("Connection closed by server")
                break
                
            message = data.decode().strip()
            
            if message.startswith("FILE:"):
                filename = message[5:]
                print(f"\nReceiving file: {filename}")
                with open("received_" + filename, "wb") as f:
                    while True:
                        chunk = await reader.readuntil(b'ENDOFFILE\n')
                        if chunk.endswith(b'ENDOFFILE\n'):
                            f.write(chunk[:-10])  # Remove the ENDOFFILE marker
                            break
                        f.write(chunk)
                print(f"Received file: received_{filename}")
            
            elif message.startswith("MSG:"):
                print(f"\nServer: {message[4:]}")
            
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"Error in receiver: {e}")

async def client():
    """Run the client with separate tasks for sending and receiving."""
    reader, writer = await asyncio.open_connection(SERVER_IP, PORT)
    print(f"Connected to {SERVER_IP}:{PORT}")

    send_task = asyncio.create_task(sender(writer))
    receive_task = asyncio.create_task(receiver(reader))

    try:
        # Wait for either task to finish (like when the user types 'exit')
        await asyncio.gather(send_task, receive_task, return_exceptions=True)
    finally:
        send_task.cancel()
        receive_task.cancel()
        writer.close()
        await writer.wait_closed()
        print("Connection closed")


# Run the client
if __name__ == "__main__":
    asyncio.run(client())
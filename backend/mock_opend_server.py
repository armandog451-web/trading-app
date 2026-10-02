import asyncio
import logging

logger = logging.getLogger(__name__)

async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """Send synthetic TICK messages for AAPL and TSLA every second.
    The format matches the expectation of MoomooOpenDConnection:
    TICK|SYMBOL|bid|ask|bidSize|askSize|...\n"""
    symbols = ["AAPL", "TSLA"]
    try:
        while True:
            for sym in symbols:
                bid = 150.0
                ask = 150.5
                bid_sz = 100
                ask_sz = 120
                line = f"TICK|{sym}|{bid}|{ask}|{bid_sz}|{ask_sz}\n"
                writer.write(line.encode())
                await writer.drain()
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        logger.info("Mock OpenD server client handler cancelled")
    except Exception as e:
        logger.exception(f"Mock OpenD server error: {e}")
    # Keep connection open; server will close when stopped

async def main():
    server = await asyncio.start_server(handle_client, "127.0.0.1", 11111)
    addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets)
    logger.info(f"Mock OpenD server listening on {addrs}")
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())

import typer
import uvicorn
import logging
import os
from typing import Optional

app = typer.Typer()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.command()
def start(
    host: str = "0.0.0.0", 
    port: int = 8000, 
    reload: bool = True,
    log_level: str = "info"
):
    """Start the Xiaohongshu Content Extractor API server"""
    logger.info(f"Starting server on {host}:{port}")
    
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["access"]["fmt"] = "%(asctime)s - %(levelname)s - %(message)s"
    
    uvicorn.run(
        "api:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level.lower(),
        log_config=log_config
    )

@app.command()
def get_ip():
    """Get your local IP address to configure Shortcuts"""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    
    logger.info(f"Your local IP address is: {ip}")
    logger.info(f"Use this in Shortcuts with: http://{ip}:8000/extract")
    return ip

if __name__ == "__main__":
    app() 
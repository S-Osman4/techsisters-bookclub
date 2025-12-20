#!/usr/bin/env python3
"""
TechSisters Book Club - FastAPI Application Runner

Usage:
    python run.py              # Development mode (auto-reload)
    python run.py --prod       # Production mode (multiple workers)
"""

import uvicorn
import sys

if __name__ == "__main__":
    # Check if production mode
    is_production = "--prod" in sys.argv or "-p" in sys.argv
    
    if is_production:
        print("🚀 Starting in PRODUCTION mode...")
        # Production settings
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            workers=4,  # Multiple workers for better performance
            log_level="info",
            timeout_keep_alive=30,  # Close idle connections after 30 seconds
            limit_concurrency=100,  # Limit to 100 concurrent connections
            limit_max_requests=5000
        )
    else:
        print("🔧 Starting in DEVELOPMENT mode...")
        # Development settings
        uvicorn.run(
            "app.main:app",
            host="127.0.0.1",
            port=8000,
            reload=True,  # Auto-reload on code changes
            log_level="debug",
            timeout_keep_alive=5,     # Close idle connections after 5 seconds
            limit_concurrency=10,     # Limit to 10 concurrent connections
            limit_max_requests=100,   # Restart after 100 requests (prevents leaks)
            reload_dirs=["app"], 
        )
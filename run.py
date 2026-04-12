# run.py
"""
Application runner.

Usage:
    python run.py           # development (auto-reload)
    python run.py --prod    # production (multiple workers)
"""
import sys
import uvicorn


def main() -> None:
    is_prod = "--prod" in sys.argv or "-p" in sys.argv

    if is_prod:
        print("Starting in PRODUCTION mode...")
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            workers=4,
            log_level="info",
            timeout_keep_alive=30,
            limit_concurrency=100,
        )
    else:
        print("Starting in DEVELOPMENT mode...")
        uvicorn.run(
            "app.main:app",
            host="127.0.0.1",
            port=8000,
            reload=True,
            reload_dirs=["app"],
            log_level="debug",
        )


if __name__ == "__main__":
    main()
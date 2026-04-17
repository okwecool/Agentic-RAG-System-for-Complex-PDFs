"""Run the lightweight frontend application."""

from __future__ import annotations

import argparse
import logging

from src.config.settings import get_settings
from src.frontend.app import create_frontend_app

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the lightweight frontend.")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()

    settings = get_settings()
    app = create_frontend_app(settings)
    queued_app = app.queue(default_concurrency_limit=2)
    launch_kwargs = {
        "server_name": args.host or settings.frontend_host,
        "server_port": args.port or settings.frontend_port,
    }
    try:
        queued_app.launch(show_api=False, **launch_kwargs)
    except TypeError:
        logger.info("frontend.run falling back to Gradio launch() without show_api for compatibility.")
        queued_app.launch(**launch_kwargs)


if __name__ == "__main__":
    main()

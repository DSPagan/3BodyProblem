#!/usr/bin/env python3
# /// script
# dependencies = ["numpy"]
# ///
"""Entry point for the three-body simulator.

Runs both as a desktop app (``python main.py``) and as the entry point for the
WebAssembly build produced by pygbag. pygbag needs an async main loop and the
heavy dependencies (numpy) declared up front — hence the PEP 723 header above and
the top-level import below.
"""
import asyncio

import numpy  # noqa: F401  -- imported here so the web build bundles it

from threebody.app import App

if __name__ == "__main__":
    asyncio.run(App().run_async())

#!/usr/bin/env python3
"""Entry point for the three-body simulator.

Runs both as a desktop app (``python main.py``) and as the entry point for the
WebAssembly build produced by pygbag. pygbag needs an async main loop, which is
why the app loop is async (see ``threebody.app.App.run_async``). The project has
no compiled dependencies, so the browser build is small and needs no extra setup.
"""
import asyncio

import pygame  # noqa: F401  -- imported at top level so the web (pygbag) build fully sets it up

from threebody.app import App

if __name__ == "__main__":
    asyncio.run(App().run_async())

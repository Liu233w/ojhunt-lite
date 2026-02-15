#!/usr/bin/env python3
"""
Development server entry point for OJHunt Lite web application.
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("web.app:app", host="127.0.0.1", port=8080, reload=True)

from fastapi import FastAPI
from fastapi.responses import FileResponse
from openpuc_scrapers.server.app import create_app
from openpuc_scrapers.server.routes import register_routes

# Create the FastAPI application
app = create_app()

# Register all routes
register_routes(app)

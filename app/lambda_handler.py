"""
This file wraps the FastAPI app with Mangum to make it compatible with AWS Lambda.
"""
from mangum import Mangum

from app.main import app

handler = Mangum(app)

# wsgi.py
import os

from app import create_app
from app.config import DevelopmentConfig, ProductionConfig

config_class = (
    ProductionConfig
    if os.environ.get("FLASK_ENV") == "production"
    else DevelopmentConfig
)
app = create_app(config_class=config_class)

if __name__ == "__main__":
    # Development server only (not for production - change later)
    app.run(debug=True, host="0.0.0.0", port=5000)

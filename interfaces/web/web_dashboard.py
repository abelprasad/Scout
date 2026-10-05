# Thin entry point: builds the generic dashboard app for the active mission.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.interfaces.dashboard import create_dashboard_app

app = create_dashboard_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

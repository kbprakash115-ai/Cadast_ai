"""
Root Launcher for CadastralAI Streamlit Dashboard.
Allows running: `streamlit run app.py` from the project root.
"""

import os
import sys

# Ensure root project directory is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cadastral_ai.app import main

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Text-to-Speech Tool - Main Entry Point
"""
import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from gui import main

if __name__ == "__main__":
    main()

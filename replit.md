# WebM Metadata Editor

## Overview
A web application for editing WebM video file metadata, specifically the EBML Duration tag. Built with Python Flask backend and vanilla JavaScript frontend.

## Project Purpose
This application allows users to upload WebM video files and modify the duration metadata by directly manipulating the binary EBML structure without using external parsing libraries.

## Recent Changes
- **November 11, 2025**: Initial project setup
  - Created Flask backend with binary EBML processing
  - Implemented frontend with drag-and-drop interface
  - Dark-themed UI with centered 600px layout
  - Fixed unit conversion: milliseconds input converted to seconds for EBML spec
  - Added EBML size byte (0x88) validation for robust error handling

## Project Architecture

### Backend (Python Flask)
- **app.py**: Main Flask application
  - `/` - Serves the frontend HTML page
  - `/upload` - POST endpoint for file processing
  - Binary EBML parser that searches for Duration tag (0x4489)
  - Validates EBML size byte (0x88) before modification
  - Converts milliseconds to seconds (EBML Duration spec requirement)
  - Modifies 8-byte IEEE 754 float64 value with proper unit conversion
  - Returns modified file for download

### Frontend
- **templates/index.html**: Main HTML structure with drag-and-drop zone
- **static/style.css**: Dark theme styling with centered layout
- **static/script.js**: File validation, upload handling, download trigger

## Technical Details
- File size limit: 10MB
- Supported format: .webm only
- Duration input: milliseconds (converted to seconds for EBML spec compliance)
- Duration stored as IEEE 754 double-precision float (8 bytes) in EBML format
- Direct binary search without external EBML libraries
- Uses struct module for float64 packing (big-endian)
- EBML size byte validation (0x88) prevents corruption of malformed files

## Dependencies
- Python 3.11
- Flask (web framework)
- struct (binary processing, built-in)
- werkzeug (file handling, comes with Flask)

## Workflow
Server runs on port 5000 with Flask development server bound to 0.0.0.0

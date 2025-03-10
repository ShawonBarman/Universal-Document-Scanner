# Universal Document Scanner

## Overview
A powerful web application for extracting document information using Google Document AI. Seamlessly scan driver's licenses, IDs, and official documents via camera or file upload with an intuitive interface.

## Features
- 📸 Multiple document upload methods
  - Camera capture
  - File upload
  - Drag & drop support
- 🔍 Supports multiple document types
  - Driver's licenses
  - ID cards
  - Official documents
- 🖥️ Responsive web interface
- 🔒 Secure Google Document AI processing

## Prerequisites
- Python 3.8+
- Google Cloud Project
- Document AI Processor

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/ShawonBarman/Universal-Document-Scanner.git
cd Universal-Document-Scanner
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
1. Create a `.env` file
2. Add your Google Cloud credentials
3. Set up Document AI processor details

## Usage
```bash
python app.py
```
Open `http://localhost:5005` in your browser

## Configuration
Refer to `.env.example` for required environment variables

## Contributing
1. Fork the repository
2. Create your feature branch
3. Commit changes
4. Push to the branch
5. Create a Pull Request

## Support
Open an issue in the GitHub repository

## Technologies
- Flask
- Google Document AI
- Python
- HTML5
- Tailwind CSS

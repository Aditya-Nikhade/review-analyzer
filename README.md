# Customer Review Analysis (CRA)

A Python-based application for analyzing customer reviews using natural language processing.

## Features

- Review analysis and sentiment detection
- Docker containerization support
- Web interface for review submission and analysis
- Status checking functionality

## Setup

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

### Using Docker
```bash
docker-compose up --build
```

### Without Docker
```bash
python app.py
```

## Project Structure

- `app.py` - Main application file
- `pipeline.py` - NLP processing pipeline
- `check_status.py` - Status checking functionality
- `templates/` - HTML templates
- `Dockerfile` - Docker configuration
- `docker-compose.yml` - Docker Compose configuration

## Requirements

See `requirements.txt` for the complete list of dependencies.

## License

MIT License 
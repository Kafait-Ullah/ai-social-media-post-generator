# Social Media Post Generator

This project uses Streamlit and LangGraph to generate social media posts.

## Project Structure

- `main.py`: Streamlit UI and main application logic.
- `requirements.txt`: Python dependencies.
- `.gitignore`: Specifies intentionally untracked files to ignore.
- `.env`: Environment variables (e.g., API keys).
- `modules/`:
    - `models.py`: Pydantic data models for post generation.
    - `generator.py`: LangGraph nodes and graph logic for post generation.
    - `validator.py`: Function to validate generated posts.

# Discount Calculator - Setup Guide

## Cloning the Repository

Clone the repository:
git clone https://github.com/yourusername/discount-calculator.git
cd discount-calculator



Backend Setup (Python/FastAPI)
Create and activate virtual environment:
Create virtual environment
python -m venv venv

Activate virtual environment
On macOS/Linux:
source venv/bin/activate
On Windows:
venv\Scripts\activate

Install dependencies:
pip install -r requirements.txt

Start the backend server:
uvicorn main:app --reload

The backend will run at: http://localhost:8000


# Comments API

A Flask-based comment system API that allows users to create sections, post comments, reply to comments, and manage user authentication.

## Features

- User authentication (login, signup, logout)
- Create sections for organizing comments
- Post comments to sections
- Reply to comments
- Like comments
- Spam detection and content categorization
- Dashboard for comment management

## Tech Stack

- Flask
- SQLite
- Flask-CORS
- Werkzeug

## Setup

1. Clone the repository
2. Create a virtual environment: `python -m venv myenv`
3. Activate the virtual environment:
   - Windows: `myenv\Scripts\activate`
   - Linux/Mac: `source myenv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Run the application: `python app.py`

## API Endpoints

- `/api/register` - Register a new user
- `/api/login` - User login
- `/api/sections` - Create a new section
- `/api/sections/<section_id>/comments` - Get or post comments for a section
- `/api/comments/<comment_id>/replies` - Add replies to a comment
- `/api/comments/<comment_id>/like` - Like a comment
- `/api/delete-comment/<comment_id>` - Delete a comment
- `/api/all-comments` - Get all comments 
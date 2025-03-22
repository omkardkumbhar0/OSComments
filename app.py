from flask import Flask, request, jsonify, render_template, url_for, session, redirect
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import json
from datetime import datetime, timedelta
import secrets
from functools import wraps
import re
from collections import defaultdict
from threading import Lock
from better_profanity import profanity  # Install with: pip install profanity-filter
import os

app = Flask(__name__, static_url_path='/static', static_folder='static')
app.secret_key = secrets.token_hex(16)  # For session management
# Update CORS to allow requests from any origin
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/signup')
def signup_page():
    return render_template('signup.html')

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    return redirect(url_for('login_page'))

# Enhanced Database setup function
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT UNIQUE,
                    email TEXT UNIQUE,
                    password_hash TEXT,
                    api_key TEXT UNIQUE,
                    created_at TEXT)''')
    
    # Comment sections table
    c.execute('''CREATE TABLE IF NOT EXISTS comment_sections (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    section_name TEXT,
                    created_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    # Comments table with updated schema
    c.execute('''CREATE TABLE IF NOT EXISTS comments (
                    id INTEGER PRIMARY KEY,
                    section_id INTEGER,
                    blog_url TEXT,
                    username TEXT,
                    comment TEXT,
                    timestamp TEXT,
                    likes_count INTEGER DEFAULT 0,
                    parent_id INTEGER DEFAULT NULL,
                    is_owner BOOLEAN DEFAULT 0,
                    user_ip TEXT,
                    spam_score INTEGER DEFAULT 0,
                    moderation_status TEXT DEFAULT 'approved',
                    FOREIGN KEY (parent_id) REFERENCES comments (id),
                    FOREIGN KEY (section_id) REFERENCES comment_sections (id))''')
    
    # Likes table
    c.execute('''CREATE TABLE IF NOT EXISTS likes (
                    id INTEGER PRIMARY KEY,
                    comment_id INTEGER,
                    user_ip TEXT,
                    created_at TEXT,
                    FOREIGN KEY (comment_id) REFERENCES comments (id))''')
    
    # Create indexes for better performance
    c.execute('CREATE INDEX IF NOT EXISTS idx_comments_section ON comments(section_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_comments_parent ON comments(parent_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_likes_comment ON likes(comment_id)')
    
    conn.commit()
    conn.close()

# Initialize the database
init_db()

# User registration endpoint
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    if not all([username, email, password]):
        return jsonify({"error": "Missing required fields"}), 400
    
    password_hash = generate_password_hash(password)
    api_key = secrets.token_urlsafe(32)
    
    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('INSERT INTO users (username, email, password_hash, api_key, created_at) VALUES (?, ?, ?, ?, ?)',
                 (username, email, password_hash, api_key, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        conn.close()
        return jsonify({"message": "Registration successful", "api_key": api_key})
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username or email already exists"}), 409

# User login endpoint
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT id, password_hash, api_key FROM users WHERE username = ?', (username,))
    user = c.fetchone()
    conn.close()
    
    if user and check_password_hash(user[1], password):
        session['user_id'] = user[0]
        return jsonify({"message": "Login successful", "api_key": user[2]})
    return jsonify({"error": "Invalid credentials"}), 401

# Create new comment section
@app.route('/api/sections', methods=['POST'])
def create_section():
    if 'user_id' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    data = request.get_json()
    section_name = data.get('section_name')
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('INSERT INTO comment_sections (user_id, section_name, created_at) VALUES (?, ?, ?)',
             (session['user_id'], section_name, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    section_id = c.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Section created", "section_id": section_id})

# Rate limiting storage
rate_limits = defaultdict(list)
rate_limit_lock = Lock()

def check_spam(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        user_ip = request.remote_addr
        current_time = datetime.now()
        
        with rate_limit_lock:
            # Clean up old entries
            rate_limits[user_ip] = [t for t in rate_limits[user_ip] 
                                  if t > current_time - timedelta(hours=1)]
            
            # Check rate limits
            if len(rate_limits[user_ip]) >= 10:  # Max 10 comments per hour
                return jsonify({'error': 'Too many comments. Please try again later.'}), 429
            
            # Add current timestamp
            rate_limits[user_ip].append(current_time)
        
        return func(*args, **kwargs)
    return wrapper

def is_spam_content(text, username):
    # Initialize spam score
    spam_score = 0
    spam_reasons = []

    # Check for common spam patterns
    spam_patterns = {
        r'https?://': ('Too many URLs', 2),
        r'(.)\1{4,}': ('Repeated characters', 1),
        r'([^\w\s])\1{2,}': ('Excessive punctuation', 1),
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b': ('Email address detected', 2)
    }
    
    # Count URLs
    url_count = len(re.findall(r'https?://', text))
    if url_count > 2:
        spam_score += 2
        spam_reasons.append('Too many URLs (max 2 allowed)')
    
    # Check patterns
    for pattern, (reason, score) in spam_patterns.items():
        if re.search(pattern, text, re.IGNORECASE):
            spam_score += score
            spam_reasons.append(reason)
    
    # Additional checks
    word_count = len(text.split())
    if word_count < 2:
        spam_score += 1
        spam_reasons.append('Message too short')
        
    if len(set(text.lower())) < 3:
        spam_score += 1
        spam_reasons.append('Too few unique characters')
    
    # Consider comment spam if score is too high
    is_spam = spam_score >= 3
    return is_spam, spam_reasons

def categorize_comment(comment_text):
    """Categorize comments based on sentiment and content"""
    # Initialize scores
    positive_words = {'great', 'good', 'awesome', 'excellent', 'thanks', 'helpful', 'love', 'perfect', 'amazing'}
    negative_words = {'bad', 'poor', 'terrible', 'hate', 'awful', 'worst', 'useless', 'horrible'}
    improvement_indicators = {'should', 'could', 'would be better', 'suggest', 'improve', 'consider', 'maybe add'}
    
    words = set(comment_text.lower().split())
    
    # Check for matches
    positive_matches = len(words.intersection(positive_words))
    negative_matches = len(words.intersection(negative_words))
    improvement_matches = any(indicator in comment_text.lower() for indicator in improvement_indicators)
    
    if improvement_matches:
        return 'improvement'
    elif positive_matches > negative_matches:
        return 'good'
    elif negative_matches > positive_matches:
        return 'bad'
    return 'neutral'

# Update the add_comment endpoint to use the new spam detection
@app.route('/api/sections/<int:section_id>/comments', methods=['POST'])
@check_spam
def add_comment(section_id):
    data = request.json
    user_ip = request.remote_addr
    
    # Basic validation
    if not data.get('comment') or not data.get('username'):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Length limits
    if len(data['comment']) > 1000:
        return jsonify({'error': 'Comment too long (max 1000 characters)'}), 400
    if len(data['username']) > 50:
        return jsonify({'error': 'Username too long (max 50 characters)'}), 400
    
    # Check for spam content
    is_spam, spam_reasons = is_spam_content(data['comment'], data['username'])
    if is_spam:
        return jsonify({
            'error': 'Comment detected as spam',
            'reasons': spam_reasons
        }), 400
    
    # Add to database with timestamp
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    try:
        # Check for duplicate comments in last hour
        c.execute('''
            SELECT COUNT(*) FROM comments 
            WHERE user_ip = ? AND comment = ? AND 
            timestamp > datetime('now', '-1 hour')
        ''', (user_ip, data['comment']))
        
        if c.fetchone()[0] > 0:
            return jsonify({'error': 'Duplicate comment'}), 400
        
        # Insert comment
        c.execute('''
            INSERT INTO comments (section_id, blog_url, username, comment, timestamp, user_ip)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (section_id, data['blog_url'], data['username'], data['comment'],
              datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user_ip))
        
        conn.commit()
        return jsonify({'message': 'Comment added successfully'}), 201
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# Add reply endpoint
@app.route('/api/comments/<int:comment_id>/replies', methods=['POST'])
def add_reply(comment_id):
    data = request.json
    user_ip = request.remote_addr
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    try:
        # Get parent comment's section_id
        c.execute('SELECT section_id FROM comments WHERE id = ?', (comment_id,))
        parent = c.fetchone()
        if not parent:
            return jsonify({'error': 'Parent comment not found'}), 404
        
        section_id = parent[0]
        is_owner = bool(data.get('is_owner', False))
        
        # Insert reply with is_owner flag
        c.execute('''INSERT INTO comments 
            (section_id, blog_url, username, comment, timestamp, parent_id, is_owner, user_ip)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (section_id, data.get('blog_url', ''), data['username'], data['comment'],
             datetime.now().strftime('%Y-%m-%d %H:%M:%S'), comment_id, is_owner, user_ip))
        
        conn.commit()
        return jsonify({'message': 'Reply added successfully'}), 201
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# Update get_section_comments to include replies
@app.route('/api/sections/<int:section_id>/comments', methods=['GET'])
def get_section_comments(section_id):
    blog_url = request.args.get('blog_url', '')
    user_ip = request.remote_addr
    
    # Sanitize the blog_url to handle file:// URLs
    if blog_url.startswith('file://'):
        blog_url = blog_url.replace('file://', '')
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    try:
        # Get main comments with like info
        c.execute('''
            SELECT DISTINCT
                c.id, c.username, c.comment, c.timestamp, c.likes_count,
                EXISTS(SELECT 1 FROM likes WHERE comment_id = c.id AND user_ip = ?) as liked
            FROM comments c
            WHERE c.section_id = ? AND c.parent_id IS NULL
            ORDER BY c.timestamp DESC
        ''', (user_ip, section_id))
        
        main_comments = c.fetchall()
        result = []
        
        for comment in main_comments:
            c.execute('''
                SELECT 
                    id, username, comment, timestamp, likes_count,
                    EXISTS(SELECT 1 FROM likes WHERE comment_id = id AND user_ip = ?) as liked
                FROM comments 
                WHERE parent_id = ?
                ORDER BY timestamp ASC
            ''', (user_ip, comment[0]))
            
            replies = c.fetchall()
            
            result.append({
                'id': comment[0],
                'username': comment[1],
                'comment': comment[2],
                'timestamp': comment[3],
                'likes': comment[4],
                'liked': bool(comment[5]),
                'replies': [{
                    'id': r[0],
                    'username': r[1],
                    'comment': r[2],
                    'timestamp': r[3],
                    'likes': r[4],
                    'liked': bool(r[5])
                } for r in replies]
            })
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error fetching comments: {str(e)}")  # Add logging
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# Get user's sections
@app.route('/api/my-sections', methods=['GET'])
def get_sections():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
        
    user_id = session['user_id']
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    try:
        c.execute('''
            SELECT id, section_name, created_at 
            FROM comment_sections 
            WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (user_id,))
        
        sections = [{
            'id': row[0],
            'name': row[1],
            'created_at': row[2]
        } for row in c.fetchall()]
        
        return jsonify(sections)
    except Exception as e:
        print(f"Error fetching sections: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

# Update or add the dashboard route

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    
    user_id = session['user_id']
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    try:
        c.execute('SELECT api_key FROM users WHERE id = ?', (user_id,))
        api_key = c.fetchone()[0]
        return render_template('dashboard.html', api_key=api_key)
    finally:
        conn.close()

# Replace or update the get_all_comments route

@app.route('/api/all-comments', methods=['GET'])
def get_all_comments():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
        
    user_id = session['user_id']
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    try:
        # Modified query to only get comments from user's sections
        c.execute('''
            SELECT 
                c.id, c.section_id, c.username, c.comment, c.timestamp, 
                c.likes_count, c.blog_url, c.is_owner,
                s.section_name
            FROM comments c
            LEFT JOIN comment_sections s ON c.section_id = s.id
            WHERE c.parent_id IS NULL
            AND s.user_id = ?
            ORDER BY c.timestamp DESC
        ''', (user_id,))
        
        comments = []
        for row in c.fetchall():
            # Get replies for this comment
            c.execute('''
                SELECT id, username, comment, timestamp, likes_count, is_owner
                FROM comments 
                WHERE parent_id = ?
                ORDER BY timestamp ASC
            ''', (row[0],))
            
            replies = [{
                'id': r[0],
                'username': r[1],
                'comment': r[2],
                'timestamp': r[3],
                'likes': r[4],
                'is_owner': bool(r[5])
            } for r in c.fetchall()]
            
            comments.append({
                'id': row[0],
                'section_id': row[1],
                'username': row[2],
                'comment': row[3],
                'timestamp': row[4],
                'likes': row[5],
                'blog_url': row[6],
                'is_owner': bool(row[7]),
                'section_name': row[8] or 'Unknown Section',
                'replies': replies
            })
        
        return jsonify(comments)
        
    except Exception as e:
        print(f"Error fetching comments: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# Delete comment endpoint
@app.route('/api/delete-comment/<int:comment_id>', methods=['DELETE'])
def delete_comment(comment_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('DELETE FROM comments WHERE id = ?', (comment_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Comment deleted!"})

# Add the like endpoint
@app.route('/api/comments/<int:comment_id>/like', methods=['POST'])
def toggle_like(comment_id):
    user_ip = request.remote_addr
    
    try:
        with sqlite3.connect('database.db') as conn:
            c = conn.cursor()
            
            # Verify comment exists
            c.execute('SELECT id FROM comments WHERE id = ?', (comment_id,))
            if not c.fetchone():
                return jsonify({"error": "Comment not found"}), 404
            
            # Check if user already liked this comment
            c.execute('SELECT id FROM likes WHERE comment_id = ? AND user_ip = ?', 
                     (comment_id, user_ip))
            existing_like = c.fetchone()
            
            if existing_like:
                # Unlike: Remove like and decrease count
                c.execute('DELETE FROM likes WHERE comment_id = ? AND user_ip = ?',
                         (comment_id, user_ip))
                c.execute('UPDATE comments SET likes_count = likes_count - 1 WHERE id = ?',
                         (comment_id,))
                message = "Like removed"
            else:
                # Like: Add like and increase count
                c.execute('''INSERT INTO likes 
                           (comment_id, user_ip, created_at) 
                           VALUES (?, ?, ?)''', 
                         (comment_id, user_ip, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                c.execute('UPDATE comments SET likes_count = likes_count + 1 WHERE id = ?',
                         (comment_id,))
                message = "Like added"
            
            # Get updated like count
            c.execute('SELECT likes_count FROM comments WHERE id = ?', (comment_id,))
            likes_count = c.fetchone()[0]
            
            return jsonify({
                "message": message,
                "likes_count": likes_count,
                "success": True
            })
            
    except sqlite3.Error as e:
        return jsonify({
            "error": "Database error occurred",
            "message": str(e),
            "success": False
        }), 500

@app.route('/embed')
def embed_comments():
    url = request.args.get('url')
    title = request.args.get('title')
    site = request.args.get('site', 'default')
    
    if not url:
        return "URL parameter is required", 400
        
    # Get or create a section for this URL
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    # Check if section exists for this URL
    c.execute('SELECT id FROM comment_sections WHERE section_name = ?', (title or url,))
    section = c.fetchone()
    
    if not section:
        # Create a new section for this URL
        c.execute('''INSERT INTO comment_sections (user_id, section_name, created_at) 
                   VALUES (?, ?, ?)''', 
                 (session['user_id'], title or url, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        section_id = c.lastrowid
    else:
        section_id = section[0]
        
    conn.close()
    
    # Pass the section_id to the template
    return render_template('embed.html', section_id=section_id, url=url, title=title, site=site)

@app.route('/v1/embed.js')
def serve_embed_js():
    """Serve the embed JS file with the correct content type"""
    response = app.send_static_file('v1/embed.js')
    response.headers['Content-Type'] = 'application/javascript'
    return response

if __name__ == '__main__':
    init_db()
    # Get port from environment variable (for Render)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

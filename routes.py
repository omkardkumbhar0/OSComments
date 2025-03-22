# Add these new routes to your Flask application

from flask import abort, app, render_template

from app import login_required


@app.route('/comments/<category>')
@login_required
def view_category_comments(category):
    category_map = {
        'positive': 'good',
        'negative': 'bad',
        'improvements': 'improvement',
        'neutral': 'neutral'
    }
    
    if category not in category_map:
        abort(404)
        
    return render_template(
        'category_comments.html',
        category=category,
        category_name=category_map[category]
    )
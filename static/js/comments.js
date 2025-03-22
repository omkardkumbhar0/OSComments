class CommentsWidget {
    constructor(containerId, sectionId, apiKey) {
        this.container = document.getElementById(containerId);
        this.sectionId = sectionId;
        this.apiKey = apiKey;
        window[`commentsWidget_${this.sectionId}`] = this;  // Add this line
        this.init();
    }

    async init() {
        this.render();
        await this.loadComments();
    }

    render() {
        this.container.innerHTML = `
            <div class="comments-section">
                <div class="comments-header mb-4">
                    <div class="d-flex justify-content-between align-items-center">
                        <h3 class="comments-title">
                            <i class="bi bi-chat-square-text"></i> 
                            Discussion
                        </h3>
                        <div class="comments-count">
                            <span id="comment-count-${this.sectionId}">0</span> comments
                        </div>
                    </div>
                </div>

                <form id="comment-form-${this.sectionId}" class="comment-form">
                    <div class="comment-input-wrapper">
                        <div class="comment-input-header">
                            <input type="text" 
                                class="comment-name-input" 
                                id="comment-name-${this.sectionId}" 
                                placeholder="Your name"
                                required>
                        </div>
                        <div class="comment-input-body">
                            <textarea 
                                id="comment-text-${this.sectionId}" 
                                class="comment-textarea" 
                                placeholder="What are your thoughts?"
                                rows="3"
                                style="width: 100%; box-sizing: border-box;"
                                required></textarea>
                        </div>
                        <div class="comment-input-footer">
                            <div class="formatting-tools">
                                <button type="button" class="format-btn" title="Bold">
                                    <i class="bi bi-type-bold"></i>
                                </button>
                                <button type="button" class="format-btn" title="Italic">
                                    <i class="bi bi-type-italic"></i>
                                </button>
                                <button type="button" class="format-btn" title="Code">
                                    <i class="bi bi-code"></i>
                                </button>
                                <button type="button" class="format-btn" title="Link">
                                    <i class="bi bi-link-45deg"></i>
                                </button>
                            </div>
                            <button type="submit" class="submit-btn">
                                <i class="bi bi-send-fill"></i>
                                <span>Send</span>
                            </button>
                        </div>
                    </div>
                </form>

                <div class="comments-divider">
                    <span>Comments</span>
                </div>

                <div id="comments-list-${this.sectionId}" class="comments-list"></div>
            </div>
        `;

        // Add event listeners for formatting buttons
        const form = document.getElementById(`comment-form-${this.sectionId}`);
        const textarea = form.querySelector('textarea');
        
        // Bold button
        form.querySelector('[title="Bold"]').addEventListener('click', () => {
            this.insertFormat(textarea, '**', '**');
        });

        // Italic button
        form.querySelector('[title="Italic"]').addEventListener('click', () => {
            this.insertFormat(textarea, '*', '*');
        });

        // Code button
        form.querySelector('[title="Code"]').addEventListener('click', () => {
            this.insertFormat(textarea, '`', '`');
        });

        // Link button
        form.querySelector('[title="Link"]').addEventListener('click', () => {
            const url = prompt('Enter URL:');
            if (url) {
                this.insertFormat(textarea, '[', `](${url})`);
            }
        });

        // Add submit event listener
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = e.target.querySelector('button[type="submit"]');
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Submitting...';
            await this.submitComment();
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="bi bi-send me-2"></i>Submit Comment';
        });
    }

    // Update the submitComment method
    async submitComment() {
        const nameInput = document.getElementById(`comment-name-${this.sectionId}`);
        const textInput = document.getElementById(`comment-text-${this.sectionId}`);
        const submitBtn = document.querySelector(`#comment-form-${this.sectionId} button[type="submit"]`);

        // Basic client-side validation
        if (textInput.value.length > 1000) {
            alert('Comment is too long. Maximum 1000 characters allowed.');
            return;
        }

        if (nameInput.value.length > 50) {
            alert('Username is too long. Maximum 50 characters allowed.');
            return;
        }

        try {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Submitting...';

            const response = await fetch(`https://oscomments.onrender.com/api/sections/${this.sectionId}/comments`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': this.apiKey
                },
                body: JSON.stringify({
                    blog_url: window.location.href,
                    username: nameInput.value,
                    comment: textInput.value
                })
            });

            const data = await response.json();

            if (!response.ok) {
                if (response.status === 400 && data.reasons) {
                    alert(`Comment detected as spam:\n${data.reasons.join('\n')}`);
                } else if (response.status === 429) {
                    alert('You are commenting too frequently. Please try again later.');
                } else {
                    alert(data.error || 'Failed to submit comment. Please try again.');
                }
                return;
            }

            // Clear form
            nameInput.value = '';
            textInput.value = '';

            // Reload comments
            await this.loadComments();
        } catch (error) {
            console.error('Error submitting comment:', error);
            alert('Failed to submit comment. Please try again.');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="bi bi-send-fill"></i><span>Send</span>';
        }
    }

    async loadComments() {
        try {
            const response = await fetch(
                `https://oscomments.onrender.com/api/sections/${this.sectionId}/comments?blog_url=${encodeURIComponent(window.location.href)}`,
                {
                    headers: {
                        'X-API-Key': this.apiKey
                    }
                }
            );
            if (!response.ok) {
                throw new Error('Failed to load comments');
            }
            const comments = await response.json();
            this.displayComments(comments);
            
            // Update comment count
            const commentCount = document.getElementById(`comment-count-${this.sectionId}`);
            if (commentCount) {
                commentCount.textContent = comments.length;
            }
        } catch (error) {
            console.error('Error loading comments:', error);
        }
    }

    displayComments(comments) {
        const commentsList = document.getElementById(`comments-list-${this.sectionId}`);
        const commentCount = document.getElementById(`comment-count-${this.sectionId}`);
        commentCount.textContent = comments.length;

        if (comments.length === 0) {
            commentsList.innerHTML = `
                <div class="text-center py-5">
                    <div class="empty-state-animation mb-3">
                        <i class="bi bi-chat-square-heart display-1 text-primary opacity-75"></i>
                    </div>
                    <p class="lead text-muted">Start the conversation! 💭</p>
                    <p class="text-muted small">Share your thoughts with others</p>
                </div>
            `;
            return;
        }

        // Set max-height only when more than 2 comments
        if (comments.length > 2) {
            commentsList.style.maxHeight = '500px';
            commentsList.style.overflowY = 'auto';
            commentsList.style.paddingRight = '0.5rem'; // Add padding for scrollbar
        } else {
            commentsList.style.maxHeight = 'none';
            commentsList.style.overflowY = 'hidden';
            commentsList.style.paddingRight = '0';
        }

        // Update the comment template in displayComments method
        commentsList.innerHTML = comments.map(comment => `
            <div class="comment" data-comment-id="${comment.id}">
                <div class="comment-container">
                    <div class="d-flex w-100 gap-2">
                        <div class="comment-avatar flex-shrink-0" data-initial="${comment.username.charAt(0).toUpperCase()}">
                            ${comment.username.charAt(0).toUpperCase()}
                        </div>
                        <div class="comment-content flex-grow-1">
                            <div class="comment-header d-flex flex-wrap gap-2 align-items-center">
                                <span class="comment-author">${comment.username}</span>
                                <span class="comment-time small">
                                    <i class="bi bi-clock"></i>
                                    ${this.formatDate(comment.timestamp)}
                                </span>
                            </div>
                            <div class="comment-body my-2">
                                ${this.formatComment(comment.comment)}
                            </div>
                            <div class="comment-actions">
                                <button class="action-btn ${comment.liked ? 'liked' : ''}" 
                                        onclick="window.commentsWidget_${this.sectionId}.toggleLike('${comment.id}')">
                                    <i class="bi ${comment.liked ? 'bi-heart-fill' : 'bi-heart'}"></i>
                                    <span class="d-none d-sm-inline">Like</span>${comment.likes > 0 ? ` · ${comment.likes}` : ''}
                                </button>
                                <button class="action-btn" 
                                        onclick="window.commentsWidget_${this.sectionId}.showReplyForm('${comment.id}')">
                                    <i class="bi bi-reply"></i>
                                    <span class="d-none d-sm-inline">Reply</span>${comment.replies ? ` · ${comment.replies.length}` : ''}
                                </button>
                                
                            </div>
                            <div class="reply-container mt-3">
                                ${comment.replies ? comment.replies.map(reply => `
                                    <div class="reply ms-4 mt-2">
                                        <div class="d-flex gap-2">
                                            <div class="reply-avatar" data-initial="${reply.username.charAt(0).toUpperCase()}">
                                                ${reply.username.charAt(0).toUpperCase()}
                                            </div>
                                            <div class="reply-content">
                                                <div class="reply-header">
                                                    <span class="reply-author">${reply.username}</span>
                                                    <span class="reply-time">
                                                        ${this.formatDate(reply.timestamp)}
                                                    </span>
                                                </div>
                                                <div class="reply-body">
                                                    ${this.formatComment(reply.comment)}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                `).join('') : ''}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');

        if (comments.length > 3) {
            const lastComment = commentsList.lastElementChild;
            lastComment.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }

    formatDate(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = (now - date) / 1000; // difference in seconds

        if (diff < 60) return 'Just now';
        if (diff < 3600) return `${Math.floor(diff / 60)} minutes ago`;
        if (diff < 86400) return `${Math.floor(diff / 3600)} hours ago`;
        if (diff < 604800) return `${Math.floor(diff / 86400)} days ago`;
        
        return date.toLocaleDateString();
    }

    formatComment(text) {
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/\n/g, '<br>')
            // Code blocks
            .replace(/`(.*?)`/g, '<code class="bg-light px-2 rounded">$1</code>')
            // Blockquotes
            .replace(/^&gt; (.*)$/gm, '<blockquote class="border-start border-3 border-primary ps-3 my-2 text-muted">$1</blockquote>')
            // Lists
            .replace(/^- (.*)$/gm, '<li class="ms-3">$1</li>')
            .replace(/^(\d+)\. (.*)$/gm, '<li class="ms-3">$1. $2</li>')
            // Links
            .replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank" class="text-decoration-none">$1</a>')
            // Bold and italic
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>');
    }

    insertFormat(textarea, prefix, suffix) {
        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        const text = textarea.value;
        const before = text.substring(0, start);
        const selection = text.substring(start, end);
        const after = text.substring(end);

        textarea.value = before + prefix + selection + suffix + after;
        textarea.focus();
        textarea.selectionStart = start + prefix.length;
        textarea.selectionEnd = end + prefix.length;
    }

    // Add this method to the CommentsWidget class
    async toggleLike(commentId) {
        try {
            const response = await fetch(`https://oscomments.onrender.com/api/comments/${commentId}/like`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': this.apiKey
                }
            });

            if (!response.ok) {
                throw new Error('Failed to toggle like');
            }

            await this.loadComments(); // Reload comments to update like count
        } catch (error) {
            console.error('Error toggling like:', error);
        }
    }

    // Add these methods to the CommentsWidget class
    async submitReply(commentId, replyText) {
        try {
            const nameInput = document.getElementById(`comment-name-${this.sectionId}`);
            const response = await fetch(`https://oscomments.onrender.com/api/comments/${commentId}/replies`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': this.apiKey
                },
                body: JSON.stringify({
                    blog_url: window.location.href,
                    username: nameInput.value || 'Anonymous',
                    comment: replyText,
                    parent_id: commentId
                })
            });

            if (!response.ok) {
                throw new Error('Failed to submit reply');
            }

            await this.loadComments();
        } catch (error) {
            console.error('Error submitting reply:', error);
            alert('Failed to submit reply. Please try again.');
        }
    }

    showReplyForm(commentId) {
        const existingForm = document.querySelector('.reply-form');
        if (existingForm) {
            existingForm.remove();
        }

        const commentElement = document.querySelector(`[data-comment-id="${commentId}"]`);
        const replyForm = document.createElement('div');
        replyForm.className = 'reply-form mt-3';
        replyForm.innerHTML = `
            <div class="d-flex gap-2">
                <textarea class="form-control form-control-sm" 
                    rows="2" 
                    placeholder="Write a reply..."></textarea>
                <button class="btn btn-sm btn-dark reply-submit">
                    Reply
                </button>
            </div>
        `;

        const replyContainer = commentElement.querySelector('.reply-container');
        replyContainer.insertBefore(replyForm, replyContainer.firstChild);

        const textarea = replyForm.querySelector('textarea');
        textarea.focus();

        replyForm.querySelector('.reply-submit').addEventListener('click', async () => {
            if (textarea.value.trim()) {
                await this.submitReply(commentId, textarea.value);
                replyForm.remove();
            }
        });
    }
}

// ...existing code...

async function submitComment(sectionId, commentText, username) {
    try {
        const response = await fetch(`https://oscomments.onrender.com/api/sections/${sectionId}/comments`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                comment: commentText,
                username: username,
                blog_url: window.location.href
            })
        });

        const data = await response.json();

        if (response.ok) {
            // Handle successful comment submission
            showNotification('Comment added successfully!', 'success');
            
            // Display AI analysis if available
            if (data.analysis) {
                displayCommentAnalysis(data.analysis);
            }

            return true;
        } else {
            // Handle error cases
            const errorMessage = data.error || data.reason || 'Error submitting comment';
            showNotification(errorMessage, 'error');
            return false;
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error submitting comment', 'error');
        return false;
    }
}

function displayCommentAnalysis(analysis) {
    // Create analysis display element
    const analysisDiv = document.createElement('div');
    analysisDiv.className = 'comment-analysis';
    
    // Add analysis information
    analysisDiv.innerHTML = `
        <h4>Comment Analysis</h4>
        <ul>
            <li>Sentiment: ${analysis.sentiment}</li>
            <li>Category: ${analysis.category}</li>
            ${analysis.spam_probability > 0.3 ? 
                `<li class="warning">Spam Probability: ${Math.round(analysis.spam_probability * 100)}%</li>` : ''}
            ${analysis.toxicity_level > 0.3 ? 
                `<li class="warning">Toxicity Level: ${Math.round(analysis.toxicity_level * 100)}%</li>` : ''}
        </ul>
    `;
    
    // Add some styling
    const style = document.createElement('style');
    style.textContent = `
        .comment-analysis {
            margin: 10px 0;
            padding: 10px;
            background: #f5f5f5;
            border-radius: 4px;
            font-size: 0.9em;
        }
        .comment-analysis h4 {
            margin: 0 0 10px 0;
            color: #333;
        }
        .comment-analysis ul {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        .comment-analysis li {
            margin: 5px 0;
        }
        .comment-analysis .warning {
            color: #e65100;
        }
    `;
    document.head.appendChild(style);
    
    // Find the last submitted comment and append the analysis
    const commentsList = document.querySelector('.comments-list');
    if (commentsList) {
        const lastComment = commentsList.firstChild;
        if (lastComment) {
            lastComment.appendChild(analysisDiv);
        }
    }
}

function showNotification(message, type) {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.classList.add('fade-out');
        setTimeout(() => {
            notification.remove();
        }, 500);
    }, 3000);
}

// Add CSS for notifications
const notificationStyles = document.createElement('style');
notificationStyles.textContent = `
    .notification {
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 25px;
        border-radius: 4px;
        color: white;
        z-index: 1000;
        animation: slideIn 0.5s ease-out;
    }
    
    .notification.success {
        background-color: #4caf50;
    }
    
    .notification.error {
        background-color: #f44336;
    }
    
    .notification.fade-out {
        animation: fadeOut 0.5s ease-out;
    }
    
    @keyframes slideIn {
        from { transform: translateX(100%); }
        to { transform: translateX(0); }
    }
    
    @keyframes fadeOut {
        from { opacity: 1; }
        to { opacity: 0; }
    }
`;
document.head.appendChild(notificationStyles);

// ...existing code...
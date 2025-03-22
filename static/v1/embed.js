// Comments API Embed Script
(function() {
  // Find the comments container
  const container = document.getElementById('comments-container');
  if (!container) {
    console.error('Comments container not found. Please add <div id="comments-container"></div> to your page.');
    return;
  }

  // Get the current page URL and title
  const pageUrl = encodeURIComponent(window.location.href);
  const pageTitle = encodeURIComponent(document.title);
  
  // Get site identifier from script tag (future use)
  const scriptTag = document.querySelector('script[src*="comments.dev/v1/embed.js"]');
  const siteId = scriptTag?.getAttribute('data-site-id') || 'default';
  
  // Create the iframe for comments
  const iframe = document.createElement('iframe');
  
  // Set iframe attributes
  iframe.src = `https://comments-api.onrender.com/embed?url=${pageUrl}&title=${pageTitle}&site=${siteId}`;
  iframe.style.width = '100%';
  iframe.style.height = '600px';
  iframe.style.border = 'none';
  iframe.style.borderRadius = '4px';
  iframe.title = 'Comments';
  iframe.loading = 'lazy';
  
  // Add iframe to container
  container.appendChild(iframe);
  
  // Handle messages from iframe for dynamic height adjustment
  window.addEventListener('message', function(e) {
    if (e.origin !== 'https://comments-api.onrender.com') return;
    
    if (e.data.type === 'resize') {
      iframe.style.height = `${e.data.height}px`;
    }
  });
})(); 
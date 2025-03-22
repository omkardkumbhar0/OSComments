// OSComments Embed Script
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
  const scriptTag = document.querySelector('script[src*="embed.js"]');
  const siteId = scriptTag?.getAttribute('data-site-id') || 'default';
  
  // Dynamically determine the API domain based on the script src
  let apiDomain = 'https://oscomments.onrender.com';
  if (scriptTag) {
    const srcUrl = new URL(scriptTag.src, window.location.origin);
    apiDomain = `${srcUrl.protocol}//${srcUrl.hostname}`;
  }
  
  // Create the iframe for comments
  const iframe = document.createElement('iframe');
  
  // Set iframe attributes
  iframe.src = `${apiDomain}/embed?url=${pageUrl}&title=${pageTitle}&site=${siteId}`;
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
    // Check if the message is from our comments domain
    const origin = new URL(apiDomain).hostname;
    if (!e.origin.includes(origin)) return;
    
    if (e.data.type === 'resize') {
      iframe.style.height = `${e.data.height}px`;
    }
  });
})(); 
function getCSRFToken() {
    const cookieValue = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrf_token='))
        ?.split('=')[1];
    return cookieValue || '';
}

document.addEventListener('DOMContentLoaded', function() {

    const forms = document.querySelectorAll('form[data-ajax]');
    forms.forEach(form => {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const action = this.getAttribute('action');
            const method = this.getAttribute('method') || 'POST';
            
            try {
                const response = await fetch(action, {
                    method: method,
                    body: formData,
                    headers: {
                        'X-CSRF-Token': getCSRFToken()
                    }
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    // Handle success
                    if (data.redirect) {
                        window.location.href = data.redirect;
                    } else {

                        showFlashMessage('success', data.message || 'Operation successful');
                    }
                } else {

                    showFlashMessage('error', data.detail || 'An error occurred');
                }
            } catch (error) {
                showFlashMessage('error', 'Network error. Please try again.');
            }
        });
    });

    const deleteButtons = document.querySelectorAll('[data-confirm-delete]');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to delete this?')) {
                e.preventDefault();
            }
        });
    });
    
    const likeButtons = document.querySelectorAll('[data-like-post]');
    likeButtons.forEach(button => {
        button.addEventListener('click', async function() {
            const postId = this.dataset.postId;
            const isLiked = this.dataset.liked === 'true';
            const action = isLiked ? 'unlike' : 'like';
            
            try {
                const response = await fetch(`/api/posts/${postId}/favorite`, {
                    method: isLiked ? 'DELETE' : 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRF-Token': getCSRFToken()
                    }
                });
                
                if (response.ok) {
                    // Update button state
                    this.dataset.liked = !isLiked;
                    this.innerHTML = isLiked ? 
                        '<i class="far fa-heart"></i> Like' : 
                        '<i class="fas fa-heart"></i> Liked';
                    
                    // Update like count
                    const likeCount = this.closest('.post-actions').querySelector('.like-count');
                    if (likeCount) {
                        const currentCount = parseInt(likeCount.textContent);
                        likeCount.textContent = isLiked ? currentCount - 1 : currentCount + 1;
                    }
                }
            } catch (error) {
                console.error('Error liking post:', error);
            }
        });
    });

    const followButtons = document.querySelectorAll('[data-follow-user]');
    followButtons.forEach(button => {
        button.addEventListener('click', async function() {
            const userId = this.dataset.userId;
            const isFollowing = this.dataset.following === 'true';
            const action = isFollowing ? 'unfollow' : 'follow';
            
            try {
                const response = await fetch(`/api/users/${userId}/follow`, {
                    method: isFollowing ? 'DELETE' : 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRF-Token': getCSRFToken()
                    }
                });
                
                if (response.ok) {
                    // Update button state
                    this.dataset.following = !isFollowing;
                    this.innerHTML = isFollowing ? 
                        '<i class="fas fa-user-plus"></i> Follow' : 
                        '<i class="fas fa-user-check"></i> Following';
                    
                    // Update follower count
                    const followerCount = document.querySelector('.follower-count');
                    if (followerCount) {
                        const currentCount = parseInt(followerCount.textContent);
                        followerCount.textContent = isFollowing ? currentCount - 1 : currentCount + 1;
                    }
                }
            } catch (error) {
                console.error('Error following user:', error);
            }
        });
    });
});

function showFlashMessage(type, message) {
    const flashContainer = document.querySelector('.flash-messages') || createFlashContainer();
    const flashMessage = document.createElement('div');
    flashMessage.className = `flash-message ${type}`;
    flashMessage.textContent = message;
    
    flashContainer.appendChild(flashMessage);
    
    setTimeout(() => {
        flashMessage.remove();
        if (flashContainer.children.length === 0) {
            flashContainer.remove();
        }
    }, 5000);
}

function createFlashContainer() {
    const container = document.createElement('div');
    container.className = 'flash-messages';
    document.querySelector('.container').prepend(container);
    return container;
}

let isLoading = false;
let currentPage = 1;
let hasMorePosts = true;

function initInfiniteScroll() {
    const postList = document.querySelector('.post-list');
    if (!postList) return;
    
    window.addEventListener('scroll', async () => {
        if (isLoading || !hasMorePosts) return;
        
        const scrollPosition = window.innerHeight + window.scrollY;
        const documentHeight = document.documentElement.scrollHeight;
        
        if (scrollPosition >= documentHeight - 500) {
            await loadMorePosts();
        }
    });
}

async function loadMorePosts() {
    isLoading = true;
    currentPage++;
    
    try {
        const response = await fetch(`/api/posts?page=${currentPage}`);
        const posts = await response.json();
        
        if (posts.length === 0) {
            hasMorePosts = false;
            return;
        }
        
        const postList = document.querySelector('.post-list');
        posts.forEach(post => {
            const postElement = createPostElement(post);
            postList.appendChild(postElement);
        });
    } catch (error) {
        console.error('Error loading more posts:', error);
    } finally {
        isLoading = false;
    }
}

function createPostElement(post) {
    const div = document.createElement('div');
    div.className = 'post-card';
    div.innerHTML = `
        <h3><a href="/posts/${post.id}">${post.title}</a></h3>
        <div class="post-meta">
            By <a href="/users/${post.author.id}">${post.author.login}</a> • 
            ${new Date(post.created_at).toLocaleDateString()} • 
            ${post.categories.map(cat => cat.name).join(', ')}
        </div>
        <p class="post-excerpt">${post.summary || post.content.substring(0, 200)}...</p>
        <div class="post-actions">
            <button class="btn btn-link" data-like-post data-post-id="${post.id}" data-liked="false">
                <i class="far fa-heart"></i> Like
            </button>
            <span class="like-count">${post.likes_count}</span>
            <a href="/posts/${post.id}#comments" class="btn btn-link">
                <i class="far fa-comment"></i> Comment
            </a>
            <span>${post.comments_count}</span>
        </div>
    `;
    return div;
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initInfiniteScroll);
} else {
    initInfiniteScroll();
}
// Infinite scroll functionality for SociaFam

class InfiniteScroll {
    constructor(containerSelector, loadMoreUrl, itemSelector) {
        this.container = document.querySelector(containerSelector);
        this.loadMoreUrl = loadMoreUrl;
        this.itemSelector = itemSelector;
        this.isLoading = false;
        this.hasMore = true;
        this.page = 1;
        
        this.init();
    }
    
    init() {
        if (this.container) {
            // Add scroll event listener
            window.addEventListener('scroll', this.handleScroll.bind(this));
            
            // Load initial content
            this.loadMore();
        }
    }
    
    handleScroll() {
        const scrollTop = window.scrollY || document.documentElement.scrollTop;
        const windowHeight = window.innerHeight;
        const documentHeight = document.documentElement.scrollHeight;
        
        // Check if we're near the bottom of the page
        if (scrollTop + windowHeight >= documentHeight - 200) {
            this.loadMore();
        }
    }
    
    loadMore() {
        if (this.isLoading || !this.hasMore) return;
        
        this.isLoading = true;
        
        // Show loading indicator
        this.showLoadingIndicator();
        
        fetch(`${this.loadMoreUrl}?page=${this.page}`)
            .then(response => response.json())
            .then(data => {
                this.isLoading = false;
                
                // Hide loading indicator
                this.hideLoadingIndicator();
                
                if (data.posts && data.posts.length > 0) {
                    this.renderItems(data.posts);
                    this.page++;
                    this.hasMore = data.has_next;
                } else {
                    this.hasMore = false;
                    this.showNoMoreContent();
                }
            })
            .catch(error => {
                this.isLoading = false;
                this.hideLoadingIndicator();
                console.error('Error loading more content:', error);
            });
    }
    
    renderItems(items) {
        const fragment = document.createDocumentFragment();
        
        items.forEach(item => {
            const itemElement = this.createItemElement(item);
            fragment.appendChild(itemElement);
        });
        
        this.container.appendChild(fragment);
    }
    
    createItemElement(item) {
        // This should be implemented based on your specific item structure
        const div = document.createElement('div');
        div.className = 'post';
        div.innerHTML = `
            <div class="card">
                <div class="card-header">
                    <img src="/image/${item.author.id}" alt="${item.author.username}" class="profile-img">
                    <div>
                        <strong>${item.author.real_name}</strong>
                        <div>@${item.author.username}</div>
                    </div>
                    <span class="relative-time" data-time="${item.created_at}">${formatRelativeTime(item.created_at)}</span>
                </div>
                <div class="card-body">
                    ${item.content ? `<p>${item.content}</p>` : ''}
                    ${item.image ? `<img src="/post-image/${item.id}" class="post-img" alt="Post image">` : ''}
                    ${item.video ? `<video src="/post-video/${item.id}" class="post-video" controls></video>` : ''}
                </div>
                <div class="card-footer">
                    <div class="post-actions">
                        <button class="post-action like-btn ${item.is_liked ? 'active' : ''}" data-post-id="${item.id}">
                            <i class="${item.is_liked ? 'fas' : 'far'} fa-heart"></i>
                            <span>${item.likes_count}</span>
                        </button>
                        <button class="post-action comment-btn" data-post-id="${item.id}">
                            <i class="far fa-comment"></i>
                            <span>${item.comments_count}</span>
                        </button>
                        <button class="post-action share-btn" data-post-id="${item.id}">
                            <i class="far fa-share-square"></i>
                        </button>
                        <button class="post-action save-btn" data-post-id="${item.id}">
                            <i class="far fa-bookmark"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        return div;
    }
    
    showLoadingIndicator() {
        let loadingIndicator = document.getElementById('loadingIndicator');
        
        if (!loadingIndicator) {
            loadingIndicator = document.createElement('div');
            loadingIndicator.id = 'loadingIndicator';
            loadingIndicator.className = 'loading-indicator';
            loadingIndicator.innerHTML = '<div class="spinner"></div><p>Loading more content...</p>';
            this.container.appendChild(loadingIndicator);
        }
        
        loadingIndicator.style.display = 'block';
    }
    
    hideLoadingIndicator() {
        const loadingIndicator = document.getElementById('loadingIndicator');
        if (loadingIndicator) {
            loadingIndicator.style.display = 'none';
        }
    }
    
    showNoMoreContent() {
        const noMoreContent = document.createElement('div');
        noMoreContent.className = 'no-more-content';
        noMoreContent.innerHTML = '<p>No more content to load</p>';
        this.container.appendChild(noMoreContent);
    }
}

// Initialize infinite scroll when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new InfiniteScroll('#postsContainer', '/api/posts', '.post');
});

// Add CSS for loading indicator
const style = document.createElement('style');
style.textContent = `
    .loading-indicator {
        text-align: center;
        padding: 20px;
    }
    
    .spinner {
        border: 3px solid #f3f3f3;
        border-top: 3px solid #1877f2;
        border-radius: 50%;
        width: 30px;
        height: 30px;
        animation: spin 1s linear infinite;
        margin: 0 auto 10px;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    .no-more-content {
        text-align: center;
        padding: 20px;
        color: #65676b;
    }
`;
document.head.appendChild(style);

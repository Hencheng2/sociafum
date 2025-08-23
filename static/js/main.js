// Main JavaScript functionality for SociaFam

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Handle flash message dismissal
    const flashMessages = document.querySelectorAll('.flash');
    if (flashMessages.length > 0) {
        flashMessages.forEach(flash => {
            setTimeout(() => {
                flash.style.opacity = '0';
                setTimeout(() => flash.remove(), 300);
            }, 5000);
        });
    }
    
    // Handle mobile menu toggle
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    const mobileMenu = document.getElementById('mobileMenu');
    
    if (mobileMenuBtn && mobileMenu) {
        mobileMenuBtn.addEventListener('click', () => {
            mobileMenu.classList.toggle('show');
        });
    }
    
    // Handle profile picture upload preview
    const profilePicInput = document.getElementById('profilePic');
    const profilePicPreview = document.getElementById('profilePicPreview');
    
    if (profilePicInput && profilePicPreview) {
        profilePicInput.addEventListener('change', function() {
            const file = this.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    profilePicPreview.src = e.target.result;
                };
                reader.readAsDataURL(file);
            }
        });
    }
    
    // Handle post like functionality
    const likeButtons = document.querySelectorAll('.like-btn');
    likeButtons.forEach(button => {
        button.addEventListener('click', function() {
            const postId = this.dataset.postId;
            likePost(postId, this);
        });
    });
    
    // Handle follow functionality
    const followButtons = document.querySelectorAll('.follow-btn');
    followButtons.forEach(button => {
        button.addEventListener('click', function() {
            const userId = this.dataset.userId;
            followUser(userId, this);
        });
    });
});

// Like a post
function likePost(postId, button) {
    fetch(`/like-post/${postId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
    })
    .then(response => response.json())
    .then(data => {
        if (data.liked) {
            button.classList.add('active');
            button.innerHTML = `<i class="fas fa-heart"></i> ${data.likes_count}`;
        } else {
            button.classList.remove('active');
            button.innerHTML = `<i class="far fa-heart"></i> ${data.likes_count}`;
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
}

// Follow a user
function followUser(userId, button) {
    fetch(`/follow-user/${userId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
    })
    .then(response => response.json())
    .then(data => {
        if (data.followed) {
            button.classList.add('active');
            button.textContent = `Following (${data.followers_count})`;
        } else {
            button.classList.remove('active');
            button.textContent = `Follow (${data.followers_count})`;
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
}

// Show image in modal
function showImageModal(imageSrc) {
    const modal = document.getElementById('imageModal');
    const modalImage = document.getElementById('modalImage');
    
    if (modal && modalImage) {
        modalImage.src = imageSrc;
        const imageModal = new bootstrap.Modal(modal);
        imageModal.show();
    }
}

// Show video in modal
function showVideoModal(videoSrc) {
    const modal = document.getElementById('videoModal');
    const modalVideo = document.getElementById('modalVideo');
    
    if (modal && modalVideo) {
        modalVideo.src = videoSrc;
        const videoModal = new bootstrap.Modal(modal);
        videoModal.show();
    }
}

// Handle form submissions with AJAX
function handleFormSubmit(formId, callback) {
    const form = document.getElementById(formId);
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const action = this.action;
            const method = this.method;
            
            fetch(action, {
                method: method,
                body: formData,
            })
            .then(response => response.json())
            .then(data => {
                if (callback && typeof callback === 'function') {
                    callback(data);
                }
            })
            .catch(error => {
                console.error('Error:', error);
            });
        });
    }
}

// Format relative time
function formatRelativeTime(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffInSeconds = Math.floor((now - date) / 1000);
    
    if (diffInSeconds < 60) {
        return 'just now';
    } else if (diffInSeconds < 3600) {
        const minutes = Math.floor(diffInSeconds / 60);
        return `${minutes} minute${minutes !== 1 ? 's' : ''} ago`;
    } else if (diffInSeconds < 86400) {
        const hours = Math.floor(diffInSeconds / 3600);
        return `${hours} hour${hours !== 1 ? 's' : ''} ago`;
    } else if (diffInSeconds < 604800) {
        const days = Math.floor(diffInSeconds / 86400);
        return `${days} day${days !== 1 ? 's' : ''} ago`;
    } else {
        return date.toLocaleDateString();
    }
}

// Update all relative times on the page
function updateRelativeTimes() {
    const timeElements = document.querySelectorAll('.relative-time');
    timeElements.forEach(element => {
        const dateString = element.dataset.time;
        if (dateString) {
            element.textContent = formatRelativeTime(dateString);
        }
    });
}

// Initialize relative time formatting
document.addEventListener('DOMContentLoaded', updateRelativeTimes);
setInterval(updateRelativeTimes, 60000); // Update every minute

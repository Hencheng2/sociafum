// Reels functionality for SociaFam

class ReelsPlayer {
    constructor() {
        this.reels = [];
        this.currentReelIndex = 0;
        this.isPlaying = true;
        this.isMuted = true;
        
        this.reelContainer = document.getElementById('reelsContainer');
        this.reelVideo = document.getElementById('reelVideo');
        this.reelUsername = document.getElementById('reelUsername');
        this.reelDescription = document.getElementById('reelDescription');
        this.reelLikes = document.getElementById('reelLikes');
        this.reelComments = document.getElementById('reelComments');
        this.reelPlayBtn = document.getElementById('reelPlayBtn');
        this.reelMuteBtn = document.getElementById('reelMuteBtn');
        this.reelLikeBtn = document.getElementById('reelLikeBtn');
        
        this.init();
    }
    
    init() {
        if (this.reelContainer) {
            this.loadReels();
            
            // Add event listeners
            this.reelContainer.addEventListener('click', this.togglePlay.bind(this));
            this.reelMuteBtn.addEventListener('click', this.toggleMute.bind(this));
            this.reelLikeBtn.addEventListener('click', this.toggleLike.bind(this));
            
            // Add swipe events for mobile
            this.reelContainer.addEventListener('touchstart', this.handleTouchStart.bind(this), false);
            this.reelContainer.addEventListener('touchmove', this.handleTouchMove.bind(this), false);
            
            // Add keyboard events for desktop
            document.addEventListener('keydown', this.handleKeyDown.bind(this));
            
            // Add visibility change event
            document.addEventListener('visibilitychange', this.handleVisibilityChange.bind(this));
        }
    }
    
    loadReels() {
        // In a real implementation, this would fetch reels from the server
        // For now, we'll use data attributes on the reel elements
        const reelElements = document.querySelectorAll('.reel');
        this.reels = Array.from(reelElements).map(el => ({
            id: el.dataset.reelId,
            video: el.dataset.reelVideo,
            username: el.dataset.username,
            description: el.dataset.description,
            likes: parseInt(el.dataset.likes),
            comments: parseInt(el.dataset.comments),
            isLiked: el.dataset.isLiked === 'true'
        }));
        
        if (this.reels.length > 0) {
            this.currentReelIndex = 0;
            this.showReel();
        }
    }
    
    showReel() {
        if (this.reels.length === 0) return;
        
        const reel = this.reels[this.currentReelIndex];
        
        this.reelVideo.src = `/video/${reel.video}`;
        this.reelUsername.textContent = reel.username;
        this.reelDescription.textContent = reel.description;
        this.reelLikes.textContent = this.formatCount(reel.likes);
        this.reelComments.textContent = this.formatCount(reel.comments);
        
        // Update like button state
        if (reel.isLiked) {
            this.reelLikeBtn.classList.add('active');
            this.reelLikeBtn.innerHTML = '<i class="fas fa-heart"></i>';
        } else {
            this.reelLikeBtn.classList.remove('active');
            this.reelLikeBtn.innerHTML = '<i class="far fa-heart"></i>';
        }
        
        this.playReel();
    }
    
    playReel() {
        this.reelVideo.play().then(() => {
            this.isPlaying = true;
            this.updatePlayButton();
        }).catch(error => {
            console.error('Error playing video:', error);
        });
    }
    
    pauseReel() {
        this.reelVideo.pause();
        this.isPlaying = false;
        this.updatePlayButton();
    }
    
    togglePlay() {
        if (this.isPlaying) {
            this.pauseReel();
        } else {
            this.playReel();
        }
    }
    
    toggleMute() {
        this.isMuted = !this.isMuted;
        this.reelVideo.muted = this.isMuted;
        this.updateMuteButton();
    }
    
    toggleLike() {
        const reel = this.reels[this.currentReelIndex];
        reel.isLiked = !reel.isLiked;
        
        if (reel.isLiked) {
            reel.likes++;
            this.reelLikeBtn.classList.add('active');
            this.reelLikeBtn.innerHTML = '<i class="fas fa-heart"></i>';
        } else {
            reel.likes--;
            this.reelLikeBtn.classList.remove('active');
            this.reelLikeBtn.innerHTML = '<i class="far fa-heart"></i>';
        }
        
        this.reelLikes.textContent = this.formatCount(reel.likes);
        
        // Send like to server
        fetch(`/like-post/${reel.id}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
        }).catch(error => {
            console.error('Error:', error);
        });
    }
    
    updatePlayButton() {
        if (this.isPlaying) {
            this.reelPlayBtn.style.display = 'none';
        } else {
            this.reelPlayBtn.style.display = 'block';
        }
    }
    
    updateMuteButton() {
        if (this.isMuted) {
            this.reelMuteBtn.innerHTML = '<i class="fas fa-volume-mute"></i>';
        } else {
            this.reelMuteBtn.innerHTML = '<i class="fas fa-volume-up"></i>';
        }
    }
    
    nextReel() {
        if (this.currentReelIndex < this.reels.length - 1) {
            this.currentReelIndex++;
            this.showReel();
        }
    }
    
    previousReel() {
        if (this.currentReelIndex > 0) {
            this.currentReelIndex--;
            this.showReel();
        }
    }
    
    handleTouchStart(e) {
        this.touchStartY = e.touches[0].clientY;
    }
    
    handleTouchMove(e) {
        if (!this.touchStartY) return;
        
        const touchEndY = e.touches[0].clientY;
        const diffY = touchEndY - this.touchStartY;
        
        // Vertical swipe (next/previous reel)
        if (Math.abs(diffY) > 50) {
            if (diffY < 0) {
                this.nextReel();
            } else {
                this.previousReel();
            }
        }
        
        // Reset touch coordinates
        this.touchStartY = null;
    }
    
    handleKeyDown(e) {
        if (e.key === 'ArrowDown') {
            this.nextReel();
        } else if (e.key === 'ArrowUp') {
            this.previousReel();
        } else if (e.key === ' ') {
            this.togglePlay();
        } else if (e.key === 'm') {
            this.toggleMute();
        }
    }
    
    handleVisibilityChange() {
        if (document.hidden) {
            this.pauseReel();
        }
    }
    
    formatCount(count) {
        if (count >= 1000000) {
            return (count / 1000000).toFixed(1) + 'M';
        } else if (count >= 1000) {
            return (count / 1000).toFixed(1) + 'K';
        } else {
            return count.toString();
        }
    }
}

// Initialize reels player when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ReelsPlayer();
});

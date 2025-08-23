// Stories functionality for SociaFam

class StoryViewer {
    constructor() {
        this.stories = [];
        this.currentStoryIndex = 0;
        this.currentUserId = null;
        this.isPlaying = true;
        this.progressInterval = null;
        
        this.modal = document.getElementById('storyModal');
        this.storyImage = document.getElementById('storyImage');
        this.storyVideo = document.getElementById('storyVideo');
        this.storyUsername = document.getElementById('storyUsername');
        this.storyProgress = document.getElementById('storyProgress');
        this.storyTime = document.getElementById('storyTime');
        
        this.init();
    }
    
    init() {
        if (this.modal) {
            this.modal.addEventListener('show.bs.modal', (event) => {
                const button = event.relatedTarget;
                this.currentUserId = parseInt(button.dataset.userId);
                this.loadStories(this.currentUserId);
            });
            
            this.modal.addEventListener('hidden.bs.modal', () => {
                this.pauseStory();
                this.clearProgress();
            });
            
            // Add swipe events for mobile
            this.modal.addEventListener('touchstart', this.handleTouchStart.bind(this), false);
            this.modal.addEventListener('touchmove', this.handleTouchMove.bind(this), false);
            
            // Add keyboard events for desktop
            document.addEventListener('keydown', this.handleKeyDown.bind(this));
        }
    }
    
    loadStories(userId) {
        // In a real implementation, this would fetch stories from the server
        // For now, we'll use data attributes on the story elements
        const storyElements = document.querySelectorAll(`.story[data-user-id="${userId}"]`);
        this.stories = Array.from(storyElements).map(el => ({
            id: el.dataset.storyId,
            type: el.dataset.storyType,
            media: el.dataset.storyMedia,
            username: el.dataset.username,
            time: el.dataset.time
        }));
        
        if (this.stories.length > 0) {
            this.currentStoryIndex = 0;
            this.showStory();
        }
    }
    
    showStory() {
        if (this.stories.length === 0) return;
        
        const story = this.stories[this.currentStoryIndex];
        
        // Hide both media types first
        this.storyImage.style.display = 'none';
        this.storyVideo.style.display = 'none';
        
        if (story.type === 'image') {
            this.storyImage.style.display = 'block';
            this.storyImage.src = `/image/${story.media}`;
        } else if (story.type === 'video') {
            this.storyVideo.style.display = 'block';
            this.storyVideo.src = `/video/${story.media}`;
            this.storyVideo.play();
        }
        
        this.storyUsername.textContent = story.username;
        this.storyTime.textContent = formatRelativeTime(story.time);
        
        this.startProgress();
    }
    
    startProgress() {
        this.clearProgress();
        this.isPlaying = true;
        
        // Create progress bars for each story
        this.storyProgress.innerHTML = '';
        for (let i = 0; i < this.stories.length; i++) {
            const progressBar = document.createElement('div');
            progressBar.className = 'progress-bar';
            if (i < this.currentStoryIndex) {
                progressBar.classList.add('completed');
            }
            this.storyProgress.appendChild(progressBar);
        }
        
        // Animate current progress bar
        const currentProgressBar = this.storyProgress.children[this.currentStoryIndex];
        currentProgressBar.style.animation = 'progress 5s linear';
        
        // Set timeout to move to next story
        this.progressInterval = setTimeout(() => {
            this.nextStory();
        }, 5000);
    }
    
    pauseStory() {
        this.isPlaying = false;
        this.clearProgress();
        
        if (this.stories[this.currentStoryIndex].type === 'video') {
            this.storyVideo.pause();
        }
    }
    
    resumeStory() {
        if (this.stories[this.currentStoryIndex].type === 'video') {
            this.storyVideo.play();
        }
        this.startProgress();
    }
    
    clearProgress() {
        if (this.progressInterval) {
            clearTimeout(this.progressInterval);
            this.progressInterval = null;
        }
    }
    
    nextStory() {
        if (this.currentStoryIndex < this.stories.length - 1) {
            this.currentStoryIndex++;
            this.showStory();
        } else {
            this.closeModal();
        }
    }
    
    previousStory() {
        if (this.currentStoryIndex > 0) {
            this.currentStoryIndex--;
            this.showStory();
        }
    }
    
    closeModal() {
        const modal = bootstrap.Modal.getInstance(this.modal);
        modal.hide();
    }
    
    handleTouchStart(e) {
        this.touchStartX = e.touches[0].clientX;
        this.touchStartY = e.touches[0].clientY;
    }
    
    handleTouchMove(e) {
        if (!this.touchStartX || !this.touchStartY) return;
        
        const touchEndX = e.touches[0].clientX;
        const touchEndY = e.touches[0].clientY;
        
        const diffX = touchEndX - this.touchStartX;
        const diffY = touchEndY - this.touchStartY;
        
        // Horizontal swipe (next/previous story)
        if (Math.abs(diffX) > Math.abs(diffY)) {
            if (diffX > 50) {
                this.previousStory();
            } else if (diffX < -50) {
                this.nextStory();
            }
        }
        // Vertical swipe (close story)
        else if (diffY > 100) {
            this.closeModal();
        }
        
        // Reset touch coordinates
        this.touchStartX = null;
        this.touchStartY = null;
    }
    
    handleKeyDown(e) {
        if (e.key === 'ArrowRight') {
            this.nextStory();
        } else if (e.key === 'ArrowLeft') {
            this.previousStory();
        } else if (e.key === 'Escape') {
            this.closeModal();
        } else if (e.key === ' ') {
            if (this.isPlaying) {
                this.pauseStory();
            } else {
                this.resumeStory();
            }
        }
    }
}

// Initialize story viewer when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new StoryViewer();
});

// CSS animation for progress bar
const style = document.createElement('style');
style.textContent = `
    @keyframes progress {
        from { width: 0%; }
        to { width: 100%; }
    }
    
    .progress-bar {
        height: 3px;
        background-color: rgba(255, 255, 255, 0.4);
        flex-grow: 1;
        margin: 0 2px;
        border-radius: 2px;
        overflow: hidden;
    }
    
    .progress-bar.completed {
        background-color: rgba(255, 255, 255, 0.9);
    }
    
    .progress-bar:not(.completed) {
        background-color: rgba(255, 255, 255, 0.4);
    }
`;
document.head.appendChild(style);

// Chat functionality for SociaFam

class Chat {
    constructor() {
        this.chatContainer = document.getElementById('chatContainer');
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.messagesContainer = document.getElementById('messagesContainer');
        this.userId = null;
        this.pollingInterval = null;
        
        this.init();
    }
    
    init() {
        if (this.chatContainer) {
            this.userId = this.chatContainer.dataset.userId;
            
            // Add event listeners
            this.sendButton.addEventListener('click', this.sendMessage.bind(this));
            this.messageInput.addEventListener('keypress', this.handleKeyPress.bind(this));
            
            // Load initial messages
            this.loadMessages();
            
            // Start polling for new messages
            this.startPolling();
            
            // Scroll to bottom of chat
            this.scrollToBottom();
        }
    }
    
    sendMessage() {
        const content = this.messageInput.value.trim();
        
        if (!content) return;
        
        const formData = new FormData();
        formData.append('receiver_id', this.userId);
        formData.append('content', content);
        
        fetch('/send-message', {
            method: 'POST',
            body: formData,
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.messageInput.value = '';
                this.addMessage({
                    id: data.message_id,
                    content: content,
                    sender_id: parseInt(document.body.dataset.currentUserId),
                    receiver_id: parseInt(this.userId),
                    created_at: new Date().toISOString(),
                    is_read: true
                });
                
                this.scrollToBottom();
            }
        })
        .catch(error => {
            console.error('Error sending message:', error);
        });
    }
    
    handleKeyPress(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            this.sendMessage();
        }
    }
    
    loadMessages() {
        // Messages are already loaded in the template
        // This would be used if we were loading messages via AJAX
        this.scrollToBottom();
    }
    
    pollForNewMessages() {
        fetch(`/api/chat/${this.userId}`)
            .then(response => response.json())
            .then(messages => {
                // Check for new messages
                const lastMessageId = this.getLastMessageId();
                const newMessages = messages.filter(msg => msg.id > lastMessageId);
                
                if (newMessages.length > 0) {
                    newMessages.forEach(message => {
                        this.addMessage(message);
                    });
                    
                    this.scrollToBottom();
                }
            })
            .catch(error => {
                console.error('Error polling for messages:', error);
            });
    }
    
    startPolling() {
        this.pollingInterval = setInterval(() => {
            this.pollForNewMessages();
        }, 3000); // Poll every 3 seconds
    }
    
    stopPolling() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
    }
    
    addMessage(message) {
        const messageElement = this.createMessageElement(message);
        this.messagesContainer.appendChild(messageElement);
    }
    
    createMessageElement(message) {
        const isCurrentUser = message.sender_id === parseInt(document.body.dataset.currentUserId);
        const messageClass = isCurrentUser ? 'message sent' : 'message received';
        
        const div = document.createElement('div');
        div.className = messageClass;
        div.innerHTML = `
            <div class="message-content">${this.escapeHtml(message.content)}</div>
            <div class="message-time">${formatRelativeTime(message.created_at)}</div>
        `;
        
        return div;
    }
    
    getLastMessageId() {
        const lastMessage = this.messagesContainer.lastElementChild;
        if (lastMessage && lastMessage.dataset.messageId) {
            return parseInt(lastMessage.dataset.messageId);
        }
        return 0;
    }
    
    scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize chat when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new Chat();
});

// Add CSS for chat
const style = document.createElement('style');
style.textContent = `
    .chat-container {
        display: flex;
        flex-direction: column;
        height: 100%;
    }
    
    .messages-container {
        flex-grow: 1;
        overflow-y: auto;
        padding: 10px;
    }
    
    .message {
        margin-bottom: 10px;
        max-width: 70%;
    }
    
    .message.sent {
        align-self: flex-end;
        margin-left: auto;
    }
    
    .message.received {
        align-self: flex-start;
    }
    
    .message-content {
        padding: 10px;
        border-radius: 18px;
        margin-bottom: 5px;
    }
    
    .message.sent .message-content {
        background-color: #1877f2;
        color: white;
    }
    
    .message.received .message-content {
        background-color: #f0f2f5;
        color: #1c1e21;
    }
    
    .message-time {
        font-size: 12px;
        color: #65676b;
    }
    
    .chat-input {
        display: flex;
        padding: 10px;
        border-top: 1px solid #e4e6eb;
    }
    
    .chat-input input {
        flex-grow: 1;
        padding: 10px;
        border: 1px solid #dddfe2;
        border-radius: 20px;
        outline: none;
    }
    
    .chat-input button {
        margin-left: 10px;
        padding: 10px 15px;
        background-color: #1877f2;
        color: white;
        border: none;
        border-radius: 20px;
        cursor: pointer;
    }
`;
document.head.appendChild(style);

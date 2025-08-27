async function startChat(userId) {
    try {
        const response = await fetch('/api/start_chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId })
        });
        const result = await response.json();
        if (result.success) {
            window.location.href = result.chat_url;
        } else {
            alert(result.message);
        }
    } catch (error) {
        console.error('Error starting chat:', error);
        alert('Failed to start chat.');
    }
}

async function blockUser(userId) {
    if (confirm('Are you sure you want to block this user?')) {
        try {
            const response = await fetch('/api/block_user', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ blocked_id: userId })
            });
            const result = await response.json();
            if (result.success) {
                location.reload();
            } else {
                alert(result.message);
            }
        } catch (error) {
            console.error('Error blocking user:', error);
            alert('Failed to block user.');
        }
    }
}

async function unfollow(userId) {
    if (confirm('Are you sure you want to unfollow this user?')) {
        try {
            const response = await fetch('/api/unfollow_user', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: userId })
            });
            const result = await response.json();
            if (result.success) {
                location.reload();
            } else {
                alert(result.message);
            }
        } catch (error) {
            console.error('Error unfollowing user:', error);
            alert('Failed to unfollow user.');
        }
    }
}

async function acceptRequest(friendshipId) {
    try {
        const response = await fetch('/api/accept_friend_request', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ friendship_id: friendshipId })
        });
        const result = await response.json();
        if (result.success) {
            location.reload();
        } else {
            alert(result.message);
        }
    } catch (error) {
        console.error('Error accepting request:', error);
        alert('Failed to accept friend request.');
    }
}

async function declineRequest(friendshipId) {
    try {
        const response = await fetch('/api/decline_friend_request', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ friendship_id: friendshipId })
        });
        const result = await response.json();
        if (result.success) {
            location.reload();
        } else {
            alert(result.message);
        }
    } catch (error) {
        console.error('Error declining request:', error);
        alert('Failed to decline friend request.');
    }
}

async function followUser(userId) {
    try {
        const response = await fetch('/api/follow_user', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId })
        });
        const result = await response.json();
        if (result.success) {
            location.reload();
        } else {
            alert(result.message);
        }
    } catch (error) {
        console.error('Error following user:', error);
        alert('Failed to follow user.');
    }
}

async function removeSuggested(userId) {
    try {
        const response = await fetch('/api/remove_suggested_user', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ dismissed_user_id: userId })
        });
        const result = await response.json();
        if (result.success) {
            location.reload();
        } else {
            alert(result.message);
        }
    } catch (error) {
        console.error('Error removing suggested user:', error);
        alert('Failed to remove suggested user.');
    }
}

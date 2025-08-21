# SociaFam

SociaFam is a social networking platform inspired by Facebook, Instagram, and WhatsApp. It enables users to connect, share posts, stories, and reels, chat in real-time, play games, join groups, attend events, and more. Built with Flask (backend), HTML/CSS/JavaScript (frontend), and SQLite (database), it prioritizes simplicity, security, and user experience.

## Features
- User profiles with customizable bios and photos
- Friendships (add, accept, decline requests)
- Real-time chat, voice/video calls, and status updates
- Feeds with posts, stories, and reels
- Groups, events, marketplace, and games
- Admin dashboard for user/content management
- Secure authentication with JWT and 2FA
- Responsive design with accessibility features (dark mode, multi-language)

## Prerequisites
- Python 3.10+
- Git

## Setup Instructions
1. Clone the repository:
git clone <repository-url>
cd sociafam</repository-url>
text2. Set up Python virtual environment:
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
text3. Install dependencies:
pip install -r requirements.txt
text4. Create a `.env` file in the root directory with:
FLASK_SECRET_KEY=your-secret-key-here
textGenerate a secret key: `python -c 'import secrets; print(secrets.token_hex(32))'`
5. Initialize the SQLite database:
python app.py
text(This creates `sociafam.db` on first run.)
6. Start the Flask server:
python app.py
text7. Access the app at `http://127.0.0.1:5000`.

## Development Phases
1. **Phase 1**: Setup, authentication (login/signup/2FA), core structure
2. **Phase 2**: Profiles, friendships
3. **Phase 3**: Posts, stories, reels
4. **Phase 4**: Real-time chat, notifications
5. **Phase 5**: Groups, events, marketplace, games
6. **Phase 6**: Admin tools, analytics
7. **Phase 7**: Polish, testing, deployment prep

## Contributing
Contributions are welcome! Submit a pull request or open an issue.

## License
MIT License

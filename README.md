# SociaFam

SociaFam is a comprehensive social networking platform inspired by Facebook, Instagram, and WhatsApp. It allows users to connect, share posts, stories, and reels, chat in real-time, play games, join groups, attend events, and more. Built with Django (backend), React (frontend), and MySQL (database), it emphasizes security, scalability, and user experience.

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
- Node.js 18+
- MySQL 8+
- Git

## Setup Instructions
1. Clone the repository:
git clone <repository-url>
cd sociafam</repository-url>
text2. Set up Python virtual environment:
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
text3. Install backend dependencies:
pip install -r requirements.txt
text4. Set up MySQL database:
mysql -u root -p
CREATE DATABASE sociafam_db;
text5. Configure `backend/settings.py` with your MySQL credentials.
6. Run migrations and create superuser:
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
text7. Install frontend dependencies:
cd frontend
npm install
text8. Start backend server:
cd ../
python manage.py runserver
text9. Start frontend server (in another terminal):
cd frontend
npm start
text## Access
- Backend: http://127.0.0.1:8000
- Frontend: http://localhost:3000
- Admin: http://127.0.0.1:8000/admin

## Development Phases
1. **Phase 1**: Setup, authentication (login/signup/2FA), core structure
2. **Phase 2**: Profiles, friendships
3. **Phase 3**: Posts, stories, reels
4. **Phase 4**: Real-time chat, notifications
5. **Phase 5**: Groups, events, marketplace, games
6. **Phase 6**: Admin tools, analytics
7. **Phase 7**: Polish, testing, deployment prep

## Contributing
Contributions are welcome! Please submit a pull request or open an issue.

## License
MIT License (or specify your preferred license)

# StudyHub - Online Collaborative Study Platform

A modern, full-stack collaborative learning platform built with Flask, SQLite, and vanilla JavaScript. Students can study together, share materials, ask doubts, join study groups, take quizzes, and track their progress with AI-powered recommendations.

## Features

### Core Features
- **Study Materials** - Upload, share, rate, and download notes, PDFs, and documents
- **Doubts & Answers** - Post questions, get answers, mark accepted solutions
- **Discussions** - Threaded conversations with replies, pinning, and locking
- **Study Groups** - Create/join groups, share materials, group discussions
- **Quizzes & MCQs** - Timed quizzes with instant scoring and explanations
- **Progress Tracking** - Visual dashboards with charts and analytics
- **AI Recommendations** - Personalized content suggestions using scikit-learn

### Technical Features
- **Secure Authentication** - Registration, login, password hashing, session management
- **Authorization** - Role-based access control, ownership validation
- **File Upload Security** - Validation, sanitization, safe storage
- **Responsive Design** - Mobile-first, works on all devices
- **Accessibility** - Semantic HTML, keyboard navigation, ARIA labels
- **Real-time UI** - Toast notifications, modals, dynamic content

## Tech Stack

### Frontend
- HTML5, CSS3, Vanilla JavaScript (ES6+)
- Tailwind CSS for styling
- Lucide Icons
- Chart.js for progress visualizations

### Backend
- Python 3.8+
- Flask 3.0
- Flask-SQLAlchemy 3.1
- Flask-Login 0.6
- Flask-WTF 1.2
- Werkzeug 3.0

### Database
- SQLite (development)
- Compatible with PostgreSQL/MySQL for production

### AI/ML
- Python scikit-learn
- TF-IDF vectorization
- Cosine similarity for content-based filtering
- Collaborative filtering for peer-based recommendations

## Project Structure

```
study_platform/
├── app.py                 # Application entry point
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── README.md              # This file
├── database/
│   └── __init__.py        # Database initialization
├── models/
│   └── __init__.py        # Database models
├── routes/
│   ├── __init__.py
│   ├── auth.py            # Authentication routes
│   ├── dashboard.py       # Dashboard routes
│   ├── subjects.py        # Subject browsing
│   ├── materials.py       # Study materials
│   ├── doubts.py          # Doubts & answers
│   ├── discussions.py     # Discussions
│   ├── groups.py          # Study groups
│   ├── quizzes.py         # Quizzes & MCQs
│   ├── search.py          # Global search
│   ├── progress.py        # Progress tracking
│   └── api.py             # API endpoints
├── services/
│   ├── __init__.py
│   ├── file_service.py    # File handling
│   ├── auth_service.py    # Authentication logic
│   └── recommendation_service.py  # AI recommendations
├── ai/
│   └── __init__.py        # ML utilities
├── templates/
│   ├── base.html          # Base template
│   ├── landing.html       # Landing page
│   ├── partials/          # Reusable components
│   ├── auth/              # Auth templates
│   ├── dashboard/         # Dashboard templates
│   ├── subjects/          # Subject templates
│   ├── materials/         # Material templates
│   ├── doubts/            # Doubt templates
│   ├── discussions/       # Discussion templates
│   ├── groups/            # Group templates
│   ├── quizzes/           # Quiz templates
│   ├── search/            # Search templates
│   ├── progress/          # Progress templates
│   └── errors/            # Error pages
├── static/
│   ├── css/               # Custom styles
│   ├── js/                # JavaScript modules
│   └── images/            # Static images
└── uploads/
    ├── materials/         # Uploaded files
    └── avatars/           # User avatars
```

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- Git (optional)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd study_platform
   ```

2. **Create a virtual environment**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate
   
   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables** (optional)
   ```bash
   # Create .env file
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Initialize the database**
   ```bash
   python -c "from app import create_app; from database import init_db; app = create_app(); init_db(app)"
   ```
   Or simply run the app once - it will auto-create tables and seed initial subjects.

6. **Run the application**
   ```bash
   python app.py
   ```

7. **Access the application**
   Open http://localhost:5000 in your browser

## Configuration

### Environment Variables
| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key | Auto-generated |
| `DATABASE_URL` | Database connection string | `sqlite:///study_platform.db` |
| `FLASK_ENV` | Environment mode | `development` |

### Configuration Options (config.py)
- `MAX_CONTENT_LENGTH` - Max upload size (default: 16MB)
- `ALLOWED_EXTENSIONS` - Allowed file types
- `SESSION_COOKIE_*` - Session security settings
- `RATE_LIMIT_*` - Rate limiting configuration

## Usage

### For Students
1. **Register** - Create an account with email and password
2. **Browse Subjects** - Explore available subjects
3. **Upload Materials** - Share notes, PDFs, and resources
4. **Ask Doubts** - Post questions, get community help
5. **Join Discussions** - Participate in threaded conversations
6. **Create/Join Groups** - Collaborate with peers
7. **Take Quizzes** - Test knowledge with timed MCQs
8. **Track Progress** - View analytics and AI recommendations

### For Developers
- **Adding Models** - Define in `models/__init__.py`, run migration
- **New Routes** - Create in `routes/`, register in `app.py`
- **Services** - Business logic in `services/`
- **Templates** - Extend `base.html`, use partials
- **Static Assets** - Add to `static/`

## AI Recommendation System

The recommendation engine uses scikit-learn to provide personalized suggestions:

### Algorithm
1. **Content-Based Filtering** - TF-IDF vectorization of material/quiz content
2. **Collaborative Filtering** - User similarity based on activity overlap
3. **Weak Area Detection** - Identifies subjects with low quiz scores
4. **Cold Start Handling** - Popular content for new users

### Training
- Runs automatically on first request
- Retrains daily or on manual refresh
- Processes user activity: views, ratings, quiz attempts, progress

### API Endpoint
```bash
POST /api/recommendations/refresh
```
Returns personalized materials, quizzes, and subject suggestions.

## Security

### Implemented Protections
- **Password Hashing** - Werkzeug's PBKDF2 with SHA-256
- **CSRF Protection** - Flask-WTF on all forms
- **SQL Injection Prevention** - SQLAlchemy ORM parameterized queries
- **XSS Prevention** - Jinja2 auto-escaping
- **File Upload Validation** - Extension, MIME type, size checks
- **Secure Sessions** - HttpOnly, SameSite, secure cookies
- **Authorization Checks** - Server-side ownership validation
- **Rate Limiting** - Configurable limits on auth endpoints

### Best Practices
- Never commit secrets to version control
- Use environment variables for configuration
- Keep dependencies updated
- Run security audits regularly

## Development

### Running Tests
```bash
# Install test dependencies
pip install pytest pytest-cov

# Run tests
pytest tests/ -v --cov
```

### Code Style
```bash
# Format with Black
black .

# Lint with Flake8
flake8 .
```

### Database Migrations
```bash
# Install Flask-Migrate
pip install Flask-Migrate

# Initialize
flask db init

# Create migration
flask db migrate -m "Description"

# Apply
flask db upgrade
```

## Deployment

### Production Checklist
- [ ] Set `FLASK_ENV=production`
- [ ] Use strong `SECRET_KEY`
- [ ] Configure PostgreSQL/MySQL database
- [ ] Set up reverse proxy (Nginx)
- [ ] Enable HTTPS with SSL certificates
- [ ] Configure proper logging
- [ ] Set up monitoring/alerting
- [ ] Run database migrations
- [ ] Collect static files if using CDN

### Docker (Optional)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:create_app()"]
```

## Future Improvements

### Planned Features
- [ ] Real-time notifications with WebSockets
- [ ] Rich text editor for content
- [ ] Video/audio material support
- [ ] Gamification (badges, leaderboards)
- [ ] Mobile app (React Native/Flutter)
- [ ] Advanced analytics dashboard
- [ ] Multi-language support
- [ ] Offline mode with service workers
- [ ] Integration with LMS platforms
- [ ] AI-powered quiz generation

### Technical Debt
- [ ] Add comprehensive test suite
- [ ] Implement API versioning
- [ ] Add database migration system
- [ ] Improve error logging/aggregation
- [ ] Add CI/CD pipeline
- [ ] Implement caching (Redis)
- [ ] Add search indexing (Elasticsearch)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For issues and feature requests, please use the GitHub issue tracker.

---

Built with ❤️ for students everywhere. Happy learning!
# Sarovar South Spice — AI Restaurant Concierge

An AI-powered restaurant chatbot built with Flask, Groq LLM (Llama 3.1), and PostgreSQL (Neon). Features natural language conversations, real-time table reservations, interactive menu browsing, and a modern responsive UI.

**Live Demo:** [(https://your-app-url.vercel.app](https://finance-tracker-ashy-iota.vercel.app))

## Features

- **AI-Powered Chat** — Natural conversations via Groq LLM with rule-based intent fallback for 100% response coverage
- **Table Reservations** — Book tables with name, date, time, party size, and special requests — persisted in PostgreSQL
- **Interactive Menu** — Browse categorized menu with dietary filters (Veg, Vegan, Spicy, Bestsellers)
- **Voice Input** — Speech-to-text using Web Speech API
- **Dark/Light Theme** — Toggle with persistent preference
- **Conversation Rating** — 5-star feedback system stored in database
- **Session Memory** — Context-aware multi-turn conversations

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Flask, Python |
| AI/NLP | Groq API, Llama 3.1 8B |
| Database | PostgreSQL (Neon Serverless) |
| Frontend | HTML, CSS, JavaScript |
| Deployment | Vercel (Serverless) |

## Architecture

```
User → Chat UI → Flask API → Intent Detection
                                ├── Groq LLM (primary)
                                └── Rule-based (fallback)
                           → PostgreSQL (Neon)
                                ├── Bookings
                                ├── Menu Items
                                └── Ratings
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Serve chat interface |
| POST | `/chat` | Send message, get AI response |
| GET | `/menu` | Get menu items (supports `?category=` and `?veg=true` filters) |
| GET | `/menu/categories` | Get all menu categories |
| POST | `/book` | Create a table reservation |
| GET | `/booking/<id>` | Look up booking by ID |
| POST | `/rate` | Submit conversation rating |
| GET | `/test` | Health check (LLM & DB status) |

## Setup

### Prerequisites
- Python 3.10+
- [Neon](https://neon.tech) PostgreSQL account (free tier)
- [Groq](https://console.groq.com) API key (free tier)

### Local Development

```bash
git clone https://github.com/your-username/sarovar-chatbot.git
cd sarovar-chatbot
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file:
```
DATABASE_URL=postgresql://user:pass@ep-xxx.neon.tech/dbname?sslmode=require
GROQ_API_KEY=your_groq_api_key
SECRET_KEY=any_random_string
```

Run:
```bash
python app.py
```

### Deploy to Vercel

1. Push code to GitHub
2. Import repo in [Vercel](https://vercel.com)
3. Add environment variables: `DATABASE_URL`, `GROQ_API_KEY`, `SECRET_KEY`
4. Deploy — database tables auto-initialize on first request

## Project Structure

```
├── app.py              # Flask backend, routes, LLM & DB logic
├── full.json           # Intent patterns for rule-based fallback
├── requirements.txt    # Python dependencies
├── runtime.txt         # Python version for Vercel
├── vercel.json         # Vercel deployment config
└── static/
    ├── index.html      # Chat UI
    ├── style.css       # Styling
    └── *.webp/jpeg     # Avatar & logo assets
```

## License

MIT

# Blog API

A full-featured blog API built with FastAPI, PostgreSQL, and Redis.

## Features

- **User Authentication**: Register, login, JWT tokens
- **Posts**: Create, read, update, delete posts with categories
- **Comments**: Nested comments on posts
- **Favorites/Likes**: Like posts and save to favorites
- **Follow System**: Follow other users
- **Search**: Full-text search for posts and users
- **Admin Panel**: Administrative functions and statistics
- **REST API**: Fully documented with OpenAPI/Swagger
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Caching**: Redis for caching frequent queries
- **Docker**: Containerized deployment
- **Testing**: Comprehensive test suite

## Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker (optional)

## Quick Start

### With Docker (Recommended)

```bash

git clone <repository-url>
cd blog-project

cp .env.example .env

docker-compose -f docker/docker-compose.yml up --build

# http://localhost:8000
# http://localhost:8000/api/docs
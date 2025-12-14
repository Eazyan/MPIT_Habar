# 🚀 RezonansAI — ИИ-Ньюсмейкер

> **Преврати одну новость в неделю контента на всех платформах**

AI-агент для PR-специалистов и маркетологов: автоматический анализ новостей, генерация адаптированного контента для 7+ платформ, умный PR-ассистент с поддержкой нескольких LLM-моделей.

---

## 📋 Тизер

**RezonansAI** — это автономный ИИ-агент, который находит суть в любой новости и превращает её в готовый медиаплан для всех площадок. Один клик — и у вас посты для Telegram, VK, VC, Dzen, TenChat, Email-рассылки и пресс-релиза. 

**Стек разработки:** Python (FastAPI, LangGraph, LangChain), Next.js 14, TypeScript, PostgreSQL, Redis, ChromaDB, MinIO, Docker, Telegram Bot API. Поддержка Claude, DeepSeek, Qwen и локальных моделей через Ollama.

---

## ✨ Ключевые возможности

### 🎯 Основной функционал
| Функция | Описание |
|---------|----------|
| **Анализ новостей** | Извлечение фактов, цитат, цифр, определение тональности |
| **PR-вердикт** | Автоматическое решение: Отвечать / Игнорировать / Newsjack |
| **Мульти-платформенность** | Telegram, VK, VC, Dzen, TenChat, Email, Пресс-релиз |
| **Генерация изображений** | AI-картинки через Pollinations.ai |
| **Публикация** | Отправка в Telegram, VK Share, Email (mailto:) |

### 🧠 Умные фичи
| Функция | Описание |
|---------|----------|
| **Newsjacking** | Поиск креативных связей даже с нерелевантными новостями |
| **RAG-память** | Лайкнутые посты обучают систему вашему стилю |
| **Brand Profile** | Персонализация под голос и ценности бренда |
| **Категоризация** | CRISIS / PRODUCT / COMPETITOR / ROUTINE |
| **Режим Blogger vs PR** | Анализ чужого бренда или написание от лица своего |

### ⚡ Технические преимущества
| Функция | Описание |
|---------|----------|
| **Мульти-модель** | Claude, DeepSeek, Qwen, Ollama (офлайн) |
| **Multi-tenant** | Изоляция данных между пользователями |
| **Async LangGraph** | Асинхронный граф агентов для параллельной обработки |
| **Deep Linking** | Привязка Telegram через 6-значный код |

---

## 🏗️ Архитектура

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Frontend      │     │   Telegram      │     │   External      │
│   (Next.js)     │     │   Bot           │     │   LLMs          │
│   Port: 3000    │     │   (aiogram)     │     │   Claude/Qwen   │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │      Backend API        │
                    │      (FastAPI)          │
                    │      Port: 8000         │
                    └────────────┬────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
┌────────▼────────┐   ┌─────────▼─────────┐   ┌─────────▼─────────┐
│   PostgreSQL    │   │      Redis        │   │    ChromaDB       │
│   (Users, Auth) │   │   (Task Queue)    │   │   (RAG Vector)    │
│   Port: 5432    │   │   Port: 6379      │   │   Port: 8001      │
└─────────────────┘   └───────────────────┘   └───────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │       MinIO (S3)        │
                    │   (History, Knowledge)  │
                    │   Port: 9000/9001       │
                    └─────────────────────────┘
```

### Граф LangGraph агентов

```
[START] → [Analyzer] → [Context/RAG] → [Writer] → [Visual] → [END]
              │              │             │           │
              ▼              ▼             ▼           ▼
         Факты, Цитаты   Похожие      7 постов   AI-картинка
         Sentiment       Кейсы        для СМИ    Pollinations
         PR-вердикт
```

---

## 🛠️ Технологический стек

### Backend
- **FastAPI** — асинхронный REST API
- **LangGraph** — оркестрация AI-агентов  
- **LangChain** — интеграция LLM
- **SQLAlchemy** — ORM для PostgreSQL
- **Pydantic** — валидация данных
- **BeautifulSoup** — парсинг веб-страниц

### Frontend
- **Next.js 14** — React фреймворк с App Router
- **TypeScript** — типизация
- **Framer Motion** — анимации
- **TailwindCSS-like** — стилизация (Vanilla CSS)

### Telegram Bot
- **aiogram 3** — асинхронный Telegram Bot API
- **Redis PubSub** — уведомления в реальном времени

### Инфраструктура
- **Docker Compose** — оркестрация контейнеров
- **PostgreSQL** — основная БД (пользователи, auth)
- **Redis** — очередь задач, кэш
- **ChromaDB** — векторная БД для RAG
- **MinIO** — S3-совместимое хранилище

### AI/LLM
- **Claude 3.5 Sonnet** — основная модель (Anthropic)
- **Qwen 2.5 72B** — альтернатива через OpenRouter
- **DeepSeek** — альтернатива через OpenRouter
- **Ollama** — локальные модели (офлайн-режим)

---

## 🚀 Быстрый старт

### Требования
- Docker & Docker Compose
- API ключ Anthropic (Claude) или OpenRouter
- Telegram Bot Token (от @BotFather)

### Установка

```bash
# 1. Клонировать репозиторий
git clone https://github.com/your-username/rezonans-ai.git
cd rezonans-ai

# 2. Создать .env файл
cp .env.example .env

# 3. Заполнить обязательные переменные в .env:
#    - ANTHROPIC_API_KEY
#    - BOT_TOKEN
#    - POSTGRES_PASSWORD
#    - MINIO_ROOT_PASSWORD
#    - SECRET_KEY

# 4. Запустить все сервисы
docker compose up -d --build

# 5. Открыть в браузере
open http://localhost:3000
```

### Первый запуск

1. **Регистрация** — создайте аккаунт на http://localhost:3000
2. **Настройки бренда** — заполните профиль компании (имя, описание, tone of voice)
3. **Привязка Telegram** — нажмите "Подключить Telegram" в шапке
4. **Генерация** — вставьте URL новости и нажмите "Сгенерировать"

---

## 📁 Структура проекта

```
rezonans-ai/
├── backend/                 # FastAPI Backend
│   ├── app/
│   │   ├── agents/          # LangGraph агенты
│   │   │   ├── analyzer.py  # Анализ новостей
│   │   │   ├── writer.py    # Генерация постов
│   │   │   ├── visual.py    # Генерация изображений
│   │   │   ├── graph.py     # Граф агентов
│   │   │   └── state.py     # Состояние графа
│   │   ├── auth/            # Аутентификация
│   │   │   ├── models.py    # SQLAlchemy модели
│   │   │   ├── router.py    # Auth endpoints
│   │   │   └── utils.py     # JWT, хеширование
│   │   ├── rag/             # RAG система
│   │   │   └── store.py     # ChromaDB клиент
│   │   ├── main.py          # FastAPI app
│   │   ├── models.py        # Pydantic модели
│   │   ├── llm_factory.py   # Фабрика LLM
│   │   ├── storage.py       # MinIO клиент
│   │   └── database.py      # PostgreSQL
│   ├── scripts/             # Утилиты
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                # Next.js Frontend
│   ├── app/                 # App Router
│   │   ├── page.tsx         # Главная страница
│   │   ├── plan/[id]/       # Страница медиаплана
│   │   └── auth/            # Страницы авторизации
│   ├── components/          # React компоненты
│   ├── lib/                 # Утилиты (API, Auth)
│   └── Dockerfile
│
├── bot/                     # Telegram Bot
│   ├── main.py              # Основная логика
│   └── Dockerfile
│
├── docker-compose.yml       # Оркестрация
├── .env.example             # Шаблон переменных
└── README.md
```

---

## 🔐 Переменные окружения

| Переменная | Обязательно | Описание |
|------------|-------------|----------|
| `ANTHROPIC_API_KEY` | ❌ | Ключ API Claude |
| `BOT_TOKEN` | ✅ | Токен Telegram бота |
| `POSTGRES_PASSWORD` | ✅ | Пароль PostgreSQL |
| `MINIO_ROOT_PASSWORD` | ✅ | Пароль MinIO |
| `SECRET_KEY` | ✅ | Секрет для JWT |
| `OPENROUTER_API_KEY` | ❌ | Ключ OpenRouter (Qwen, DeepSeek) |
| `TAVILY_API_KEY` | ❌ | Ключ Tavily (поиск новостей) |

P.S. Обязательно наличие API любой LLM или локальной. Claude не обязателен и даже не рекомендуется из-за проблем с доступом. 

---

## 📱 Использование

### Веб-интерфейс

1. Вставьте URL новости
2. Выберите модель (Claude / Qwen / DeepSeek / Ollama)
3. Выберите режим (PR / Blogger)
4. Нажмите "Сгенерировать"
5. Получите медиаплан с 7 постами + изображением
6. Редактируйте, копируйте, публикуйте

### Telegram Bot

1. Отправьте `/start` боту @RezonansAI_bot
2. Привяжите аккаунт (если ещё не привязан)
3. Отправьте URL новости
4. Получите результат прямо в чате

### Настройка модели через бота

```
/config          # Открыть настройки
Выбрать модель   # Claude / Qwen / DeepSeek / Ollama
Выбрать режим    # PR / Blogger
```

---

## 🏆 Особенности реализации

### Newsjacking
Агент не просто анализирует релевантность — он активно ищет способы "захватить" новость для вашего бренда, даже если она напрямую не связана.

### RAG-обучение
Каждый лайкнутый пост сохраняется в векторную базу ChromaDB. При следующих генерациях система находит похожие успешные кейсы и использует их как примеры.

### Мульти-модельность
Переключайтесь между облачными (Claude, Qwen, DeepSeek) и локальными (Ollama) моделями без перезапуска. Идеально для тестирования и офлайн-работы.

### Изоляция данных
Каждый пользователь видит только свои генерации. Данные разделены на уровне PostgreSQL, MinIO и ChromaDB.

---

## 📄 Лицензия

MIT License — свободное использование с указанием авторства.

---

## 👥 Команда

Разработано для хакатона MPIT 2024.

---

<p align="center">
  <b>RezonansAI</b> — Дайте новостям вторую жизнь 🚀
</p>

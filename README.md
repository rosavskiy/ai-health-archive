# AI Health Archive — PWA (версия 5.0)

## Архитектура

```
healthsafe/
├── backend/          # FastAPI + Celery
│   ├── app/
│   │   ├── api/routes/       # auth, documents, metrics, ai_chat, notifications
│   │   ├── core/             # config, security (JWT, TOTP, bcrypt)
│   │   ├── db/               # SQLAlchemy models (deperсонализация)
│   │   ├── services/         # ai_shield, storage (AES-256), email_sync (IMAP)
│   │   └── tasks/            # Celery worker + beat
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/         # Next.js 14 + Tailwind CSS (PWA)
│   ├── src/app/      # consent, login, dashboard, archive, trends, chat
│   ├── public/       # manifest.json, sw.js (Service Worker)
│   └── Dockerfile
└── docker-compose.yml
```

## Быстрый старт

### 1. Настройка окружения
```bash
cp backend/.env.example backend/.env
# Заполните backend/.env: ключи Yandex Cloud, OpenAI, S3
```

### 2. Запуск через Docker Compose
```bash
docker-compose up --build
```

- API: http://localhost:8000/api/docs
- PWA: http://localhost:3000

### 3. Запуск для разработки (без Docker)

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# Celery worker:
celery -A app.tasks.worker.celery_app worker --loglevel=info
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Ключевые модули

### AI-Shield (OCR + маскирование)
`backend/app/services/ai_shield.py`

Pipeline: **Загрузка файла → Yandex Vision OCR → Regex PII mask → LLM mask + Extract → Сохранение деперсонализированных метрик**

### Схема БД (деперсонализация, 152-ФЗ)
`backend/app/db/models.py`

- `users` — только auth-данные (email, hashed_password, TOTP secret)
- `encrypted_docs` — зашифрованные документы в S3 + маскированный текст
- `metrics` — медицинские показатели только через UUID без ФИО

### IMAP Email Sync
`backend/app/services/email_sync.py`

Автоматически распознаёт письма от Invitro, Helix, CMD, Гемотест и других лабораторий и извлекает PDF-вложения.

### PWA
- `frontend/public/manifest.json` — манифест с иконками и категорией "health"
- `frontend/public/sw.js` — Service Worker: cache-first для статики, network-first для API, Push Notifications

## Безопасность

| Слой | Технология |
|------|-----------|
| Передача данных | HTTPS (TLS 1.3) |
| Хранение файлов | AES-256-GCM (client-side) + SSE (Yandex S3) |
| Пароли | bcrypt |
| Auth | JWT + 2FA TOTP |
| ПДн в LLM | Запрещено — только деперсонализированные показатели |
| Хранение данных | Исключительно РФ-серверы (Yandex Cloud / Selectel) |

## Соответствие 152-ФЗ

1. **Локализация** — все данные в РФ-контуре
2. **Акцепт при регистрации** — страница `/consent` с 3 чекбоксами (оферта, политика, согласие на спец. категории ПД)
3. **Деперсонализация** — ФИО, СНИЛС, полис заменяются на токены в БД
4. **Трансграничный запрет** — иностранные LLM получают только анонимизированный текст без связки личность+медданные

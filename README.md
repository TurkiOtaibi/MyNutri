# myNutri

Personal Arabic-first online nutrition tracker.

## Stack

- Backend: FastAPI, SQLModel, Alembic
- Database: PostgreSQL
- Frontend: Next.js, TypeScript, Tailwind CSS, Base UI
- Calc engine: Python pure functions with pytest coverage

## Local Development

1. Start PostgreSQL and the API container:

```powershell
docker compose -p mynutri up -d db api
```

2. Or run the backend directly during development:

```powershell
cd backend
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

3. Run the frontend:

```powershell
cd frontend
npm install
npm run dev
```

The app opens at `http://localhost:3000` and expects the API at `http://localhost:8000`.

## Verification

```powershell
cd backend
pytest

cd ..\\frontend
npm run typecheck
npm run build
```

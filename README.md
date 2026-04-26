# YomShishi 3x3 PWA

Closed-group app for managing Friday 3v3 basketball games with manual game creation, automatic waitlist logic, and push reminders.

## Architecture

- Frontend: React + Vite + TypeScript, mobile-first RTL Hebrew UI, installable PWA.
- Backend: Node.js + Express, SQLite-compatible storage via `sql.js` persisted to disk (`backend/data/yomshishi.sqlite`).
- Registration: one-time by name + email, user id stored in localStorage and used for future actions.
- Group policy: only pre-approved emails can register (`APPROVED_EMAILS`).
- Admin policy: any approved participant can create the next game, but only emails in `ADMIN_EMAILS` can edit or delete an existing game.

## Game Rules Implemented

- Games are created manually by participants and are not auto-created by the server.
- The player who creates a game is not auto-registered and must join like everyone else.
- Registration closes 24 hours before the game (`REGISTRATION_LEAD_HOURS`).
- At the registration deadline, a push reminder is sent automatically to everyone who installed the app and enabled push.
- OPEN: 0-5 players
- CONFIRMED: 6-9 players
- WAITING: 10-11 players (positions 10-11 in waiting list)
- LOCKED: 12 players (all must attend)
- On drop from 12 to 11, positions 10-11 return to waiting.

## Local Run (No Admin Required)

1. Backend:
   - Copy `backend/.env.example` to `backend/.env` and set values.
   - Run `npm install` in backend.
   - Run `npm run dev` in backend.
2. Frontend:
   - Copy `frontend/.env.example` to `frontend/.env`.
   - Set `VITE_API_BASE_URL`.
   - Run `npm install` in frontend.
   - Run `npm run dev` in frontend.

## Push Notifications

- Generate VAPID keys (example):
  - `npx web-push generate-vapid-keys`
- Put keys in `backend/.env`.
- The backend checks every few minutes for games whose 24-hour reminder time has arrived.
- Optional manual trigger endpoint: POST `/api/reminders/dispatch` with secret from `REMINDER_SECRET`.

## GitHub Pages

- Workflow: `.github/workflows/deploy-pages.yml`
- Required repository variable: `VITE_API_BASE_URL` (public backend URL).

## Contabo Deployment

- Workflow: `.github/workflows/deploy-contabo.yml`
- Add secrets:
  - `CONTABO_HOST`
  - `CONTABO_USER`
  - `CONTABO_SSH_KEY`

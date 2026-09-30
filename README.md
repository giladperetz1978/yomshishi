# YomShishi 3x3 PWA

Closed-group app for managing Friday 3v3 basketball games with manual game creation, automatic waitlist logic, and push reminders.

## Architecture

- Frontend: React + Vite + TypeScript, mobile-first RTL Hebrew UI, installable PWA.
- Backend: Node.js + Express, SQLite-compatible storage via `sql.js` persisted to disk (`backend/data/yomshishi.sqlite`).
- Authentication: Google Sign-In only (no password / no email verification flow in app).
- Session persistence: user id stored in localStorage for future actions.
- Group policy: only pre-approved emails can register (`APPROVED_EMAILS`).
- Admin policy: any approved participant can create the next game, but only emails in `ADMIN_EMAILS` can edit or delete an existing game.

## Game Rules Implemented

- Games are created manually by participants and are not auto-created by the server.
- The player who creates a game is not auto-registered and must join like everyone else.
- Registration remains open after the lottery; the game does not lock at the cutoff.
- The lottery runs automatically at 21:00 Israel time on the day before the game.
- OPEN: 0-5 players
- CONFIRMED: every registered player currently has a playing role
- Before the lottery, 10-11 players all remain in the playing role.
- Up to 9 players: everyone plays, with no lottery.
- 10-11 players after the lottery: one or two players wait, respectively.
- WAITING: one or more players are assigned to the late-arrival list.
- Exactly 12 players: everyone plays and any waiting status is cleared.
- After the lottery, new registrations are automatically assigned to the waiting list; players above position 12 wait automatically.
- Waiting players arrive about one hour after the game starts.
- Player profiles support an optional public photo, email, phone, and free-form details. Photos are resized in the browser and stored in the local SQLite database.
- Active players who have not registered for a game for two consecutive months are automatically deactivated by the server.
- An injury status exempts a player from inactivity cleanup until the selected injury end date. The end date can be extended from the injury screen.
- Active injured players and their injury end dates are displayed alongside each game roster.

## Local Run (No Admin Required)

1. Backend:
   - Copy `backend/.env.example` to `backend/.env` and set values.
   - Set `GOOGLE_CLIENT_ID` to the exact OAuth Web Client ID used by the frontend domain.
   - Run `npm install` in backend.
   - Run `npm run dev` in backend.
2. Frontend:
   - Copy `frontend/.env.example` to `frontend/.env`.
   - Keep `VITE_API_BASE_URL` empty when frontend is served from the same backend host.
   - Run `npm install` in frontend.
   - Run `npm run dev` in frontend.
   - The Vite development server proxies `/api` to the local backend at `http://localhost:8787`.

## Scheduled Lottery

- The backend checks upcoming games every minute.
- At 21:00 Israel time on the day before a game, it recalculates player roles and saves the roster snapshot.

## GitHub Pages

- Workflow: `.github/workflows/deploy-pages.yml`
- Required repository variable: `VITE_API_BASE_URL` (public backend URL).

## Contabo Deployment

- Workflow: `.github/workflows/deploy-contabo.yml`
- Add secrets:
  - `CONTABO_HOST`
  - `CONTABO_USER`
  - `CONTABO_SSH_KEY`

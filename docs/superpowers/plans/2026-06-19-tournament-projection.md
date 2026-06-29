# Tournament Projection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a dynamic 2026 World Cup group qualification and knockout simulation feature using real completed scores plus model predictions for unplayed matches.

**Architecture:** Add a backend tournament projection service as the single rules authority, expose it via a new API route, then render the projection in React with an interactive bracket. The service merges live/official match data, predicts missing group and knockout scores with the existing model, applies 2026 qualification rules, and simulates the tournament to a champion.

**Tech Stack:** FastAPI, Python unittest, existing `prediction_model.py`, React, TypeScript, Tailwind, lucide-react.

---

### Task 1: Backend Projection Service

**Files:**
- Create: `backend/services/tournament_projection.py`
- Create: `backend/tests/test_tournament_projection.py`

- [x] Write failing tests for mixed real/predicted group scoring, best third selection, official 2026 third-place routing for the A/B/C/D/E/G/I/J combination, and knockout simulation producing a champion.
- [x] Implement standings, best third ranking, Round of 32 pairing, and knockout simulation functions.
- [x] Run `backend\venv\Scripts\python.exe -m unittest backend.tests.test_tournament_projection`.

### Task 2: Backend API

**Files:**
- Create: `backend/routers/tournament.py`
- Modify: `backend/main.py`

- [x] Write a failing API test that `/api/v1/tournament/projection` returns groups, qualifiers, round-of-32 bracket, simulated rounds, and champion.
- [x] Register the router and wire the service to merged live matches.
- [x] Run the focused backend tests.

### Task 3: Frontend API And Page

**Files:**
- Modify: `frontend/src/services/api.ts`
- Create: `frontend/src/pages/TournamentPage.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Layout.tsx`

- [x] Add TypeScript contracts and `tournamentAPI.getProjection`.
- [x] Build a page with status cards, group qualifiers, best thirds, a polished bracket, and one-click simulate/refresh controls.
- [x] Add navigation route `/tournament`.

### Task 4: Verification

**Files:**
- Backend and frontend touched above.

- [x] Run `backend\venv\Scripts\python.exe -m unittest discover -s backend\tests`.
- [x] Run `npm run build` inside `frontend`.
- [x] Fix any failing test or build issue before handoff.

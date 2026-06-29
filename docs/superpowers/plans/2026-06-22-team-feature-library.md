# Team Feature Library Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a first-pass team feature library that turns completed-match stats and review signals into a bounded prediction calibration layer.

**Architecture:** Add a focused backend service that builds per-team profiles from completed matches before the target match date. Prediction routing passes a profile-based adjustment into `predict_match`, which applies small xG and draw-risk changes and returns an explainable `team_feature_adjustment` payload. Frontend prediction types and analysis cards expose the feature-library influence.

**Tech Stack:** Python services and unittest backend tests; FastAPI routes; React/TypeScript frontend types and existing prediction page UI.

---

### Task 1: Team Feature Service

**Files:**
- Create: `backend/services/team_feature_library.py`
- Test: `backend/tests/test_team_feature_library.py`

- [ ] Write failing tests for profile generation, red-card dampening, tactical tags, and future-match filtering.
- [ ] Implement `build_team_feature_library(matches, before=None)` and `build_match_feature_adjustment(current_match, matches)`.
- [ ] Keep sample windows small and weights bounded: one match is evidence, not a new base rating.

### Task 2: Prediction Integration

**Files:**
- Modify: `backend/routers/predictions.py`
- Modify: `backend/routers/reviews.py`
- Modify: `backend/services/prediction_model.py`
- Test: `backend/tests/test_prediction_team_features.py`

- [ ] Write failing tests that a round-two prediction includes `team_feature_adjustment`, feature notes, and bounded xG changes.
- [ ] Pass team feature adjustment from route-level live matches into `predict_match`.
- [ ] Apply only small calibration: attack deltas, draw delta, and feature notes.
- [ ] Include feature-library fields in current model backtest.

### Task 3: Frontend Visibility

**Files:**
- Modify: `frontend/src/services/api.ts`
- Modify: `frontend/src/pages/PredictPage.tsx`

- [ ] Add TypeScript types for `TeamFeatureAdjustment`.
- [ ] Show a compact prediction-page block listing profile notes and adjustment strength.
- [ ] Keep existing poster/export layout untouched in this MVP.

### Task 4: Verification

**Files:**
- Test commands only

- [ ] Run `python backend\tests\test_team_feature_library.py`.
- [ ] Run `python backend\tests\test_prediction_team_features.py`.
- [ ] Run existing review and prediction tests touched by this path.
- [ ] Run `npm run build` in `frontend`.

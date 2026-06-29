# Team Profile Memory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the persistent WC2026 team profile memory flow: completed matches write profiles, reviews show latest team features, predictions read profiles as `profile_adjustment`, and current-model backtests compare with vs without the profile library.

**Architecture:** Keep profile generation in `services.team_feature_library`, add a small JSON store beside prediction snapshots, and keep prediction calibration as a low-weight layer. Review endpoints become the synchronization point because they already aggregate completed official matches, while prediction endpoints read the stored profile first and fall back to in-memory generation when needed.

**Tech Stack:** FastAPI backend, Python `unittest`, React + TypeScript frontend.

---

### Task 1: Persistent Profile Store

**Files:**
- Modify: `backend/services/team_feature_library.py`
- Test: `backend/tests/test_team_feature_library.py`

- [ ] Add failing tests for `sync_team_profile_store`, `load_team_profile_store`, and `build_match_feature_adjustment(..., profile_store=...)`.
- [ ] Implement JSON store path via `TEAM_PROFILE_STORE_PATH`, defaulting to backend data path.
- [ ] Write completed-match profiles with `generated_at`, `match_count`, and `profiles`.
- [ ] Read stored profiles by team and apply target-date leakage guard using `last_match_date`.

### Task 2: Prediction API Profile Adjustment

**Files:**
- Modify: `backend/services/prediction_model.py`
- Modify: `backend/routers/predictions.py`
- Test: `backend/tests/test_reviews_api.py`

- [ ] Add failing API test requiring `profile_adjustment` in prediction response.
- [ ] Alias `team_feature_adjustment` to `profile_adjustment` in model output.
- [ ] Use stored profiles in `/predictions/predict`, while preserving fallback when store is empty.

### Task 3: Review Sync and Backtest Comparison

**Files:**
- Modify: `backend/routers/reviews.py`
- Modify: `backend/services/review_engine.py`
- Test: `backend/tests/test_reviews_api.py`

- [ ] Add failing test for `team_profiles` in review audit payload.
- [ ] Add failing test for `profile_comparison` in current-model backtest payload.
- [ ] Sync profile store whenever review audit/backtest runs.
- [ ] Build paired backtest summaries: `without_profile`, `with_profile`, and `delta`.

### Task 4: Frontend Display

**Files:**
- Modify: `frontend/src/services/api.ts`
- Modify: `frontend/src/pages/ReviewPage.tsx`
- Verify: `npm run build`

- [ ] Type `team_profiles` and `profile_comparison`.
- [ ] Add a compact review-page section showing latest profile cards for selected match teams.
- [ ] Add a compact comparison block for current-model backtest mode.

### Task 5: Verification and Runtime

**Files:**
- Run only.

- [ ] Run new focused backend tests.
- [ ] Run `python -m unittest discover backend/tests` from backend venv.
- [ ] Run frontend `npm run build`.
- [ ] Restart local backend and spot-check prediction/review endpoints.

# APSARA Project Export

APSARA is a password security platform with three parts:

- A FastAPI backend that handles authentication, password scoring, breach checks, and admin analytics
- A main frontend for end users to sign in, register, and analyze passwords
- An admin dashboard for viewing telemetry, scores, recent checks, and policy data

This repository is a flattened GitHub export of the most important runtime files from those apps.

## Why this repo is flat

The original project uses multiple nested app folders. For GitHub sharing, review, and quick browsing, the important files were copied into a single folder with no subfolders.

That makes the repository easier to read because:

- the core files are visible at a glance
- there is no deep folder traversal
- the main backend, frontend, and admin pieces are grouped by prefix instead of directory tree
- it is simpler to share the project as a clean code snapshot

## What is included

- Backend FastAPI entry points, routers, services, config, and models
- Main APSARA frontend pages, API routes, middleware, and shared component files
- Admin dashboard pages, API routes, middleware, and shared component files
- Minimal manifest/config files needed to understand each app

## What is not included

- Empty folders and sample-only assets
- Generated build output and cache folders
- Local secrets, env files, and backup folders

## File naming

The files are prefixed with `backend_`, `frontend_`, or `admin_` because this export is intentionally flat and contains no subfolders.

## Important note

This export is meant for GitHub sharing and code review. It is not the original runnable folder structure.

If you want to run the apps locally, use the original workspace layout in the parent project instead of this export.

## Push commands

```powershell
git remote add origin https://github.com/aadithyamahadev/APSARA-TBP-.git
git push -u origin main
```

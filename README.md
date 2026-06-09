# APSARA Project Export

This repository is a flattened, GitHub-friendly export of the core APSARA project files.

It is organized this way so the important runtime pieces are easy to review, share, and push to GitHub without the original nested app folders.

## What is included

- Backend FastAPI entry points, routers, services, config, and models
- Main APSARA frontend pages, API routes, middleware, and shared component files
- Admin dashboard pages, API routes, middleware, and shared component files
- Minimal manifest/config files needed to understand each app

## What is not included

- Empty folders and sample-only assets
- Generated build output and cache folders
- Local secrets, env files, and local backup folders

## File naming

The files are prefixed with `backend_`, `frontend_`, or `admin_` because this export is intentionally flat and contains no subfolders.

## Repo purpose

This export is meant for GitHub sharing and code review. It is not the original runnable folder structure.

If you want to run the apps locally, use the original workspace layout in the parent project instead of this export.

## Push commands

```powershell
git remote add origin https://github.com/aadithyamahadev/APSARA-TBP-.git
git push -u origin main
```

# APSARA Flat Export

This folder is a flattened export of the essential APSARA runtime files for GitHub sharing.

It contains:
- backend entry files and runtime helpers
- main frontend pages, routes, and shared components
- admin dashboard pages, routes, and shared components
- minimal config files needed to understand the stack

Notes:
- File names are prefixed because this folder is intentionally flat and contains no subfolders.
- This export is for sharing on GitHub. The original repo should be kept if you want the apps to run with their normal package structure.

## Push to GitHub

```powershell
git init
git add .
git commit -m "Initial flat export"
git branch -M main
git remote add origin <your-repo-url>
git push -u origin main
```

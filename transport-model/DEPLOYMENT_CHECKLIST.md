# Deployment Checklist - GitHub + Render

## Pre-Deployment Files ✅

All configuration files have been created for you:

- ✅ `.gitignore` - Prevents committing secrets and backup files
- ✅ `.env.example` - Template for environment variables
- ✅ `Procfile` - Tells Render to use gunicorn
- ✅ `requirements.txt` - Updated with gunicorn>=21.2.0
- ✅ `app.py` - Updated with proper PORT configuration for Render

---

## What to Deploy to GitHub

### ✅ YES - Deploy These Files (21 production files)

**Core Application (3 files):**
- app.py
- constants.py
- async_api_client.py

**Utils Package (5 files):**
- utils/__init__.py
- utils/helpers.py
- utils/conversions.py
- utils/api_helpers.py
- utils/ship_helpers.py

**Services Package (5 files):**
- services/__init__.py
- services/geocoding.py
- services/weather_service.py
- services/carbon_service.py
- services/openai_service.py

**Models Package (7 files):**
- models/__init__.py
- models/fuel_processes.py ⭐ (Phase 4)
- models/food_processes.py ⭐ (Phase 4)
- models/orchestration.py ⭐ (Phase 4)
- models/insurance_model.py
- models/ship_calculations.py
- models/capex_calculations.py

**Frontend (3 files - optional if hosted separately):**
- transport-model-new.html
- transport-model.js
- style.css

**Configuration (4 files):**
- requirements.txt
- Procfile
- .gitignore
- .env.example

### ❌ NO - Do NOT Deploy (automatically ignored by .gitignore)

- ❌ .env (has your secrets!)
- ❌ OG/ folder
- ❌ app_backup_before_integration.py
- ❌ app_before_phase3_step8.py
- ❌ app_before_phase4.py
- ❌ models/optimization.py (old file)
- ❌ models/fuel_processor.py (old file)
- ❌ models/fuel_processor_complete.py (old file)
- ❌ __pycache__/ folders
- ❌ *.pyc files

---

## Step-by-Step Deployment

### Step 1: Initialize Git (if not done)

```bash
cd C:\Users\eshan\OneDrive\Desktop\eshan-website\simbooni
git init
```

### Step 2: Verify .gitignore is Working

```bash
# Add .gitignore first
git add .gitignore

# Add all files
git add .

# Check what will be committed (verify .env is NOT included)
git status
```

**IMPORTANT:** Make sure `.env` does NOT appear in the list!

### Step 3: Make Initial Commit

```bash
git commit -m "Production deployment: Refactored modular LCA application

- 70-80% performance improvement
- Reduced app.py from 3,526 to 1,513 lines
- Extracted 28 process functions to domain modules
- Added proper Render configuration
- Production-ready with gunicorn"
```

### Step 4: Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `lca-transport-model` (or your choice)
3. Description: "LCA tool for fuel/food transport with modular architecture"
4. **DO NOT** initialize with README, .gitignore, or license
5. Click "Create repository"

### Step 5: Push to GitHub

```bash
# Replace YOUR_USERNAME with your actual GitHub username
git remote add origin https://github.com/YOUR_USERNAME/lca-transport-model.git
git branch -M main
git push -u origin main
```

### Step 6: Deploy to Render

1. **Go to Render Dashboard**
   - Visit: https://render.com/dashboard
   - Click "New +" → "Web Service"

2. **Connect Repository**
   - Select your GitHub account
   - Choose the repository you just created
   - Click "Connect"

3. **Configure Service**

   | Setting | Value |
   |---------|-------|
   | Name | `lca-transport-model` |
   | Region | Oregon (US West) or closest |
   | Branch | `main` |
   | Root Directory | *(leave blank)* |
   | Runtime | `Python 3` |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `gunicorn app:app` |
   | Instance Type | Free (or Starter $7/month) |

4. **Add Environment Variables**

   Click "Advanced" → Add these:

   | Key | Value |
   |-----|-------|
   | `GOOGLE_API_KEY` | (paste your Google API key) |
   | `OPENAI_API_KEY` | (paste your OpenAI API key) |
   | `PYTHON_VERSION` | `3.11.0` |

   **IMPORTANT:**
   - Get these values from your local `.env` file
   - Do NOT include quotes around the values
   - Make sure there are no extra spaces

5. **Deploy**
   - Click "Create Web Service"
   - Wait 5-10 minutes for first deployment
   - Monitor the logs for any errors

### Step 7: Test Deployment

Once you see "Your service is live 🎉":

1. **Copy the URL** (e.g., `https://lca-transport-model.onrender.com`)

2. **Test the Backend**
   ```bash
   # Should return something (not 404)
   curl https://your-app-name.onrender.com
   ```

3. **Update Frontend** (if needed)
   - Open `transport-model.js`
   - Find: `const API_URL = '...'`
   - Update to your new Render URL

4. **Test Full Workflow**
   - Open `transport-model-new.html` in browser
   - Fill out a simple calculation
   - Submit and verify results load

---

## Quick Verification Commands

### Before Pushing to GitHub

```bash
# Check what files will be committed
git status

# Verify .env is NOT listed
git status | grep .env
# Should output nothing or only .env.example

# Verify backup files are NOT listed
git status | grep -E "(OG|backup|before_phase)"
# Should output nothing
```

### After Pushing to GitHub

```bash
# Verify remote is set correctly
git remote -v

# Should show:
# origin  https://github.com/YOUR_USERNAME/REPO_NAME.git (fetch)
# origin  https://github.com/YOUR_USERNAME/REPO_NAME.git (push)
```

### After Render Deployment

Check logs for these success messages:
```
✅ "Successfully installed Flask..."
✅ "Build succeeded"
✅ "[STARTUP] Flask app initialized successfully"
✅ "API Keys status: Google=True, OpenAI=True"
✅ "Your service is live"
```

---

## Troubleshooting Quick Fixes

### Problem: `.env` file committed by mistake

```bash
# Remove from git (keeps local file)
git rm --cached .env
git commit -m "Remove .env from repository"
git push
```

### Problem: Import errors on Render

**Check:** Make sure all `__init__.py` files are present:
```bash
ls utils/__init__.py services/__init__.py models/__init__.py
```

### Problem: API keys not loading

**Fix:**
1. Go to Render dashboard
2. Your service → Environment
3. Verify keys are set (no quotes, no spaces)
4. Click "Save Changes"
5. Render will auto-restart

### Problem: Port binding error

**Fix:** Your `app.py` is already configured correctly! Shows:
```python
port = int(os.environ.get('PORT', 5000))
app.run(host='0.0.0.0', port=port, debug=debug_mode)
```

---

## What Changes to Make to Your Existing GitHub Repo

If you already have a GitHub repo for this project:

### Replace These Files:
1. ✅ `app.py` - New refactored version (1,513 lines)
2. ✅ All files in `models/` folder
3. ✅ All files in `utils/` folder
4. ✅ All files in `services/` folder

### Add These New Files:
1. ✅ `models/fuel_processes.py` (Phase 4)
2. ✅ `models/food_processes.py` (Phase 4)
3. ✅ `models/orchestration.py` (Phase 4)
4. ✅ `utils/api_helpers.py` (Phase 3)
5. ✅ `utils/ship_helpers.py` (Phase 3)
6. ✅ `.gitignore` (new)
7. ✅ `.env.example` (new)
8. ✅ `Procfile` (new)

### Update These Files:
1. ✅ `requirements.txt` - Add gunicorn>=21.2.0

### Commit and Push:
```bash
git add .
git commit -m "Deploy refactored application with modular architecture"
git push origin main
```

### Update Render:
- Render will auto-deploy from GitHub (if auto-deploy enabled)
- Or manually click "Deploy latest commit"

---

## Render Settings Checklist

### ✅ Required Settings (already configured)

1. **Build Command:** `pip install -r requirements.txt`
2. **Start Command:** `gunicorn app:app`
3. **Environment Variables:**
   - GOOGLE_API_KEY
   - OPENAI_API_KEY
   - PYTHON_VERSION (optional, defaults to 3.7)

### ❌ No Changes Needed

You do NOT need to:
- ❌ Change instance type (Free tier works fine)
- ❌ Add custom domains (optional)
- ❌ Configure health checks (Render does this automatically)
- ❌ Set up databases (not used in this app)

---

## Summary: What You Need to Do

### Quick 5-Step Process:

1. ✅ **Verify files** - All config files created ✓
2. ✅ **Git add/commit** - `git add . && git commit -m "Production deploy"`
3. ✅ **Create GitHub repo** - https://github.com/new
4. ✅ **Push to GitHub** - `git push -u origin main`
5. ✅ **Deploy on Render** - Connect repo, add env vars, deploy

**Total time:** ~10-15 minutes

---

## Your Files Are Ready! 🚀

All configuration files have been created:
- ✅ Procfile
- ✅ .gitignore
- ✅ .env.example
- ✅ requirements.txt (updated)
- ✅ app.py (updated with PORT config)

**You can now follow the steps above to deploy!**

For detailed instructions, see: [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)

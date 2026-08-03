# Bella's Bake Shop — Menu Board

A self-updating digital menu board. Runs entirely on GitHub's free tier —
no server, no monthly cost, nothing to maintain once it's set up.

- `index.html` — the board itself (loads `data/menu.json`, cycles through slides)
- `data/menu.json` — the current menu, refreshed automatically every night
- `scripts/sync_menu.py` — pulls prices/items from Square and rewrites `data/menu.json`
- `.github/workflows/nightly-sync.yml` — tells GitHub to run the script every night

## One-time setup (about 15 minutes)

**1. Create a GitHub account** (if you don't have one) at github.com — free.

**2. Create a new repository**
   - Click "New repository," name it something like `bellas-menu-board`
   - Keep it **Public** (required for free GitHub Pages hosting — the menu.json
     will be visible to anyone who looks, which is fine, it's just your public menu)
   - Upload all the files in this folder, keeping the same folder structure
     (drag-and-drop works on github.com, or use GitHub Desktop)

**3. Get a Square access token**
   - In your Square Developer Dashboard (developer.squareup.com), open your
     application, and get a **Production** access token with `ITEMS_READ` permission
   - Treat this like a password — don't share it or paste it anywhere public

**4. Add the token as a GitHub secret**
   - In your repo: Settings → Secrets and variables → Actions → New repository secret
   - Name: `SQUARE_ACCESS_TOKEN`
   - Value: paste the token from step 3
   - This keeps it private — it never appears in the code or the public site

**5. Turn on GitHub Pages**
   - In your repo: Settings → Pages
   - Source: "Deploy from a branch," Branch: `main`, folder: `/ (root)`
   - Save. GitHub will give you a URL like `https://yourusername.github.io/bellas-menu-board/`
   - That URL is what you point each screen's browser to

**6. Test the sync manually**
   - In your repo: Actions tab → "Nightly menu sync" → "Run workflow"
   - Wait about 30 seconds, refresh — `data/menu.json` should update with a
     fresh `synced_at` timestamp

After that, it runs on its own every night. No further steps.

## Changing the nightly time

Edit the `cron:` line in `.github/workflows/nightly-sync.yml`. It's in UTC.
Current setting runs at 3:10am UTC (~11:10pm Eastern).

## If a screen shows stale data

The board checks for a fresh `data/menu.json` once an hour on its own — no
reload needed. If something looks off, the Actions tab will show whether the
last nightly run succeeded or failed, and why.

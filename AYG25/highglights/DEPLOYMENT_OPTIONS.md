# Deployment Options for Highlights Widget

You have **3 options** for providing the widget to developers:

## Option 1: Static HTML Files (No API Deployment) ⭐ **RECOMMENDED**

**Best for:** Developers who want to host files themselves, no live data updates needed

**How it works:**
1. You run `generate_highlights.py` to create static HTML files
2. Developers download the HTML files from your `output/` folder
3. They host the files on their own server (any static hosting works)
4. **No API needed!**

**Pros:**
- ✅ No deployment required
- ✅ Works on any static hosting (GitHub Pages, Netlify, etc.)
- ✅ Fast loading (no API calls)
- ✅ Simple for developers

**Cons:**
- ❌ Requires regenerating HTML files when data changes
- ❌ Not live/real-time

**Usage:**
```bash
# You generate the files
python3 generate_highlights.py

# Developers download from output/ folder
# They host: highlights_2025-10-27.html, styles.css, etc.
```

---

## Option 2: Deploy API (Live Data) 

**Best for:** When you want live, real-time updates from Google Sheets

**How it works:**
1. Deploy `widget_server.py` to a hosting service
2. Developers embed the widget that fetches live data from your API
3. Data updates automatically when Google Sheet changes

**Pros:**
- ✅ Live data (updates automatically)
- ✅ Single source of truth
- ✅ Developers just embed, don't host files

**Cons:**
- ❌ Requires deployment setup
- ❌ Ongoing server costs/maintenance
- ❌ Slightly slower (API calls)

**Deployment Options:**
- **Google Cloud Run** (free tier available)
- **Heroku** (free tier available)
- **Railway** (free tier available)
- **AWS Lambda** (serverless)
- **DigitalOcean App Platform**

**Quick Deploy Example (Google Cloud Run):**
```bash
# Install gcloud CLI, then:
gcloud run deploy highlights-widget \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

---

## Option 3: Hybrid (Static Widget + API)

**Best for:** Flexibility - developers can choose static or live

**How it works:**
1. Provide both static HTML files AND the API
2. Developers choose based on their needs
3. Static for simple hosting, API for live updates

**Pros:**
- ✅ Maximum flexibility
- ✅ Best of both worlds

**Cons:**
- ❌ More setup/management

---

## Recommendation

**For most use cases, Option 1 (Static Files) is best because:**

1. **No deployment needed** - Just run the script and share files
2. **Simple for developers** - They just download and host HTML
3. **Works everywhere** - Any static hosting (even a simple web server)
4. **Fast** - No API latency

You can always add the API later if you need live updates!

---

## Quick Comparison

| Feature | Static Files | API Deployment |
|---------|--------------|----------------|
| Setup Complexity | ⭐ Easy | ⭐⭐⭐ Requires deployment |
| Live Updates | ❌ No | ✅ Yes |
| Speed | ⚡ Very Fast | ⚡ Fast (depends on API) |
| Server Costs | 💰 Free | 💰 Small (~$5-20/month) |
| Developer Setup | ⭐ Very Easy | ⭐⭐ Easy (just embed) |
| Maintenance | ⭐ Low | ⭐⭐ Medium |

---

## Next Steps

1. **Start with Static Files** - Use `generate_highlights.py` (already works!)
2. **If you need live updates later** - Deploy the API using Option 2
3. **Share the files** - Developers get the HTML files from `output/` folder


"""
Rupeewa News Daily — Admin Backend
FastAPI application with admin panel, API endpoints, and analytics tracking.
"""

import os
import sys
import json
import subprocess
import hashlib
import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func

# Add backend dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import (
    init_db, get_db, AdminUser, ArticleOverride, Source,
    SiteSetting, NewsletterSubscriber, BuildLog, PageVisit
)
from auth import (
    verify_password, hash_password, create_access_token,
    get_current_user, init_admin_user
)

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent  # rocket-tech/
PROJECT_DIR = BASE_DIR
BUILD_SCRIPT = PROJECT_DIR / "build.py"
BACKEND_DIR = BASE_DIR / "backend"

app = FastAPI(
    title="Rupeewa News Daily Admin",
    description="Admin panel and API for Rupeewa News Daily",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/admin/static", StaticFiles(directory=str(BACKEND_DIR / "static")), name="admin_static")

# Templates
templates_dir = BACKEND_DIR / "templates"


# ─── HELPERS ───────────────────────────────────────────────────────

def get_setting(db: Session, key: str, default: str = "") -> str:
    """Get a site setting by key."""
    setting = db.query(SiteSetting).filter(SiteSetting.key == key).first()
    return setting.value if setting else default


def set_setting(db: Session, key: str, value: str):
    """Set or update a site setting."""
    setting = db.query(SiteSetting).filter(SiteSetting.key == key).first()
    if setting:
        setting.value = value
        setting.updated_at = datetime.datetime.utcnow()
    else:
        setting = SiteSetting(key=key, value=value)
        db.add(setting)
    db.commit()


def get_build_stats() -> dict:
    """Get stats from the latest build."""
    index_path = PROJECT_DIR / "index.html"
    sitemap_path = PROJECT_DIR / "sitemap.xml"
    now = datetime.datetime.now()
    
    stats = {
        "index_size": index_path.stat().st_size if index_path.exists() else 0,
        "sitemap_size": sitemap_path.stat().st_size if sitemap_path.exists() else 0,
        "last_build": "Never",
        "article_count": 0,
        "source_count": 0,
    }
    
    if index_path.exists():
        mtime = datetime.datetime.fromtimestamp(index_path.stat().st_mtime)
        stats["last_build"] = mtime.isoformat()
    
    # Count articles from index.html
    if index_path.exists():
        content = index_path.read_text()
        stats["article_count"] = content.count('<article')
    
    # Count sources from build.py
    build_py = PROJECT_DIR / "build.py"
    if build_py.exists():
        content = build_py.read_text()
        import re
        sources = re.findall(r'rss_urls\[\s*"([^"]+)"\s*\]', content)
        stats["source_count"] = len(sources)
    
    return stats


# ─── STARTUP ───────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    """Initialize database and default admin user."""
    init_db()
    db = next(get_db())
    try:
        init_admin_user(db, "admin", "admin123")
    finally:
        db.close()
    print("🚀 Rupeewa Admin Backend started!")


# ─── AUTH ENDPOINTS ────────────────────────────────────────────────

@app.post("/api/auth/login")
async def api_login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Login endpoint returning JWT token."""
    user = db.query(AdminUser).filter(AdminUser.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    
    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer", "username": user.username}


@app.get("/api/auth/me")
async def api_me(current_user = Depends(get_current_user)):
    """Get current user info."""
    return {"username": current_user.username, "is_active": current_user.is_active}


# ─── DASHBOARD API ────────────────────────────────────────────────

@app.get("/api/dashboard")
async def api_dashboard(
    db: Session = Depends(get_db),
    _=Depends(get_current_user)
):
    """Get dashboard statistics."""
    stats = get_build_stats()
    
    # Database stats
    articles_count = db.query(ArticleOverride).count()
    sources_count = db.query(Source).count()
    subscribers = db.query(NewsletterSubscriber).filter(NewsletterSubscriber.is_active == True).count()
    recent_builds = db.query(BuildLog).order_by(BuildLog.started_at.desc()).limit(5).all()
    
    # Visit stats (last 7 days)
    week_ago = datetime.datetime.utcnow() - datetime.timedelta(days=7)
    visits_7d = db.query(PageVisit).filter(PageVisit.visited_at >= week_ago).count()
    
    return {
        "build": stats,
        "db_articles": articles_count,
        "db_sources": sources_count,
        "subscribers": subscribers,
        "visits_7d": visits_7d,
        "recent_builds": [
            {"status": b.status, "articles": b.articles_count,
             "started": b.started_at.isoformat() if b.started_at else None}
            for b in recent_builds
        ],
        "now": datetime.datetime.now().isoformat()
    }


# ─── ARTICLES API ─────────────────────────────────────────────────

@app.get("/api/articles")
async def api_articles(
    page: int = 1,
    limit: int = 50,
    db: Session = Depends(get_db),
    _=Depends(get_current_user)
):
    """Get articles from the latest build with override info."""
    index_path = PROJECT_DIR / "index.html"
    articles = []
    
    if index_path.exists():
        content = index_path.read_text()
        # Parse article cards from the HTML
        import re
        card_pattern = re.compile(
            r'<article[^>]*>.*?<a href="([^"]+)".*?<h[23][^>]*>(.*?)</h[23]>.*?<p[^>]*class="card-desc">(.*?)</p>.*?</article>',
            re.DOTALL
        )
        for match in card_pattern.finditer(content):
            url = match.group(1).strip()
            title = re.sub(r'<[^>]+>', '', match.group(2)).strip()
            desc = re.sub(r'<[^>]+>', '', match.group(3)).strip()
            
            # Check for overrides
            override = db.query(ArticleOverride).filter(ArticleOverride.article_url == url).first()
            
            articles.append({
                "url": url,
                "title": title,
                "description": desc[:200],
                "is_featured": override.is_featured if override else False,
                "is_hidden": override.is_hidden if override else False,
            })
    
    return {"articles": articles[(page-1)*limit:page*limit], "total": len(articles), "page": page}


@app.post("/api/articles/override")
async def api_article_override(
    url: str = Form(...),
    is_featured: bool = Form(False),
    is_hidden: bool = Form(False),
    custom_description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user)
):
    """Set article override (feature, hide, custom content)."""
    override = db.query(ArticleOverride).filter(ArticleOverride.article_url == url).first()
    if not override:
        override = ArticleOverride(article_url=url)
        db.add(override)
    
    override.is_featured = is_featured
    override.is_hidden = is_hidden
    override.custom_description = custom_description
    override.updated_at = datetime.datetime.utcnow()
    db.commit()
    
    return {"status": "ok", "url": url, "is_featured": is_featured, "is_hidden": is_hidden}


# ─── SOURCES API ───────────────────────────────────────────────────

@app.get("/api/sources")
async def api_sources(
    db: Session = Depends(get_db),
    _=Depends(get_current_user)
):
    """Get all RSS sources."""
    sources = db.query(Source).all()
    # Also get sources from build.py
    build_py = PROJECT_DIR / "build.py"
    build_sources = {}
    if build_py.exists():
        import re
        content = build_py.read_text()
        for match in re.finditer(r'rss_urls\[\s*"([^"]+)"\s*\]\s*=\s*"([^"]+)"', content):
            build_sources[match.group(1)] = match.group(2)
    
    result = []
    for src in sources:
        result.append({
            "id": src.id,
            "name": src.name,
            "rss_url": src.rss_url,
            "is_active": src.is_active,
            "article_limit": src.article_limit,
        })
    
    return {"db_sources": result, "build_sources": build_sources, "count": len(result)}


@app.post("/api/sources/add")
async def api_add_source(
    name: str = Form(...),
    rss_url: str = Form(...),
    article_limit: int = Form(30),
    db: Session = Depends(get_db),
    _=Depends(get_current_user)
):
    """Add a new RSS source."""
    existing = db.query(Source).filter(Source.rss_url == rss_url).first()
    if existing:
        raise HTTPException(status_code=400, detail="Source already exists")
    
    source = Source(name=name, rss_url=rss_url, article_limit=article_limit)
    db.add(source)
    db.commit()
    
    return {"status": "ok", "id": source.id, "name": name}


@app.delete("/api/sources/{source_id}")
async def api_delete_source(
    source_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user)
):
    """Delete a source."""
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    db.delete(source)
    db.commit()
    return {"status": "ok", "deleted": source_id}


# ─── SEO SETTINGS API ──────────────────────────────────────────────

@app.get("/api/seo")
async def api_seo(
    db: Session = Depends(get_db),
    _=Depends(get_current_user)
):
    """Get current SEO settings."""
    settings = {}
    for key in ["site_name", "site_description", "site_keywords",
                "og_title", "og_description", "twitter_handle",
                "google_analytics_id", "custom_head_html"]:
        settings[key] = get_setting(db, key)
    return settings


@app.post("/api/seo")
async def api_seo_update(
    request: Request,
    db: Session = Depends(get_db),
    _=Depends(get_current_user)
):
    """Update SEO settings."""
    data = await request.json()
    for key, value in data.items():
        set_setting(db, key, str(value))
    return {"status": "ok"}


# ─── BUILD API ─────────────────────────────────────────────────────

@app.post("/api/build/trigger")
async def api_trigger_build(
    db: Session = Depends(get_db),
    _=Depends(get_current_user)
):
    """Trigger a site rebuild."""
    log = BuildLog(status="running", started_at=datetime.datetime.utcnow())
    db.add(log)
    db.commit()
    
    try:
        result = subprocess.run(
            [sys.executable, str(BUILD_SCRIPT)],
            capture_output=True, text=True, timeout=120,
            cwd=str(PROJECT_DIR)
        )
        
        log.status = "success" if result.returncode == 0 else "failed"
        log.error_message = result.stderr[:1000] if result.stderr else None
        
        # Count articles in output
        index_path = PROJECT_DIR / "index.html"
        if index_path.exists():
            content = index_path.read_text()
            log.articles_count = content.count('<article')
            log.output_size = index_path.stat().st_size
            log.sources_count = content.count('source-filter')
        
        log.finished_at = datetime.datetime.utcnow()
        db.commit()
        
        return {
            "status": log.status,
            "articles": log.articles_count,
            "output": result.stdout[-500:],
            "error": result.stderr[-500:] if result.stderr else None
        }
    except Exception as e:
        log.status = "failed"
        log.error_message = str(e)
        log.finished_at = datetime.datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/build/logs")
async def api_build_logs(
    db: Session = Depends(get_db),
    _=Depends(get_current_user)
):
    """Get recent build logs."""
    logs = db.query(BuildLog).order_by(BuildLog.started_at.desc()).limit(20).all()
    return {
        "logs": [
            {
                "id": l.id, "status": l.status,
                "articles": l.articles_count,
                "started": l.started_at.isoformat() if l.started_at else None,
                "finished": l.finished_at.isoformat() if l.finished_at else None,
                "error": l.error_message[:200] if l.error_message else None
            }
            for l in logs
        ]
    }


# ─── SUBSCRIBERS API ───────────────────────────────────────────────

@app.get("/api/subscribers")
async def api_subscribers(
    db: Session = Depends(get_db),
    _=Depends(get_current_user)
):
    """Get newsletter subscribers."""
    subs = db.query(NewsletterSubscriber).order_by(NewsletterSubscriber.subscribed_at.desc()).all()
    return {
        "subscribers": [
            {"email": s.email, "subscribed_at": s.subscribed_at.isoformat(), "is_active": s.is_active}
            for s in subs
        ],
        "total": len(subs)
    }


# ─── TRACKING ENDPOINT ─────────────────────────────────────────────

@app.get("/api/track")
async def api_track(
    page: str = Query("/"),
    referrer: str = Query(""),
    db: Session = Depends(get_db)
):
    """Simple analytics tracking (no auth needed)."""
    visit = PageVisit(
        path=page[:500],
        referrer=referrer[:500] if referrer else None,
        visited_at=datetime.datetime.utcnow()
    )
    db.add(visit)
    db.commit()
    return {"status": "ok"}


# ─── ADMIN PAGES ───────────────────────────────────────────────────

@app.get("/admin", response_class=HTMLResponse)
@app.get("/admin/", response_class=HTMLResponse)
async def admin_dashboard():
    """Serve admin panel."""
    return FileResponse(str(templates_dir / "admin.html"))

@app.get("/admin/{page_name}", response_class=HTMLResponse)
async def admin_page(page_name: str):
    """Serve admin panel sub-pages."""
    return FileResponse(str(templates_dir / "admin.html"))


# ─── HEALTH CHECK ──────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "Rupeewa Admin", "time": datetime.datetime.now().isoformat()}

#!/usr/bin/env python3
"""
Rocket News Daily — Professional Build Script
Fetches tech news from RSS feeds and generates a polished index.html
"""

import json, os, re, time, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from html import escape

# RSS Feed Sources
FEEDS = {
    "Hacker News": {
        "url": "https://hnrss.org/frontpage?count=15",
        "color": "#ff6600",
        "icon": "Y"
    },
    "TechCrunch": {
        "url": "https://techcrunch.com/feed/",
        "color": "#0aff01",
        "icon": "T"
    },
    "The Verge": {
        "url": "https://www.theverge.com/rss/index.xml",
        "color": "#1a8aff",
        "icon": "V"
    },
    "DEV Community": {
        "url": "https://dev.to/feed",
        "color": "#7c3aed",
        "icon": "D"
    },
    "Ars Technica": {
        "url": "https://feeds.arstechnica.com/arstechnica/index",
        "color": "#ff4d00",
        "icon": "A"
    },
    "Wired": {
        "url": "https://www.wired.com/feed/rss",
        "color": "#aabbcc",
        "icon": "W"
    }
}

SITE_URL = "https://rupeewa.vercel.app"
SITE_NAME = "Rupeewa News Daily"
SITE_DESC = "Stay ahead with the latest tech news, AI breakthroughs, startup stories, and gadget reviews. Curated daily from Hacker News, TechCrunch, The Verge, and more."
HERO_IMG = "https://rupeewa.vercel.app/logo.jpg"

def fetch_rss(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RocketNews/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception as e:
        print(f"  ⚠️  {e}")
        return None

def parse_rss(xml_data, source_name):
    items = []
    try:
        root = ET.fromstring(xml_data)
        ns = {'atom': 'http://www.w3.org/2005/Atom', 'dc': 'http://purl.org/dc/elements/1.1/', 
              'content': 'http://purl.org/rss/1.0/modules/content/', 'media': 'http://search.yahoo.com/mrss/'}

        for item in root.iter('item'):
            title = item.findtext('title', '')
            link = item.findtext('link', '')
            desc = item.findtext('description', '')
            pub_date = item.findtext('pubDate', '')
            creator = item.findtext('{http://purl.org/dc/elements/1.1/}creator', '')
            # Try to get image
            img = ''
            media_el = item.find('{http://search.yahoo.com/mrss/}content')
            if media_el is not None:
                img = media_el.get('url', '')
            if not img:
                media_el = item.find('{http://search.yahoo.com/mrss/}thumbnail')
                if media_el is not None:
                    img = media_el.get('url', '')
            enclosure = item.find('enclosure')
            if not img and enclosure is not None:
                url_attr = enclosure.get('url', '')
                if url_attr and any(x in url_attr for x in ['.jpg', '.png', '.webp']):
                    img = url_attr

            desc = re.sub(r'<[^>]+>', '', desc)
            desc = desc.strip()[:300]
            # Clean up HN-style descriptions with URLs
            desc = re.sub(r'Article URL: https?://[^\s]+', '', desc)
            desc = re.sub(r'Comments URL: https?://[^\s]+', '', desc)
            desc = re.sub(r'Points: \d+', '', desc)
            desc = re.sub(r'# Comments: \d+', '', desc)
            desc = re.sub(r'\s+', ' ', desc).strip()
            if len(desc) > 200:
                desc = desc[:desc.rfind(' ')] + '\u2026'

            items.append({
                'title': title, 'link': link, 'description': desc,
                'source': source_name, 'published': pub_date,
                'creator': creator, 'image': img
            })

        for entry in root.iter('{http://www.w3.org/2005/Atom}entry'):
            title = entry.findtext('{http://www.w3.org/2005/Atom}title', '')
            link_el = entry.find('{http://www.w3.org/2005/Atom}link')
            link = link_el.get('href', '') if link_el is not None else ''
            desc_el = entry.find('{http://www.w3.org/2005/Atom}content') or entry.find('{http://www.w3.org/2005/Atom}summary')
            desc = desc_el.text if desc_el is not None else ''
            desc = re.sub(r'<[^>]+>', '', desc).strip()[:300]
            # Clean up HN-style descriptions with URLs
            desc = re.sub(r'Article URL: https?://[^\s]+', '', desc)
            desc = re.sub(r'Comments URL: https?://[^\s]+', '', desc)
            desc = re.sub(r'Points: \d+', '', desc)
            desc = re.sub(r'# Comments: \d+', '', desc)
            desc = re.sub(r'\s+', ' ', desc).strip()
            if len(desc) > 200:
                desc = desc[:desc.rfind(' ')] + '\u2026'
            pub_date = entry.findtext('{http://www.w3.org/2005/Atom}published', '') or entry.findtext('{http://www.w3.org/2005/Atom}updated', '')
            author_el = entry.find('{http://www.w3.org/2005/Atom}author')
            creator = author_el.findtext('{http://www.w3.org/2005/Atom}name', '') if author_el is not None else ''
            # Try image from Atom
            img = ''
            media_el = entry.find('{http://search.yahoo.com/mrss/}content')
            if media_el is not None:
                img = media_el.get('url', '')
            items.append({
                'title': title, 'link': link, 'description': desc,
                'source': source_name, 'published': pub_date,
                'creator': creator, 'image': img
            })
    except Exception as e:
        print(f"  ⚠️  Parse error: {e}")
    return items

def format_time(pub_date_str):
    if not pub_date_str:
        return ''
    formats = ['%a, %d %b %Y %H:%M:%S %z', '%a, %d %b %Y %H:%M:%S %Z',
               '%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%dT%H:%M:%S.%f%z',
               '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S']
    pub_date = None
    for fmt in formats:
        try:
            pub_date = datetime.strptime(pub_date_str.strip(), fmt)
            break
        except:
            continue
    if pub_date is None:
        return pub_date_str[:10] if pub_date_str else ''
    now = datetime.now(pub_date.tzinfo) if pub_date.tzinfo else datetime.now()
    diff = now - pub_date
    hours = diff.total_seconds() / 3600
    if hours < 1:
        mins = int(diff.total_seconds() / 60)
        return f'{mins}m ago' if mins > 0 else 'just now'
    elif hours < 24:
        return f'{int(hours)}h ago'
    elif hours < 48:
        return 'yesterday'
    else:
        return f'{int(hours / 24)}d ago'

def generate_jsonld(all_news):
    """Generate all JSON-LD structured data blocks."""
    social_links = ["https://github.com/Rocketnew/rocket-tech"]

    org_schema = json.dumps({
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": SITE_NAME,
        "url": SITE_URL,
        "logo": SITE_URL + "/logo.jpg",
        "sameAs": social_links
    }, ensure_ascii=False)

    website_schema = json.dumps({
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": SITE_NAME,
        "url": SITE_URL,
        "description": SITE_DESC,
        "potentialAction": {
            "@type": "SearchAction",
            "target": {
                "@type": "EntryPoint",
                "urlTemplate": SITE_URL + "/?q={search_term_string}"
            },
            "query-input": "required name=search_term_string"
        }
    }, ensure_ascii=False)

    # NewsArticle schema for first 9 articles
    article_blocks = []
    for item in all_news[:9]:
        schema = {
            "@context": "https://schema.org",
            "@type": "NewsArticle",
            "headline": item["title"],
            "description": item["description"][:200],
            "image": item.get("image") or HERO_IMG,
            "datePublished": item.get("published") or datetime.now().isoformat(),
            "author": {
                "@type": "Person",
                "name": item.get("creator") or item["source"]
            },
            "publisher": {
                "@type": "Organization",
                "name": SITE_NAME,
                "logo": SITE_URL + "/logo.jpg"
            },
            "url": item["link"],
            "mainEntityOfPage": {
                "@type": "WebPage",
                "@id": item["link"]
            }
        }
        article_blocks.append(json.dumps(schema, ensure_ascii=False))

    # Speakable schema for Google AI Overview
    speakable_schema = json.dumps({
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": SITE_NAME,
        "url": SITE_URL,
        "speakable": {
            "@type": "SpeakableSpecification",
            "cssSelector": [".hero-header h1", ".hero-header p", ".featured-card h2"]
        }
    }, ensure_ascii=False)

    # FAQPage schema for site categories
    faq_blocks = []
    for src in sorted(set(item["source"] for item in all_news)):
        faq_blocks.append({
            "@type": "Question",
            "name": f"Latest {src} news today",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": f"Find the latest {src} articles, news, and updates on Rupeewa News Daily. Curated daily with the most important stories."
            }
        })
    faq_schema = json.dumps({
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": faq_blocks[:5]
    }, ensure_ascii=False)

    return org_schema, website_schema, article_blocks, speakable_schema, faq_schema

def generate_html(all_news):
    now = datetime.now().strftime('%b %d, %Y · %I:%M %p')
    iso_now = datetime.now().isoformat() + '+00:00'
    today_str = datetime.now().strftime('%Y-%m-%d')
    sources = sorted(set(item['source'] for item in all_news))
    load_more_html = '<div class="load-more-wrapper"><button id="loadMore" class="load-more-btn">Show More Stories</button></div>' if len(all_news) > 48 else ''

    # Generate JSON-LD
    json_org, json_website, json_articles, json_speakable, json_faq = generate_jsonld(all_news)
    json_articles_html = '\n'.join(
        f'  <script type="application/ld+json">{a}</script>' for a in json_articles
    ) + '\n  <script type="application/ld+json">' + json_speakable + '</script>'
    json_articles_html += '\n  <script type="application/ld+json">' + json_faq + '</script>'

    # Hero: top 3 articles with images (or without)
    hero_cards_html = ''
    featured = all_news[:3]
    areas = ['main', 'side1', 'side2']
    for i, item in enumerate(featured):
        src_info = FEEDS.get(item['source'], {})
        color = src_info.get('color', '#666')
        icon = src_info.get('icon', 'N')
        title = escape(item['title'])
        desc = escape(item['description'])
        link = escape(item['link'])
        time_ago = format_time(item['published'])
        creator = escape(item['creator']) if item.get('creator') else ''
        img = item.get('image', '')

        img_style = f' style="background-image:url(\'{escape(img)}\')"' if img else ''

        hero_cards_html += f'''
    <a href="{link}" target="_blank" rel="noopener" class="featured-card" data-area="{areas[i]}">
      <div class="featured-bg"{img_style}></div>
      <div class="featured-gradient"></div>
      <div class="featured-content">
        <span class="featured-source"><span class="source-dot" style="background:{color};--dot-color:{color}"></span>{escape(item['source'])}</span>
        <h2>{title}</h2>
        {f'<p>{desc}</p>' if desc else ''}
        <div class="featured-meta">
          {f'<span class="featured-author">{creator}</span>' if creator else ''}
          <span class="featured-time">{time_ago}</span>
        </div>
      </div>
    </a>'''

    # Build cards (limit to 48 for performance)
    display_news = all_news[:48]
    cards_html = ''
    ad_slots = ['monetag-slot-1', 'monetag-slot-2', 'monetag-slot-3', 'monetag-slot-4', 'monetag-slot-5']
    for idx, item in enumerate(display_news):
        src_info = FEEDS.get(item['source'], {})
        color = src_info.get('color', '#666')
        icon = src_info.get('icon', 'N')
        title = escape(item['title'])
        desc = escape(item['description'])
        link = escape(item['link'])
        time_ago = format_time(item['published'])
        source = escape(item['source'])
        creator = escape(item['creator']) if item.get('creator') else ''
        img = item.get('image', '')
        src_class = source.lower().replace(' ', '').replace('.', '')
        card_img_style = f' style="background-image:url(\'{escape(img)}\')"' if img else ''
        fallback_hidden = ' style="display:none"' if img else ''

        cards_html += f'\n    <article class="news-card source-accent-{src_class}" data-source="{src_class}" itemscope itemtype="https://schema.org/NewsArticle">\n' + \
    f'      <meta itemprop="datePublished" content="{escape(item.get("published", ""))}">\n' + \
    f'      <div class="card-img-wrapper">\n' + \
    f'        <div class="card-img"{card_img_style}></div>\n' + \
    f'        <div class="card-fallback"{fallback_hidden}>\n' + \
    f'          <div class="source-gradient source-gradient-{src_class}"></div>\n' + \
    f'          <div class="source-pattern"></div>\n' + \
    f'          <span class="source-icon" style="background:{color};color:#000">{icon}</span>\n' + \
    f'        </div>\n' + \
    f'        <span class="card-source-tag" style="background:{color};color:#000">{source}</span>\n' + \
    f'      </div>\n' + \
    f'      <div class="card-body">\n' + \
    f'        <h3 itemprop="headline"><a href="{link}" target="_blank" rel="noopener" itemprop="url">{title}</a></h3>\n' + \
    (f'        <p itemprop="description">{desc}</p>\n' if desc else '') + \
    f'        <div class="card-meta">\n' + \
    f'          <span class="card-time"><time datetime="{escape(item.get("published", ""))}">{time_ago}</time></span>\n' + \
    (f'          <span class="card-author" itemprop="author">{creator}</span>\n' if creator else '') + \
    f'          <span class="card-arrow">\u2192</span>\n' + \
    f'        </div>\n' + \
    f'      </div>\n' + \
    f'    </article>'
        # Insert ad containers after card 8, 16, 24
        if (idx + 1) % 8 == 0 and (idx + 1) // 8 <= len(ad_slots):
            slot_id = ad_slots[(idx + 1) // 8 - 1]
            cards_html += f'\n    <div class="ad-slot" data-ad-slot="{slot_id}">\n' + \
    f'      <div class="ad-label">\u2014 Sponsored \u2014</div>\n' + \
    f'      <div id="{slot_id}" class="ad-container"></div>\n' + \
    f'    </div>'

    # Source filter buttons
    source_buttons = ''
    for s in sources:
        s_class = s.lower().replace(' ', '').replace('.', '')
        src_info = FEEDS.get(s, {})
        color = src_info.get('color', '#666')
        source_buttons += f'''
        <button class="cat-btn" data-filter="{s_class}" style="--btn-color:{color}">{escape(s)}</button>'''

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="google-site-verification" content="4lKhG4kpuIxY8trSyF3P4g685OgZlY1l09pk29As63k">
  <title>{SITE_NAME} — Today's Top Tech News</title>
  <meta name="description" content="{SITE_DESC}">
  <meta name="robots" content="index, follow">
  <meta name="keywords" content="tech news, AI, startups, gadgets, Hacker News, TechCrunch, The Verge, technology, daily news, programming">
  <meta name="author" content="{SITE_NAME}">
  <meta property="article:published_time" content="{iso_now}">
  <meta property="article:modified_time" content="{iso_now}">
  <meta name="date" content="{today_str}">
  <link rel="canonical" href="{SITE_URL}/">

  <!-- Open Graph / Social Meta -->
  <meta property="og:title" content="{SITE_NAME} \u2014 Today's Top Tech News">
  <meta property="og:description" content="{SITE_DESC}">
  <meta property="og:image" content="{HERO_IMG}">
  <meta property="og:url" content="{SITE_URL}/">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="{SITE_NAME}">
  <meta property="og:locale" content="en_US">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{SITE_NAME} \u2014 Today's Top Tech News">
  <meta name="twitter:description" content="{SITE_DESC}">
  <meta name="twitter:image" content="{HERO_IMG}">

  <!-- JSON-LD Structured Data -->
  <script type="application/ld+json">{json_org}</script>
  <script type="application/ld+json">{json_website}</script>
{json_articles_html}

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="style.css">
  <link rel="manifest" href="/manifest.json">
  <meta name="theme-color" content="#6c63ff">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-title" content="Rupeewa">
  <meta name="mobile-web-app-capable" content="yes">
  <!-- Search bar styles -->
  <style>
      .search-wrapper {{ margin: 1rem 0 0; position: relative; max-width: 480px; }}
      .search-input {{
          width: 100%; padding: 0.7rem 1rem 0.7rem 2.5rem; border-radius: 12px;
          border: 1px solid #2a2a3a; background: #12121a; color: #e1e1e8;
          font-size: 0.9rem; outline: none; transition: all 0.2s;
          box-sizing: border-box;
      }}
      .search-input:focus {{ border-color: #6c63ff; box-shadow: 0 0 0 3px rgba(108,99,255,0.1); }}
      .search-input::placeholder {{ color: #555; }}
      .search-results {{
          position: absolute; top: 100%; left: 0; right: 0; z-index: 100;
          background: #1a1a24; border: 1px solid #2a2a3a; border-radius: 12px;
          margin-top: 4px; max-height: 360px; overflow-y: auto;
          box-shadow: 0 8px 30px rgba(0,0,0,0.4);
      }}
      .search-results a {{
          display: block; padding: 0.7rem 1rem; color: #e1e1e8; text-decoration: none;
          border-bottom: 1px solid #1e1e2e; font-size: 0.85rem;
          transition: background 0.1s;
      }}
      .search-results a:last-child {{ border-bottom: none; }}
      .search-results a:hover {{ background: rgba(108,99,255,0.05); }}
      .search-results .sr-source {{ font-size: 0.7rem; color: #6c63ff; text-transform: uppercase; letter-spacing: 0.3px; }}
      .search-results .sr-title {{ display: block; margin-top: 2px; }}
      .search-results .sr-none {{ padding: 1rem; color: #666; text-align: center; font-size: 0.85rem; }}
      .search-results .sr-count {{ padding: 0.5rem 1rem; font-size: 0.75rem; color: #555; }}
      /* ─── Mobile Nav —── */
      .nav-hamburger {{ display: none; flex-direction: column; gap: 4px; background: none; border: none; cursor: pointer; padding: 8px; }}
      .nav-hamburger span {{ display: block; width: 20px; height: 2px; background: #aaa; border-radius: 2px; transition: 0.3s; }}
      .nav-right.mobile-open {{ display: flex !important; flex-direction: column; position: absolute; top: 100%; left: 0; right: 0; background: #0a0a0f; padding: 1rem; border-bottom: 1px solid #1a1a2e; z-index: 100; }}
      /* ─── Theme Toggle —── */
      .theme-toggle {{ background: none; border: 1px solid #333; border-radius: 50%; width: 32px; height: 32px; cursor: pointer; font-size: 1rem; display: flex; align-items: center; justify-content: center; transition: 0.3s; }}
      .theme-toggle:hover {{ border-color: #6c63ff; background: #1a1a2e; }}
      @media (max-width: 768px) {{
        .nav-hamburger {{ display: flex; }}
        .nav-right {{ display: none; }}
        .nav-right.mobile-open {{ display: flex !important; }}
        .nav-update {{ display: none; }}
      }}
      /* ─── Light Theme —── */
      [data-theme="light"] {{
        --bg: #f5f5f8; --bg-card: #ffffff; --text: #1a1a2e;
        --text-secondary: #555; --border: #e0e0e8;
      }}
      [data-theme="light"] body {{ background: var(--bg, #f5f5f8); color: var(--text, #1a1a2e); }}
      [data-theme="light"] .nav-right.mobile-open {{ background: #fff; border-color: #e0e0e8; }}
      [data-theme="light"] .theme-toggle {{ border-color: #ccc; }}
      [data-theme="light"] .theme-toggle:hover {{ border-color: #6c63ff; background: #eee; }}
  </style>
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><defs><linearGradient id='g' x1='0%25' y1='0%25' x2='100%25' y2='100%25'><stop offset='0%25' stop-color='%237c3aed'/><stop offset='100%25' stop-color='%236366f1'/></linearGradient></defs><rect width='100' height='100' rx='20' fill='%230a0a0f'/><text x='50' y='72' font-size='60' text-anchor='middle'>🚀</text></svg>">
  <!-- Monetag -->
  <meta name="monetag" content="f777923a656a6851a964b8cb54790337">
  <link rel="dns-prefetch" href="https://cdn.monetag.com">
  <link rel="preconnect" href="https://cdn.monetag.com" crossorigin>
  <script src="https://quge5.com/88/tag.min.js" data-zone="247762" async data-cfasync="false"></script>
</head>
<body>

<!-- Reading Progress Bar -->
<div id="progress-bar" role="progressbar" aria-label="Reading progress"></div>

<!-- Site Notification Banner -->
<div id="site-notification" class="site-notification" style="display:none"></div>

<header>
  <nav class="nav-inner" aria-label="Main navigation">
    <div class="nav-left">
      <a href="/" class="nav-logo" aria-label="{SITE_NAME} Home">
        <img src="logo.jpg" alt="{SITE_NAME}" class="nav-logo-svg" style="height:50px;width:auto;object-fit:contain">
        <span class="nav-logo-text">Rupeewa</span>
        <span class="nav-logo-badge">News Daily</span>
      </a>
    </div>
    <button class="nav-hamburger" onclick="toggleNav()" aria-label="Toggle navigation" aria-expanded="false">
      <span></span><span></span><span></span>
    </button>
    <div class="nav-right">
      <span class="nav-stats">{len(display_news)} stories</span>
      <span class="nav-update">Updated {now}</span>
      <button class="theme-toggle" onclick="toggleTheme()" aria-label="Toggle theme">🌙</button>
    </div>
  </nav>
</header>

<main>
  <section class="hero-section" aria-label="Featured stories">
    <div class="hero-header">
      <h1>Today's <span class="gradient-text">Tech</span></h1>
      <p>The latest news from across the tech world &mdash; curated daily.</p>
      <!-- Search Bar -->
      <div class="search-wrapper">
        <input type="text" id="searchInput" class="search-input" placeholder="🔍 Search articles..." autocomplete="off" />
        <div id="searchResults" class="search-results" style="display:none"></div>
      </div>
    </div>
    <a href="https://rupeewa.com/?invite=MNTAYR" target="_blank" rel="noopener" class="refer-card-link">
    <article class="news-card refer-card" data-source="rupeewa" aria-label="Rupeewa App - Refer & Earn">
      <div class="card-img-wrapper">
        <div class="card-img" style="background-image:url('refer-earn.jpg');background-size:cover;background-position:center"></div>
        <div class="card-fallback" style="display:none"></div>
        <span class="card-source-tag" style="background:linear-gradient(135deg,#7c3aed,#6366f1);color:#fff">&rarr; Refer &amp; Earn</span>
      </div>
      <div class="card-body">
        <h3>&#x1f525; Rupeewa App &mdash; Refer &amp; Earn!</h3>
        <p>&#x1f4f1; WhatsApp tasks karo aur &#x20b9;100+ withdraw karo! Same as Athena App. Limited time offer &mdash; join now and start earning!</p>
        <div class="card-meta">
          <span class="card-time">&#x1f525; Limited Offer</span>
          <span class="card-author">Rupeewa Teams</span>
          <span class="card-arrow">&rarr;</span>
        </div>
      </div>
    </article>
    </a>
    <div class="hero-header-divider"><span>Featured Stories</span></div>
    <div class="featured-grid">
      {hero_cards_html}
    </div>
  </section>

  <section class="filter-section" aria-label="Filter by source">
    <div class="filter-inner" role="tablist" aria-label="News sources">
      <button class="cat-btn active" data-filter="all" role="tab" aria-selected="true">All</button>
      {source_buttons}
    </div>
  </section>

  <section class="news-section" aria-label="All news stories">
    <div class="news-grid" id="newsGrid">
      {cards_html}
    </div>
    {load_more_html}
  </section>
</main>

<footer>
  <div class="footer-inner">
    <div class="footer-brand" aria-label="{SITE_NAME}">🚀 {SITE_NAME}</div>
    <div class="footer-links">
      <a href="https://github.com/Rocketnew/rocket-tech" target="_blank" rel="noopener">GitHub</a>
      <span aria-hidden="true">\u00b7</span>
      <span>Daily at 7 AM</span>
      <span aria-hidden="true">\u00b7</span>
      <span>{len(FEEDS)} sources</span>
    </div>
    <div class="newsletter-form">
      <label for="nl-email">📬 Daily tech news in your inbox</label>
      <div style="display:flex;gap:0.5rem;margin-top:0.5rem;">
        <input type="email" id="nl-email" placeholder="your@email.com" 
               style="flex:1;padding:0.6rem 0.9rem;border-radius:8px;border:1px solid #2a2a3a;
                      background:#12121a;color:#e1e1e8;font-size:0.9rem;">
        <button onclick="subscribeNewsletter()" 
                style="padding:0.6rem 1.2rem;border-radius:8px;border:none;
                       background:linear-gradient(135deg,#6c63ff,#8b5cf6);color:#fff;font-weight:600;cursor:pointer;">
          Subscribe
        </button>
      </div>
      <div id="nl-msg" style="font-size:0.8rem;margin-top:0.4rem;color:#6ee7b7;"></div>
    </div>
    <div class="footer-meta">Data from {', '.join(FEEDS.keys())}</div>
  </div>
</footer>

<script>
// Category filter
document.querySelectorAll('.cat-btn').forEach(btn => {{
  btn.addEventListener('click', () => {{
    document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const filter = btn.dataset.filter;
    document.querySelectorAll('.news-card').forEach(card => {{
      if (filter === 'all') {{
        card.style.display = '';
        card.style.opacity = '1';
      }} else {{
        const match = card.dataset.source === filter;
        card.style.display = match ? '' : 'none';
        if (match) card.style.opacity = '1';
      }}
    }});
  }});
}});

// Scroll animation
const observer = new IntersectionObserver((entries) => {{
  entries.forEach(entry => {{
    if (entry.isIntersecting) {{
      entry.target.classList.add('visible');
      observer.unobserve(entry.target);
    }}
  }});
}}, {{ threshold: 0.05 }});

document.querySelectorAll('.news-card, .featured-card').forEach(el => {{
  el.classList.add('animate-in');
  observer.observe(el);
}});

// Load more (show all hidden cards)
const loadMore = document.getElementById('loadMore');
if (loadMore) {{
  let hiddenCards = [];
  document.querySelectorAll('.news-card').forEach((card, i) => {{
    if (i >= {min(48, len(display_news))}) card.style.display = 'none';
  }});
  loadMore.addEventListener('click', () => {{
    document.querySelectorAll('.news-card').forEach(card => {{
      card.style.display = '';
      card.classList.add('visible');
    }});
    loadMore.textContent = 'All stories loaded';
    loadMore.disabled = true;
    loadMore.style.opacity = '0.5';
  }});
}}

// Reading progress bar
window.addEventListener('scroll', () => {{
  const bar = document.getElementById('progress-bar');
  if (!bar) return;
  const h = document.documentElement.scrollHeight - window.innerHeight;
  bar.style.width = h > 0 ? Math.min((window.scrollY / h) * 100, 100) + '%' : '0%';
}});

// Monetag ad slots
const Monetag = {{
  init() {{
    if (!document.getElementById('mt-main')) {{
      const s = document.createElement('script');
      s.id = 'mt-main'; s.src = '//cdn.monetag.com/v/2025.js'; s.async = true;
      s.setAttribute('data-zone', 'f777923a656a6851a964b8cb54790337');
      document.head.appendChild(s);
    }}
    if (!document.getElementById('mt-push')) {{
      const s = document.createElement('script');
      s.id = 'mt-push'; s.src = '//cdn.monetag.com/p/2025.js'; s.async = true;
      s.setAttribute('data-zone', 'f777923a656a6851a964b8cb54790337');
      document.head.appendChild(s);
    }}
  }},
  initSlots() {{
    document.querySelectorAll('[data-ad-slot]').forEach(el => {{
      const c = el.querySelector('.ad-container');
      if (c && !c.children.length) c.innerHTML = '<!-- ad slot -->';
    }});
  }}
}};
Monetag.init();
Monetag.initSlots();

// Newsletter subscription
async function subscribeNewsletter() {{
  const email = document.getElementById('nl-email').value.trim();
  const msgEl = document.getElementById('nl-msg');
  if (!email || !email.includes('@')) {{
    msgEl.textContent = 'Please enter a valid email';
    msgEl.style.color = '#fca5a5';
    return;
  }}
  msgEl.textContent = 'Subscribing...';
  msgEl.style.color = '#888';
  try {{
    let subs = JSON.parse(localStorage.getItem('nl_subs') || '[]');
    if (!subs.includes(email)) {{
      subs.push(email);
      localStorage.setItem('nl_subs', JSON.stringify(subs));
    }}
    msgEl.textContent = '✅ Subscribed! Welcome!';
    msgEl.style.color = '#6ee7b7';
    document.getElementById('nl-email').value = '';
  }} catch(e) {{
    msgEl.textContent = '✅ Subscribed!';
    msgEl.style.color = '#6ee7b7';
  }}
}}

// Analytics tracking
(function() {{
  const track = () => {{
    const data = {{page: location.pathname, referrer: document.referrer || ''}};
    fetch('/api/track?' + new URLSearchParams(data), {{method: 'GET'}}).catch(() => {{}});
  }};
  track();
  document.addEventListener('visibilitychange', () => {{
    if (!document.hidden) track();
  }});
}})();

// Social share
function shareArticle(title, url) {{
  if (navigator.share) {{
    navigator.share({{title: title, url: url}}).catch(() => {{}});
  }} else {{
    const shareUrl = 'https://twitter.com/intent/tweet?text=' + encodeURIComponent(title) + '&url=' + encodeURIComponent(url);
    window.open(shareUrl, 'share', 'width=550,height=420');
  }}
}}

// Search articles
document.getElementById('searchInput')?.addEventListener('input', function() {{
  const q = this.value.trim().toLowerCase();
  const results = document.getElementById('searchResults');
  if (!q || q.length < 2) {{ results.style.display = 'none'; return; }}
  const articles = document.querySelectorAll('.news-card');
  let matches = [];
  articles.forEach(card => {{
    const title = card.querySelector('h3')?.textContent?.toLowerCase() || '';
    const desc = card.querySelector('p')?.textContent?.toLowerCase() || '';
    const source = card.querySelector('.card-source-tag')?.textContent?.toLowerCase() || '';
    if (title.includes(q) || desc.includes(q) || source.includes(q)) {{
      matches.push({{ title: card.querySelector('h3 a')?.textContent || 'Article',
                     link: card.querySelector('h3 a')?.href || '#',
                     source: card.querySelector('.card-source-tag')?.textContent || '' }});
    }}
  }});
  if (matches.length === 0) {{
    results.innerHTML = '<div class="sr-none">No articles found</div>';
  }} else {{
    results.innerHTML = '<div class="sr-count">' + matches.length + ' result' + (matches.length > 1 ? 's' : '') + '</div>' +
      matches.slice(0, 10).map(m =>
        '<a href="' + m.link + '" target="_blank" rel="noopener">' +
        '<span class="sr-source">' + m.source + '</span>' +
        '<span class="sr-title">' + m.title + '</span></a>'
      ).join('');
  }}
  results.style.display = 'block';
}});
document.addEventListener('click', function(e) {{
  const r = document.getElementById('searchResults');
  if (r && !e.target.closest('.search-wrapper')) r.style.display = 'none';
}});

// End search

// Mobile nav toggle
function toggleNav() {{
  const nav = document.querySelector('.nav-right');
  const btn = document.querySelector('.nav-hamburger');
  if (!nav || !btn) return;
  const isOpen = nav.classList.toggle('mobile-open');
  btn.setAttribute('aria-expanded', isOpen);
}}

// Light/Dark theme toggle
function toggleTheme() {{
  const html = document.documentElement;
  const btn = document.querySelector('.theme-toggle');
  const isDark = html.getAttribute('data-theme') !== 'light';
  html.setAttribute('data-theme', isDark ? 'light' : 'dark');
  localStorage.setItem('theme', isDark ? 'light' : 'dark');
  if (btn) btn.textContent = isDark ? '☀️' : '🌙';
}}

// Apply saved theme on load
(function() {{
  const saved = localStorage.getItem('theme');
  if (saved) {{
    document.documentElement.setAttribute('data-theme', saved);
    const btn = document.querySelector('.theme-toggle');
    if (btn) btn.textContent = saved === 'dark' ? '🌙' : '☀️';
  }}
}})();

const vapidPublicKey = 'BP3qGc-cn0TfGRDAkVrgfYAKqEEIvygeWxR77B1trmNN4Vy5oOj_pLDQLUpVY1Vi0-Bg9GhKFf-STnagdc1R3QM';

function urlBase64ToUint8Array(base64String) {{
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = atob(base64);
  return new Uint8Array([...rawData].map(char => char.charCodeAt(0)));
}}

async function initPushNotifications() {{
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {{
    console.log('Push notifications not supported');
    return;
  }}
  
  try {{
    // Register service worker
    const reg = await navigator.serviceWorker.register('/sw.js');
    await navigator.serviceWorker.ready;
    
    // Check existing subscription
    let sub = await reg.pushManager.getSubscription();
    if (sub) {{
      await sendSubscriptionToServer(sub);
      showPushStatus(true);
      return;
    }}
    
    // Show subscribe button after a delay
    setTimeout(showPushPrompt, 10000);
  }} catch (err) {{
    console.error('Push init failed:', err);
  }}
}}

function showPushPrompt() {{
  // Don't show if already subscribed or dismissed
  if (localStorage.getItem('push_dismissed')) return;
  if (document.querySelector('.push-prompt')) return;
  
  const prompt = document.createElement('div');
  prompt.className = 'push-prompt';
  prompt.innerHTML = `
    <div class="push-prompt-content">
      <span class="push-icon">🔔</span>
      <div class="push-text">
        <strong>Get notified</strong>
        <span>New tech news alerts</span>
      </div>
      <button class="push-btn" onclick="subscribePush()">Enable</button>
      <button class="push-dismiss" onclick="dismissPushPrompt()">&times;</button>
    </div>
  `;
  document.body.appendChild(prompt);
}}

function dismissPushPrompt() {{
  const prompt = document.querySelector('.push-prompt');
  if (prompt) prompt.remove();
  localStorage.setItem('push_dismissed', 'true');
}}

async function subscribePush() {{
  const btn = document.querySelector('.push-btn');
  if (btn) btn.disabled = true;
  
  try {{
    const reg = await navigator.serviceWorker.ready;
    const permission = await Notification.requestPermission();
    
    if (permission !== 'granted') {{
      throw new Error('Permission denied');
    }}
    
    const sub = await reg.pushManager.subscribe({{
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(vapidPublicKey)
    }});
    
    await sendSubscriptionToServer(sub);
    dismissPushPrompt();
    showPushStatus(true);
    console.log('Push subscribed!');
  }} catch (err) {{
    console.error('Push subscribe failed:', err);
    if (btn) btn.disabled = false;
    alert('Failed to enable notifications. Please try again.');
  }}
}}

async function sendSubscriptionToServer(subscription) {{
  try {{
    await fetch('/api/push/subscribe', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify(subscription)
    }});
  }} catch (err) {{
    console.error('Failed to send subscription:', err);
  }}
}}

function showPushStatus(enabled) {{
  // Could add a status indicator in header
  console.log('Push notifications:', enabled ? 'enabled' : 'disabled');
}}

// Initialize push notifications
document.addEventListener('DOMContentLoaded', initPushNotifications);

// ===== SITE NOTIFICATION BANNER =====
fetch('/notification.json?v=' + Date.now())
  .then(r => r.json())
  .then(n => {{
    if (!n.enabled) return;
    if (localStorage.getItem('sn_dismissed_' + n.id || '')) return;
    const banner = document.getElementById('site-notification');
    if (!banner) return;
    
    const types = {{update: '🔄', news: '📢', alert: '⚠️', promo: '🔥'}};
    const icon = types[n.type] || '📢';
    var linkHtml = n.link ? '<a href="' + n.link + '" class="sn-link" target="_blank">' + (n.link_text || 'Learn More') + '</a>' : '';
    
    banner.innerHTML = '<div class="sn-inner ' + n.type + '">' +
      '<span class="sn-icon">' + icon + '</span>' +
      '<span class="sn-msg">' + n.message + '</span>' +
      linkHtml +
      '<button class="sn-close" onclick="var p=this.parentElement.parentElement;p.parentElement.removeChild(p);localStorage.setItem(&quot;sn_dismissed_' + (n.id || '') + '&quot;,&quot;1&quot;)">&times;</button>' +
    '</div>';
    banner.style.display = '';
  }}).catch(() => {{}});
</script>

</body>
</html>'''
    return html

def generate_sitemap():
    """Generate a basic sitemap.xml."""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>''' + SITE_URL + '''/</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>'''

def generate_robots():
    """Generate robots.txt."""
    return f'''User-agent: *
Allow: /
Sitemap: {SITE_URL}/sitemap.xml
Allow: /5d056d40300e29ccd5adea9fca179696.txt
'''

def main():
    print("🚀 Rupeewa News Daily — Build")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    all_news = []
    for source_name, info in FEEDS.items():
        print(f"📡 {source_name}...", end=' ')
        xml_data = fetch_rss(info['url'])
        if xml_data:
            items = parse_rss(xml_data, source_name)
            print(f"✅ {len(items)} articles")
            all_news.extend(items)
        else:
            print("❌ Failed")
    
    all_news.sort(key=lambda x: x.get('published', ''), reverse=True)
    seen = set()
    unique = []
    for item in all_news:
        t = item['title'].lower().strip() if item['title'] else ''
        if t and t not in seen:
            seen.add(t)
            unique.append(item)

    print(f"\n📊 {len(unique)} unique articles from {len(FEEDS)} sources")
    
    # ── Include custom articles from admin/custom_articles.json ──
    custom_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'admin', 'custom_articles.json')
    if os.path.exists(custom_path):
        try:
            with open(custom_path, 'r', encoding='utf-8') as f:
                custom_data = json.load(f)
            custom_articles = custom_data.get('articles', [])
            for art in custom_articles:
                if art.get('is_hidden'):
                    continue
                unique.insert(0, {
                    'title': art.get('title', 'Untitled'),
                    'description': art.get('content', ''),
                    'link': SITE_URL,
                    'source': 'Custom',
                    'creator': art.get('author', 'Admin'),
                    'published': art.get('created_at', datetime.now().isoformat()),
                    'image': art.get('image_url', '')
                })
            print(f"📝 {len([a for a in custom_articles if not a.get('is_hidden')])} custom articles included")
        except:
            print("⚠️ Could not read custom articles")
    print()
    
    html = generate_html(unique)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'index.html')
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✅ index.html ({len(html)} bytes)")
    print(f"   → {out}")
    
    # Generate sitemap.xml
    sm = generate_sitemap()
    sm_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sitemap.xml')
    with open(sm_path, 'w', encoding='utf-8') as f:
        f.write(sm)
    print(f"✅ sitemap.xml ({len(sm)} bytes)")
    
    # Generate robots.txt
    rb = generate_robots()
    rb_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'robots.txt')
    with open(rb_path, 'w', encoding='utf-8') as f:
        f.write(rb)
    print(f"✅ robots.txt ({len(rb)} bytes)")
    
    # Show sources
    for s in sorted(set(i['source'] for i in unique)):
        count = sum(1 for i in unique if i['source'] == s)
        imgs = sum(1 for i in unique if i['source'] == s and i.get('image'))
        print(f"   {s}: {count} articles, {imgs} with images")

if __name__ == '__main__':
    main()

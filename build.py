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
SITE_NAME = "Rocket News Daily"
SITE_DESC = "Stay ahead with the latest tech news, AI breakthroughs, startup stories, and gadget reviews. Curated daily from Hacker News, TechCrunch, The Verge, and more."
HERO_IMG = "https://raw.githubusercontent.com/Rocketnew/rocket-tech/main/assets/og-default.png"

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
        "logo": SITE_URL + "/logo.svg",
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
                "logo": {
                    "@type": "ImageObject",
                    "url": SITE_URL + "/logo.svg"
                }
            },
            "url": item["link"],
            "mainEntityOfPage": {
                "@type": "WebPage",
                "@id": item["link"]
            }
        }
        article_blocks.append(json.dumps(schema, ensure_ascii=False))

    return org_schema, website_schema, article_blocks

def generate_html(all_news):
    now = datetime.now().strftime('%b %d, %Y \u00b7 %I:%M %p')
    sources = sorted(set(item['source'] for item in all_news))
    load_more_html = '<div class="load-more-wrapper"><button id="loadMore" class="load-more-btn">Show More Stories</button></div>' if len(all_news) > 48 else ''

    # Generate JSON-LD
    json_org, json_website, json_articles = generate_jsonld(all_news)
    json_articles_html = '\n'.join(
        f'  <script type="application/ld+json">{block}</script>'
        for block in json_articles
    )

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
  <title>{SITE_NAME} \u2014 Today's Top Tech News</title>
  <meta name="description" content="{SITE_DESC}">
  <meta name="robots" content="index, follow">
  <meta name="keywords" content="tech news, AI, startups, gadgets, Hacker News, TechCrunch, The Verge, technology, daily news, programming">
  <meta name="author" content="{SITE_NAME}">
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

<header>
  <nav class="nav-inner" aria-label="Main navigation">
    <div class="nav-left">
      <a href="/" class="nav-logo" aria-label="{SITE_NAME} Home">
        <img src="logo.svg" alt="{SITE_NAME}" class="nav-logo-svg" width="220" height="55">
      </a>
    </div>
    <div class="nav-right">
      <span class="nav-stats">{len(display_news)} stories</span>
      <span class="nav-update">Updated {now}</span>
    </div>
  </nav>
</header>

<main>
  <section class="hero-section" aria-label="Featured stories">
    <div class="hero-header">
      <h1>Today's <span class="gradient-text">Tech</span></h1>
      <p>The latest news from across the tech world \u2014 curated daily.</p>
    </div>
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
'''

def main():
    print("🚀 Rocket News Daily — Build")
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

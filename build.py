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
                desc = desc[:desc.rfind(' ')] + '…'

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
                desc = desc[:desc.rfind(' ')] + '…'
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

def generate_html(all_news):
    now = datetime.now().strftime('%b %d, %Y · %I:%M %p')
    sources = sorted(set(item['source'] for item in all_news))
    load_more_html = '<div class="load-more-wrapper"><button id="loadMore" class="load-more-btn">Show More Stories</button></div>' if len(all_news) > 48 else ''

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
        src_class = item['source'].lower().replace(' ', '').replace('.', '')

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
    for item in display_news:
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

        cards_html += f'''
    <div class="news-card source-accent-{src_class}" data-source="{src_class}">
      <div class="card-img-wrapper">
        <div class="card-img"{card_img_style}></div>
        <div class="card-fallback"{fallback_hidden}>
          <div class="source-gradient source-gradient-{src_class}"></div>
          <div class="source-pattern"></div>
          <span class="source-icon" style="background:{color};color:#000">{icon}</span>
        </div>
        <span class="card-source-tag" style="background:{color};color:#000">{source}</span>
      </div>
      <div class="card-body">
        <h3><a href="{link}" target="_blank" rel="noopener">{title}</a></h3>
        {f'<p>{desc}</p>' if desc else ''}
        <div class="card-meta">
          <span class="card-time">{time_ago}</span>
          {f'<span class="card-author">{creator}</span>' if creator else ''}
          <span class="card-arrow">→</span>
        </div>
      </div>
    </div>'''

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
  <title>Rocket News Daily — Tech News</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="style.css">
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🚀</text></svg>">
</head>
<body>

<header>
  <nav class="nav-inner">
    <div class="nav-left">
      <a href="/" class="nav-logo">
        <span class="nav-logo-icon">🚀</span>
        <span class="nav-logo-text">Rocket News</span>
        <span class="nav-logo-badge">Daily</span>
      </a>
    </div>
    <div class="nav-right">
      <span class="nav-stats">{len(display_news)} stories</span>
      <span class="nav-update">Updated {now}</span>
    </div>
  </nav>
</header>

<main>
  <section class="hero-section">
    <div class="hero-header">
      <h1>Today's <span class="gradient-text">Tech</span></h1>
      <p>The latest news from across the tech world — curated daily.</p>
    </div>
    <div class="featured-grid">
      {hero_cards_html}
    </div>
  </section>

  <section class="filter-section">
    <div class="filter-inner">
      <button class="cat-btn active" data-filter="all">All</button>
      {source_buttons}
    </div>
  </section>

  <section class="news-section">
    <div class="news-grid" id="newsGrid">
      {cards_html}
    </div>
    {load_more_html}
  </section>
</main>

<footer>
  <div class="footer-inner">
    <div class="footer-brand">🚀 Rocket News Daily</div>
    <div class="footer-links">
      <a href="https://github.com/Rocketnew/rocket-tech" target="_blank">GitHub</a>
      <span>·</span>
      <span>Daily at 7 AM</span>
      <span>·</span>
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
</script>

</body>
</html>'''
    return html

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
    # Show sources
    for s in sorted(set(i['source'] for i in unique)):
        count = sum(1 for i in unique if i['source'] == s)
        imgs = sum(1 for i in unique if i['source'] == s and i.get('image'))
        print(f"   {s}: {count} articles, {imgs} with images")

if __name__ == '__main__':
    main()

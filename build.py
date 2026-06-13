#!/usr/bin/env python3
"""
Rocket News Daily — Build Script
Fetches tech news from RSS feeds and generates index.html
"""

import json
import os
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from html import escape

# RSS Feed Sources
FEEDS = {
    "Hacker News": {
        "url": "https://hnrss.org/frontpage?count=12",
        "color": "hackernews"
    },
    "TechCrunch": {
        "url": "https://techcrunch.com/feed/",
        "color": "techcrunch"
    },
    "The Verge": {
        "url": "https://www.theverge.com/rss/index.xml",
        "color": "theverge"
    },
    "DEV Community": {
        "url": "https://dev.to/feed",
        "color": "devto"
    },
    "Ars Technica": {
        "url": "https://feeds.arstechnica.com/arstechnica/index",
        "color": "arstechnica"
    },
    "Wired": {
        "url": "https://www.wired.com/feed/rss",
        "color": "wired"
    }
}

def fetch_rss(url, timeout=10):
    """Fetch and parse an RSS feed."""
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Rocket News Daily/1.0 (news aggregator)"
            }
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
        return data
    except Exception as e:
        print(f"  ⚠️  Fetch failed: {e}")
        return None

def parse_rss(xml_data, source_name):
    """Parse RSS/Atom XML into news items."""
    items = []
    try:
        root = ET.fromstring(xml_data)
        # Handle both RSS and Atom formats
        ns = {
            'atom': 'http://www.w3.org/2005/Atom',
            'dc': 'http://purl.org/dc/elements/1.1/',
            'content': 'http://purl.org/rss/1.0/modules/content/'
        }

        # RSS 2.0
        for item in root.iter('item'):
            title = item.findtext('title', '')
            link = item.findtext('link', '')
            desc = item.findtext('description', '')
            pub_date = item.findtext('pubDate', '')
            creator = item.findtext('{http://purl.org/dc/elements/1.1/}creator', '')

            # Clean description
            desc = re.sub(r'<[^>]+>', '', desc)
            desc = desc.strip()
            if len(desc) > 250:
                desc = desc[:250] + '…'

            items.append({
                'title': title,
                'link': link,
                'description': desc,
                'source': source_name,
                'published': pub_date,
                'creator': creator
            })

        # Atom format
        for entry in root.iter('{http://www.w3.org/2005/Atom}entry'):
            title = entry.findtext('{http://www.w3.org/2005/Atom}title', '')
            link_el = entry.find('{http://www.w3.org/2005/Atom}link')
            link = link_el.get('href', '') if link_el is not None else ''
            desc_el = entry.find('{http://www.w3.org/2005/Atom}content')
            if desc_el is None:
                desc_el = entry.find('{http://www.w3.org/2005/Atom}summary')
            desc = desc_el.text if desc_el is not None else ''
            desc = re.sub(r'<[^>]+>', '', desc)
            desc = desc.strip()
            if len(desc) > 250:
                desc = desc[:250] + '…'
            pub_date = entry.findtext('{http://www.w3.org/2005/Atom}published', '') or \
                       entry.findtext('{http://www.w3.org/2005/Atom}updated', '')
            author_el = entry.find('{http://www.w3.org/2005/Atom}author')
            creator = author_el.findtext('{http://www.w3.org/2005/Atom}name', '') if author_el is not None else ''

            items.append({
                'title': title,
                'link': link,
                'description': desc,
                'source': source_name,
                'published': pub_date,
                'creator': creator
            })

    except Exception as e:
        print(f"  ⚠️  Parse error: {e}")

    return items

def format_time(pub_date_str):
    """Format published date string to relative time."""
    if not pub_date_str:
        return ''

    # Try common date formats
    formats = [
        '%a, %d %b %Y %H:%M:%S %z',
        '%a, %d %b %Y %H:%M:%S %Z',
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y-%m-%dT%H:%M:%S.%f%z',
        '%Y-%m-%dT%H:%M:%SZ',
        '%Y-%m-%dT%H:%M:%S',
    ]

    pub_date = None
    for fmt in formats:
        try:
            pub_date = datetime.strptime(pub_date_str.strip(), fmt)
            break
        except (ValueError, AttributeError):
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
    """Generate the complete HTML page."""
    now = datetime.now().strftime('%B %d, %Y at %I:%M %p')

    # Categories for filter buttons
    sources = sorted(set(item['source'] for item in all_news))

    # Build cards HTML
    cards_html = ''
    for item in all_news:
        source_class = item['source'].lower().replace(' ', '')
        color_class = FEEDS.get(item['source'], {}).get('color', 'hackernews')
        time_ago = format_time(item['published'])
        title = escape(item['title']) if item['title'] else 'Untitled'
        desc = escape(item['description']) if item['description'] else 'No description available.'
        link = escape(item['link']) if item['link'] else '#'
        source = escape(item['source'])

        cards_html += f"""
    <div class="news-card" data-source="{source_class}">
      <div class="card-top">
        <span class="source-tag source-{color_class}">{source}</span>
        <span class="time">{time_ago}</span>
      </div>
      <h2><a href="{link}" target="_blank" rel="noopener">{title}</a></h2>
      <p>{desc}</p>
      <div class="card-footer">
        <a href="{link}" class="read-more" target="_blank" rel="noopener">Read more →</a>
      </div>
    </div>"""

    source_buttons = ''
    for s in sources:
        s_class = s.lower().replace(' ', '')
        source_buttons += f'\n        <button class="cat-btn" data-filter="{s_class}">{escape(s)}</button>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Rocket News Daily — Latest Tech News</title>
  <link rel="stylesheet" href="style.css">
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🚀</text></svg>">
</head>
<body>

<header>
  <div class="header-inner">
    <div>
      <div class="logo">Rocket News</div>
      <div class="logo-sub">Daily Tech News</div>
    </div>
    <div class="header-right">
      <span class="update-badge">✦ Updated {now}</span>
      <span>{len(all_news)} stories • {len(sources)} sources</span>
    </div>
  </div>
</header>

<section class="hero">
  <h1>Latest in Tech</h1>
  <p>Curated tech news from the best sources — updated daily at 7:00 AM.</p>
</section>

<section class="categories">
  <button class="cat-btn active" data-filter="all">All</button>
  {source_buttons}
</section>

<main class="container">
  <div class="news-grid">
    {cards_html}
  </div>
</main>

<footer>
  <p>🚀 Rocket News Daily — Built with ❤️ | Data from RSS feeds | Updated daily at 7:00 AM</p>
</footer>

<script>
// Category filter
document.querySelectorAll('.cat-btn').forEach(btn => {{
  btn.addEventListener('click', () => {{
    document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const filter = btn.dataset.filter;
    document.querySelectorAll('.news-card').forEach(card => {{
      card.style.display = (filter === 'all' || card.dataset.source === filter) ? 'block' : 'none';
    }});
  }});
}});
</script>

</body>
</html>"""

    return html

def main():
    print("🚀 Rocket News Daily — Build Script")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    all_news = []
    for source_name, info in FEEDS.items():
        print(f"📡 Fetching {source_name}...")
        xml_data = fetch_rss(info['url'])
        if xml_data:
            items = parse_rss(xml_data, source_name)
            print(f"   ✅ Got {len(items)} articles")
            all_news.extend(items)
        else:
            print(f"   ❌ Failed to fetch")

    # Sort by published date (newest first)
    all_news.sort(key=lambda x: x.get('published', ''), reverse=True)

    # Remove duplicates by title (case-insensitive)
    seen_titles = set()
    unique_news = []
    for item in all_news:
        title_lower = item['title'].lower().strip() if item['title'] else ''
        if title_lower and title_lower not in seen_titles:
            seen_titles.add(title_lower)
            unique_news.append(item)

    print(f"\n📊 Total: {len(unique_news)} unique articles from {len(FEEDS)} sources")
    print()

    # Generate HTML
    html = generate_html(unique_news)

    # Write file
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'index.html')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✅ Generated index.html ({len(html)} bytes)")
    print(f"   → {output_path}")

if __name__ == '__main__':
    main()

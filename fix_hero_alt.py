#!/usr/bin/env python3
"""Fix hero_img_tag alt text in build.py"""
with open('/home/ubuntu/rocket-tech/build.py', 'r') as f:
    content = f.read()

# The target string: alt="" loading="lazy" width="1200" height="675" onerror="this.style.display=\'none\'">
# In the Python source file it appears as: alt="" loading="lazy"...
# Actually looking at the file content directly, the f-string uses single quotes:
# f'...alt="" loading="lazy" width="1200" height="675" onerror="this.style.display=\'none\'">'
# We need to replace alt="" with alt="{escape(title)}"

old = 'alt="" loading="lazy" width="1200" height="675" onerror="this.style.display=\'none\'">\' if img else \'\''
new = 'alt="{escape(title)}" loading="lazy" width="1200" height="675" onerror="this.style.display=\'none\'">\' if img else \'\''

if old in content:
    content = content.replace(old, new)
    with open('/home/ubuntu/rocket-tech/build.py', 'w') as f:
        f.write(content)
    print("✅ Fixed hero_img_tag alt text")
else:
    print("❌ Could not find exact match, trying alternative approach...")
    # Try finding just the alt="" part
    idx = content.find('hero_img_tag')
    if idx > 0:
        # Find the alt="" in the hero_img_tag line
        line_start = content.rfind('\n', 0, idx) + 1
        line_end = content.find('\n', idx)
        line = content[line_start:line_end]
        print(f"Line content: {repr(line)}")
        
        # The file uses single quotes for the f-string
        # alt="" is a literal in the string
        old2 = 'alt=""'
        new2 = 'alt="{escape(title)}"'
        # Only replace in hero_img_tag line (first occurrence after hero_img_tag)
        if old2 in line:
            line_fixed = line.replace(old2, new2, 1)  # only first occurrence
            content = content[:line_start] + line_fixed + content[line_end:]
            with open('/home/ubuntu/rocket-tech/build.py', 'w') as f:
                f.write(content)
            print("✅ Fixed using alternative method")

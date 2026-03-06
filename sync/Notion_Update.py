"""
Notion_Update.py — Publishes generated course content to Notion.

Three page levels:
  Level 1: Course Home Page (intro already added, then module headings + page links)
  Level 2: Module Pages (overview + chapter toggle headings with Outline/Content)
  Level 3: Chapter Pages (under "All Chapters" page, linked from Content toggles)

IMPORTANT: After format_text(), headings in summaries are ### level (LLM outputs ####).
"""

import os
import time
import re
from dotenv import load_dotenv
from notion_client import Client
from Markdown_Function import format_outlines_notion, unpack_outlines

load_dotenv()

notion = Client(auth=os.environ['NOTION_TOKEN'])
COURSES_PAGE_ID = os.environ['NOTION_COURSES_PAGE_ID']

print("hello")
# ─────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────

def create_top_page(page_title):
    new_page = notion.pages.create(
        parent={"page_id": COURSES_PAGE_ID},
        properties={"title": [{"text": {"content": page_title}}]}
    )
    print(f"Created course page: {page_title}")
    time.sleep(0.35)
    return new_page["id"]


def get_children_pages(page_id):
    pages = {}
    has_more = True
    cursor = None
    while has_more:
        kwargs = {"block_id": page_id}
        if cursor:
            kwargs["start_cursor"] = cursor
        result = notion.blocks.children.list(**kwargs)
        for block in result["results"]:
            if block["type"] == "child_page":
                pages[block["child_page"]["title"]] = block["id"]
        has_more = result.get("has_more", False)
        cursor = result.get("next_cursor")
        time.sleep(0.35)
    return pages


def _parse_rich_text(text):
    rich_text = []
    parts = re.split(r'(\*\*.*?\*\*)', text)
    for part in parts:
        if not part:
            continue
        if part.startswith('**') and part.endswith('**'):
            content = part[2:-2]
            if content:
                rich_text.append({"type": "text", "text": {"content": content[:2000]}, "annotations": {"bold": True}})
        else:
            for i in range(0, len(part), 2000):
                rich_text.append({"type": "text", "text": {"content": part[i:i+2000]}})
    if not rich_text:
        rich_text.append({"type": "text", "text": {"content": ""}})
    return rich_text


def _is_category_header(bullet_text):
    """Check if bullet text is a category header: entirely bold and ends with colon.
    e.g. **Chair Options:** or **Monitor Stands:**"""
    stripped = bullet_text.strip()
    if stripped.startswith('**') and stripped.endswith(':**'):
        inner = stripped[2:-2]
        return '**' not in inner
    return False


def markdown_to_notion_blocks(text):
    blocks = []
    if not text:
        return blocks
    in_category = False

    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s in ('---', '***', '___'):
            in_category = False
            blocks.append({"object": "block", "type": "divider", "divider": {}})
            continue
        if s.startswith('### '):
            in_category = False
            blocks.append({"object": "block", "type": "heading_3",
                           "heading_3": {"rich_text": [{"type": "text", "text": {"content": s[4:][:2000]}}]}})
            continue
        if s.startswith('###'):
            in_category = False
            blocks.append({"object": "block", "type": "heading_3",
                           "heading_3": {"rich_text": [{"type": "text", "text": {"content": s[3:][:2000]}}]}})
            continue
        if s.startswith('## '):
            in_category = False
            blocks.append({"object": "block", "type": "heading_2",
                           "heading_2": {"rich_text": [{"type": "text", "text": {"content": s[3:][:2000]}}]}})
            continue
        if s.startswith('##'):
            in_category = False
            blocks.append({"object": "block", "type": "heading_2",
                           "heading_2": {"rich_text": [{"type": "text", "text": {"content": s[2:][:2000]}}]}})
            continue
        if s.startswith('- ') or s.startswith('* '):
            bullet_text = s[2:]
            if _is_category_header(bullet_text):
                # Category header → bold paragraph
                in_category = True
                blocks.append({"object": "block", "type": "paragraph",
                               "paragraph": {"rich_text": _parse_rich_text(bullet_text)}})
            else:
                # Regular bullet — flat under category or standalone
                blocks.append({"object": "block", "type": "bulleted_list_item",
                               "bulleted_list_item": {"rich_text": _parse_rich_text(bullet_text)}})
            continue
        # Non-bullet line breaks category grouping
        in_category = False
        if len(s) > 2000:
            for i in range(0, len(s), 2000):
                blocks.append({"object": "block", "type": "paragraph",
                               "paragraph": {"rich_text": _parse_rich_text(s[i:i+2000])}})
        else:
            blocks.append({"object": "block", "type": "paragraph",
                           "paragraph": {"rich_text": _parse_rich_text(s)}})
    return blocks


def _outline_to_notion_blocks(text):
    """Parse outline text into bold paragraph headers + flat bullets.

    Lines starting with - **Objective:**, - **Key Topics:**, or - **Activities:**
    become bold paragraph blocks. Subsequent - lines become flat bulleted_list_item
    blocks. No nesting — avoids Notion API depth limits inside toggle headings.
    """
    PARENTS = ('Objective:', 'Key Topics:', 'Activities:')
    blocks = []
    if not text:
        return blocks

    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue

        bullet_text = None
        if s.startswith('- '):
            bullet_text = s[2:]
        elif s.startswith('* '):
            bullet_text = s[2:]

        if bullet_text is not None:
            is_parent = False
            for p in PARENTS:
                if f'**{p}**' in bullet_text or bullet_text.startswith(f'**{p}'):
                    is_parent = True
                    break

            if is_parent:
                blocks.append({
                    "object": "block", "type": "paragraph",
                    "paragraph": {"rich_text": _parse_rich_text(bullet_text)}
                })
            else:
                blocks.append({
                    "object": "block", "type": "bulleted_list_item",
                    "bulleted_list_item": {"rich_text": _parse_rich_text(bullet_text)}
                })
        else:
            blocks.append({
                "object": "block", "type": "paragraph",
                "paragraph": {"rich_text": _parse_rich_text(s)}
            })

    return blocks


def add_content_blocks(page_id, text):
    blocks = markdown_to_notion_blocks(text)
    if not blocks:
        return
    for i in range(0, len(blocks), 100):
        notion.blocks.children.append(block_id=page_id, children=blocks[i:i+100])
        time.sleep(0.35)


# ─────────────────────────────────────────────
# Level 1: Course Introduction (unchanged)
# ─────────────────────────────────────────────

def course_introduction_to_notion(course_introduction, course_page_id):
    for title, content in course_introduction.items():
        if 'Course Title' in title:
            print(f"Adding introduction: {title[:30]}")
            notion.blocks.children.append(
                block_id=course_page_id,
                children=[{"object": "block", "type": "heading_1",
                           "heading_1": {"rich_text": [{"type": "text", "text": {"content": "Introduction"}}]}}])
            time.sleep(0.35)
            add_content_blocks(course_page_id, content)
        # Module entries are handled by course_outlines_to_notion — skip them here


# ─────────────────────────────────────────────
# Parser: Extract structure from ### headings
# ─────────────────────────────────────────────

def _get_heading(line):
    """Extract heading text from a line. Returns (text, level) or None.
    Handles: ### Title, ###Title, ## Title, ##Title"""
    s = line.strip()
    if s.startswith('### '):
        return (s[4:].strip(), 3)
    if s.startswith('###'):
        return (s[3:].strip(), 3)
    if s.startswith('## '):
        return (s[3:].strip(), 2)
    if s.startswith('##'):
        return (s[2:].strip(), 2)
    return None


def _parse_module_summary(summary_text):
    """Parse module summary into structured data.

    Input headings are ### (format_text converts #### to ###):
      ### Module N: Title
      ### Overview
      ### Chapter N: Title → chapter with outline content
      ### N: Sub-title → sub-section with its own outline content

    Returns: (overview_text, entries_list)
    where entries_list = [(title, outline_text, is_chapter_start), ...]
    is_chapter_start=True for "Chapter N:" entries (divider before these)
    is_chapter_start=False for "N.M:" sub-section entries (no divider)
    """
    overview_lines = []
    entries = []
    cur_title = None
    cur_ch_num = 0
    cur_outline = []
    cur_is_chapter = False
    state = 'pre'

    for line in summary_text.splitlines():
        s = line.strip()
        if not s or s in ('---', '***', '___'):
            continue

        h = _get_heading(s)
        if h:
            text, level = h

            # Module heading → skip
            if re.match(r'Module\s+\d+', text, re.IGNORECASE):
                continue

            # Overview
            if text.lower().startswith('overview'):
                if cur_title:
                    entries.append((cur_title, '\n'.join(cur_outline), cur_is_chapter))
                    cur_title = None; cur_outline = []
                state = 'overview'
                continue

            # Chapter heading
            ch = re.match(r'Chapter\s+(\d+)\s*:\s*(.+)', text, re.IGNORECASE)
            if ch:
                if cur_title:
                    entries.append((cur_title, '\n'.join(cur_outline), cur_is_chapter))
                cur_ch_num = int(ch.group(1))
                cur_title = f"Chapter {cur_ch_num}: {ch.group(2).strip()}"
                cur_outline = []
                cur_is_chapter = True
                state = 'chapter'
                continue

            # Sub-section (### N: Title) — its own entry
            sub = re.match(r'(\d+)\s*:\s*(.+)', text)
            if sub and cur_ch_num:
                if cur_title:
                    entries.append((cur_title, '\n'.join(cur_outline), cur_is_chapter))
                sub_num = int(sub.group(1))
                sub_title = sub.group(2).strip()
                cur_title = f"{cur_ch_num}.{sub_num}: {sub_title}"
                cur_outline = []
                cur_is_chapter = False
                state = 'sub'
                continue

            # Other heading — treat as content
            if state == 'overview':
                overview_lines.append(s)
            elif state in ('chapter', 'sub') and cur_title:
                cur_outline.append(s)
            continue

        # Regular content line
        if state == 'overview' or state == 'pre':
            overview_lines.append(s)
        elif state in ('chapter', 'sub') and cur_title:
            cur_outline.append(s)

    # Flush last entry
    if cur_title:
        entries.append((cur_title, '\n'.join(cur_outline), cur_is_chapter))

    return '\n'.join(overview_lines), entries


# ─────────────────────────────────────────────
# Level 1 + 2: Module Structure Builder
# ─────────────────────────────────────────────

def course_outlines_to_notion(gemini_module_summaries, course_page_id, course_introduction=None):
    """For each module:
      Level 1: divider + heading + intro text + module page link
      Level 2: overview + chapter toggles inside module page
    """
    # Build lookup of module intro texts
    module_intros = {}
    if course_introduction:
        for title, content in course_introduction.items():
            if 'Module' in title or 'module' in title:
                module_intros[title.strip()] = content

    for course_title, modules in gemini_module_summaries.items():
        for module_title, summary_text in modules.items():

            # ── Level 1: heading + intro text + page on course home page ──
            intro_text = None
            for intro_title, intro_content in module_intros.items():
                if module_title.strip() in intro_title or intro_title in module_title.strip():
                    intro_text = intro_content
                    break

            notion.blocks.children.append(
                block_id=course_page_id,
                children=[
                    {"object": "block", "type": "divider", "divider": {}},
                    {"object": "block", "type": "heading_2",
                     "heading_2": {"rich_text": [{"type": "text", "text": {"content": module_title[:2000]}}]}}
                ]
            )
            time.sleep(0.35)

            if intro_text:
                add_content_blocks(course_page_id, intro_text)

            new_page = notion.pages.create(
                parent={"page_id": course_page_id},
                properties={"title": [{"text": {"content": module_title}}]}
            )
            time.sleep(0.35)
            module_page_id = new_page["id"]
            print(f"Created module page: {module_title}")

            # ── Level 2: inside the module page ──
            overview_text, chapters = _parse_module_summary(summary_text)

            # Overview section
            if overview_text:
                notion.blocks.children.append(
                    block_id=module_page_id,
                    children=[{"object": "block", "type": "heading_3",
                               "heading_3": {"rich_text": [{"type": "text", "text": {"content": "Overview"}}]}}]
                )
                time.sleep(0.35)
                add_content_blocks(module_page_id, overview_text)
                notion.blocks.children.append(
                    block_id=module_page_id,
                    children=[{"object": "block", "type": "divider", "divider": {}}]
                )
                time.sleep(0.35)

            # Chapter and sub-section toggles
            for entry_title, outline_text, is_chapter_start in chapters:
                # Divider only before chapter entries, not sub-sections
                if is_chapter_start:
                    notion.blocks.children.append(
                        block_id=module_page_id,
                        children=[{"object": "block", "type": "divider", "divider": {}}]
                    )
                    time.sleep(0.35)

                outline_blocks = _outline_to_notion_blocks(outline_text)
                if not outline_blocks:
                    outline_blocks = [{"object": "block", "type": "paragraph",
                                       "paragraph": {"rich_text": [{"type": "text", "text": {"content": " "}}]}}]

                content_placeholder = {"object": "block", "type": "paragraph",
                                        "paragraph": {"rich_text": [{"type": "text", "text": {"content": "Content links below."}}]}}

                toggle_block = {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": entry_title[:2000]}}],
                        "is_toggleable": True,
                        "children": [
                            {"object": "block", "type": "heading_3",
                             "heading_3": {
                                 "rich_text": [{"type": "text", "text": {"content": "Outline"}}],
                                 "is_toggleable": True,
                                 "children": outline_blocks[:100]
                             }},
                            {"object": "block", "type": "heading_3",
                             "heading_3": {
                                 "rich_text": [{"type": "text", "text": {"content": "Content"}}],
                                 "is_toggleable": True,
                                 "children": [content_placeholder]
                             }}
                        ]
                    }
                }

                notion.blocks.children.append(block_id=module_page_id, children=[toggle_block])
                time.sleep(0.35)


# ─────────────────────────────────────────────
# Level 3: Chapter Pages + Content Toggle Links
# ─────────────────────────────────────────────

def _get_module_number(title):
    m = re.match(r'Module\s+(\d+)', title, re.IGNORECASE)
    return m.group(1) if m else '?'


def _get_chapter_toggles(module_page_id):
    toggles = []
    has_more = True
    cursor = None
    while has_more:
        kwargs = {"block_id": module_page_id}
        if cursor:
            kwargs["start_cursor"] = cursor
        result = notion.blocks.children.list(**kwargs)
        for block in result["results"]:
            if block["type"] == "heading_2" and block["heading_2"].get("is_toggleable"):
                title = block["heading_2"]["rich_text"][0]["plain_text"] if block["heading_2"]["rich_text"] else ""
                toggles.append((block["id"], title))
        has_more = result.get("has_more", False)
        cursor = result.get("next_cursor")
        time.sleep(0.35)
    return toggles


def _find_content_toggle_id(chapter_toggle_id):
    result = notion.blocks.children.list(block_id=chapter_toggle_id)
    time.sleep(0.35)
    for block in result["results"]:
        if block["type"] == "heading_3" and block["heading_3"].get("is_toggleable"):
            if block["heading_3"]["rich_text"]:
                if block["heading_3"]["rich_text"][0]["plain_text"].lower().strip() == "content":
                    return block["id"]
    return None


def page_to_notion(content, course_page_id):
    """Create chapter pages under 'All Chapters', link from Content toggles.

    Each content dict key (Chapter N and N.M sub-sections) maps 1-to-1
    to a toggle on the module page, matched by position.
    """
    all_ch = notion.pages.create(
        parent={"page_id": course_page_id},
        properties={"title": [{"text": {"content": "All Chapters"}}]}
    )
    all_chapters_id = all_ch["id"]
    print("Created 'All Chapters' page")
    time.sleep(0.35)

    module_pages = get_children_pages(course_page_id)

    for module_title, chapters_dict in content.items():
        module_num = _get_module_number(module_title)
        prefix = f"M{module_num}"

        # Find module page
        module_page_id = None
        for name, pid in module_pages.items():
            if name.strip() == module_title.strip():
                module_page_id = pid
                break
        if not module_page_id:
            for name, pid in module_pages.items():
                if f"Module {module_num}" in name:
                    module_page_id = pid
                    break

        chapter_toggles = _get_chapter_toggles(module_page_id) if module_page_id else []

        # 1-to-1: each dict key matches the next toggle by position
        toggle_idx = 0
        for chapter_title, chapter_text in chapters_dict.items():
            page_title = f"{prefix} - {chapter_title}"
            new_page = notion.pages.create(
                parent={"page_id": all_chapters_id},
                properties={"title": [{"text": {"content": page_title}}]}
            )
            chapter_page_id = new_page["id"]
            print(f"Created: {page_title}")
            time.sleep(0.35)

            add_content_blocks(chapter_page_id, chapter_text)

            # Link to this entry's Content toggle
            if toggle_idx < len(chapter_toggles):
                content_id = _find_content_toggle_id(chapter_toggles[toggle_idx][0])
                if content_id:
                    notion.blocks.children.append(
                        block_id=content_id,
                        children=[{"object": "block", "type": "link_to_page",
                                   "link_to_page": {"type": "page_id", "page_id": chapter_page_id}}])
                    time.sleep(0.35)
            toggle_idx += 1


# ─────────────────────────────────────────────
# Data Transform (no API calls)
# ─────────────────────────────────────────────

def outline_reformat(gemini_outlines):
    outlines = unpack_outlines(gemini_outlines)
    outline = {}
    for module_title, module_summary in outlines.items():
        p = {}
        for page_title, page_summary in module_summary.items():
            if "Module" not in page_title:
                p[page_title] = page_summary
            outline[module_title] = p
    return outline
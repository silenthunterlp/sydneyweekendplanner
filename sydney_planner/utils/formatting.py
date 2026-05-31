import re


def markdown_to_whatsapp(text: str) -> str:
    """Convert Markdown to WhatsApp-compatible formatting."""
    # Bold: **text** → *text*
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)
    # Italic: _text_ stays as-is (WhatsApp uses _)
    # Headers: ### Heading → *Heading*
    text = re.sub(r"^#{1,3}\s+(.+)$", r"*\1*", text, flags=re.MULTILINE)
    # Remove markdown links, keep text
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
    # Code blocks → plain
    text = re.sub(r"`(.+?)`", r"\1", text)
    return text.strip()


def markdown_to_telegram(text: str) -> str:
    """Telegram supports MarkdownV2 but it's strict — use HTML mode instead."""
    # Convert **bold** → <b>bold</b>
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    # Convert _italic_ → <i>italic</i>
    text = re.sub(r"_(.+?)_", r"<i>\1</i>", text)
    # Convert ### Heading → <b>Heading</b>
    text = re.sub(r"^#{1,3}\s+(.+)$", r"<b>\1</b>", text, flags=re.MULTILINE)
    # Convert [text](url) → <a href="url">text</a>
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', text)
    return text.strip()

import os
import re
import base64
import binascii
import tempfile
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

MAX_BYTES = 5 * 1024 * 1024

def decode_js_escapes(text):
    changes = 0
    def unicode_repl(m):
        nonlocal changes
        changes += 1
        return chr(int(m.group(1), 16))
    def hex_repl(m):
        nonlocal changes
        changes += 1
        return chr(int(m.group(1), 16))
    text = re.sub(r"\\\\u\\{([0-9a-fA-F]{1,6})\\}", unicode_repl, text)
    text = re.sub(r"\\\\u([0-9a-fA-F]{4})", unicode_repl, text)
    text = re.sub(r"\\\\x([0-9a-fA-F]{2})", hex_repl, text)
    return text, changes

def decode_base64_candidates(text):
    changes = 0
    pattern = re.compile(r'''(?P<q>["'])(?P<data>[A-Za-z0-9+/]{80,}={0,2})(?P=q)''')
    def repl(m):
        nonlocal changes
        try:
            decoded = base64.b64decode(m.group("data"), validate=True).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError, ValueError):
            return m.group(0)
        if not decoded or sum(c.isprintable() or c in "\\r\\n\\t" for c in decoded) / len(decoded) < 0.92:
            return m.group(0)
        if not any(x in decoded for x in ("<", "function", "const ", "var ", "let ", "=>", "document", "window")):
            return m.group(0)
        changes += 1
        q = m.group("q")
        escaped = decoded.replace("\\\\", "\\\\\\\\").replace(q, "\\\\" + q)
        return q + escaped + q
    return pattern.sub(repl, text), changes

def basic_js_format(text):
    # Conservative formatting only; no code execution.
    text = re.sub(r";(?=\\S)", ";\\n", text)
    text = re.sub(r"}\\s*(?=(?:function|const|let|var|class)\\b)", "}\\n\\n", text)
    return text

def analyze_html(raw):
    source = raw.decode("utf-8-sig", errors="replace")
    notes = []
    source, n_esc = decode_js_escapes(source)
    if n_esc:
        notes.append(f"Common JS escapes decoded: {n_esc}")
    source, n_b64 = decode_base64_candidates(source)
    if n_b64:
        notes.append(f"Likely Base64 text strings decoded: {n_b64}")
    source = basic_js_format(source)
    low = source.lower()
    if any(x in low for x in ("webdriver", "__playwright__binding__", "headlesschrome")):
        notes.append("Anti-automation / anti-debug checks detected.")
    if re.search(r"\\b(eval|Function)\\s*\\(", source):
        notes.append("Dynamic code execution pattern detected (not executed).")
    if re.search(r"\\b(atob|btoa)\\s*\\(", source):
        notes.append("Base64-related runtime calls detected.")
    if "protected" in low and "obfuscat" in low:
        notes.append("Protection/obfuscation header detected.")
    if not notes:
        notes.append("No common decoding patterns were confidently detected.")
    notes.append("Custom encryption, key-dependent payloads, or runtime validation may not be reversible by static decoding.")
    report = "HTML Decoder Bot report\\n\\n" + "\\n".join("- " + x for x in notes)
    report += "\\n\\nSafety: uploaded scripts were analyzed as text and were not executed."
    return source.encode("utf-8"), report.encode("utf-8")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 HTML Decoder Bot\\n\\n"
        "একটি .html / .htm / .js / .txt ফাইল Document হিসেবে পাঠাও।\\n"
        "আমি static analysis করব; uploaded JavaScript execute করব না।\\n"
        "Custom encryption বা secret key থাকলে সম্পূর্ণ decode নিশ্চিত নয়।"
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    doc = msg.document
    if not doc:
        return
    name = doc.file_name or "upload.html"
    if Path(name).suffix.lower() not in {".html", ".htm", ".js", ".txt"}:
        await msg.reply_text("শুধু .html, .htm, .js বা .txt ফাইল পাঠাও।")
        return
    if doc.file_size and doc.file_size > MAX_BYTES:
        await msg.reply_text("ফাইলটি 5 MB-এর বেশি। ছোট ফাইল পাঠাও।")
        return
    tg_file = await doc.get_file()
    with tempfile.TemporaryDirectory() as td:
        input_path = Path(td) / Path(name).name
        await tg_file.download_to_drive(custom_path=str(input_path))
        raw = input_path.read_bytes()
        if len(raw) > MAX_BYTES:
            await msg.reply_text("ফাইলটি 5 MB-এর বেশি।")
            return
        output, report = analyze_html(raw)
        out_path = Path(td) / ("decoded_" + Path(name).name)
        report_path = Path(td) / "decode_report.txt"
        out_path.write_bytes(output)
        report_path.write_bytes(report)
        with out_path.open("rb") as f:
            await msg.reply_document(document=f, filename=out_path.name,
                caption="Static cleanup শেষ। এটি সম্পূর্ণ decryption নাও হতে পারে।")
        with report_path.open("rb") as f:
            await msg.reply_document(document=f, filename="decode_report.txt", caption="Decode report")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "1) /start চাপো\\n2) HTML ফাইল Document হিসেবে পাঠাও\\n"
        "3) বট cleaned HTML ও report ফেরত দেবে।\\n"
        "Encrypted payload-এর key বট নিজে থেকে উদ্ভাবন করতে পারে না।"
    )

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN environment variable first.")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

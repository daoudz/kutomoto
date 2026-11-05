# Attribution Audit Script
with open("src/kutomoto/ui/index.html", "r", encoding="utf-8") as f:
    html = f.read()
assert "<title>kutomoto — Enterprise Form Automation — Copyrights reserved to 90Studio</title>" in html
assert "<strong>Copyrights reserved to 90Studio</strong>" in html
assert "kutomoto Automation Studio v1.0.0" in html
print("[ATTRIBUTION] HTML index.html title and footer: PASSED")

with open("src/kutomoto/server/app.py", "r", encoding="utf-8") as f:
    app_code = f.read()
assert '"copyright": __copyright__' in app_code
assert "from kutomoto import __copyright__" in app_code
assert "https://90studio.com/errors/" in app_code
print("[ATTRIBUTION] API RFC 7807 problem details handlers: PASSED")

with open("src/kutomoto/__main__.py", "r", encoding="utf-8") as f:
    cli_code = f.read()
assert "from kutomoto import __copyright__, __version__" in cli_code
assert "Copyrights reserved to 90Studio" in cli_code
assert "kutomoto" in cli_code
print("[ATTRIBUTION] CLI launcher __main__.py: PASSED")

with open("run_kutomoto.bat", "r", encoding="utf-8") as f:
    bat_code = f.read()
assert "kutomoto" in bat_code
assert "Copyrights reserved to 90Studio" in bat_code
print("[ATTRIBUTION] Windows batch launcher run_kutomoto.bat: PASSED")

with open("src/kutomoto/__init__.py", "r", encoding="utf-8") as f:
    init_code = f.read()
assert '__copyright__ = "Copyrights reserved to 90Studio"' in init_code
assert '__author__ = "90Studio"' in init_code
print("[ATTRIBUTION] Package __init__.py: PASSED")

print("[ATTRIBUTION AUDIT] ALL CHECKS PASSED!")

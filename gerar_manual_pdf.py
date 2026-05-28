# -*- coding: utf-8 -*-
"""Gera MANUAL_CONFIGURACAO.pdf a partir do arquivo Markdown."""
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
MD_PATH = ROOT / "MANUAL_CONFIGURACAO.md"
PDF_PATH = ROOT / "MANUAL_CONFIGURACAO.pdf"


def _markdown_para_html(texto_md: str) -> str:
    try:
        import markdown
    except ImportError:
        raise SystemExit(
            "Instale o pacote markdown: .\\venv\\Scripts\\python.exe -m pip install markdown"
        )

    corpo = markdown.markdown(
        texto_md,
        extensions=["tables", "fenced_code", "nl2br"],
    )
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Manual de Configuração — Automação NFe</title>
<style>
@page {{
    size: A4;
    margin: 18mm 16mm;
}}
body {{
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.45;
    color: #1a1a1a;
}}
h1 {{
    font-size: 20pt;
    color: #1f538d;
    border-bottom: 2px solid #1f538d;
    padding-bottom: 6px;
    margin-top: 0;
}}
h2 {{
    font-size: 14pt;
    color: #163d68;
    margin-top: 22px;
    page-break-after: avoid;
}}
h3 {{
    font-size: 12pt;
    margin-top: 16px;
    page-break-after: avoid;
}}
p, li {{
    margin: 6px 0;
}}
ul, ol {{
    padding-left: 22px;
}}
table {{
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0;
    font-size: 10pt;
}}
th, td {{
    border: 1px solid #ccc;
    padding: 6px 8px;
    text-align: left;
}}
th {{
    background: #e8f0fa;
}}
code {{
    background: #f4f4f4;
    padding: 1px 4px;
    border-radius: 3px;
    font-size: 9.5pt;
}}
hr {{
    border: none;
    border-top: 1px solid #ddd;
    margin: 20px 0;
}}
blockquote {{
    border-left: 4px solid #1f538d;
    margin: 10px 0;
    padding: 4px 12px;
    color: #444;
    background: #f8fafc;
}}
</style>
</head>
<body>
{corpo}
</body>
</html>"""


def gerar_pdf(caminho_md: Path = MD_PATH, caminho_pdf: Path = PDF_PATH) -> Path:
    if not caminho_md.is_file():
        raise FileNotFoundError(f"Manual não encontrado: {caminho_md}")

    texto = caminho_md.read_text(encoding="utf-8")
    html = _markdown_para_html(texto)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html, wait_until="networkidle")
        page.pdf(
            path=str(caminho_pdf),
            format="A4",
            print_background=True,
            margin={"top": "16mm", "bottom": "16mm", "left": "14mm", "right": "14mm"},
        )
        browser.close()

    return caminho_pdf


if __name__ == "__main__":
    destino = gerar_pdf()
    print(f"PDF gerado: {destino}")

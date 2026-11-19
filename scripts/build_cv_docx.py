#!/usr/bin/env python3
"""Builds a resume .docx from a Markdown draft, in the look of templates/cv_master.docx.

The master file is only read: its styles, numbering, header/footer and a few
paragraphs (name, contacts, education) are reused. The output must be another path.

    python3 scripts/build_cv_docx.py templates/cv_ai_engineering_draft.md templates/cv_ai_engineering.docx

Markdown the script understands:
    # NAME                      taken from the master, not from the draft
    **Title**                   the line under the name
    ## SECTION                  section heading with a rule under it
    ### A · B · C · Dates       entry header; the last part goes to the right edge
    - bullet with **bold**      bullet
    Stack: ...                  small grey line
    | Label | text |            skills row
    plain text                  paragraph (the first one under ### is the grey subtitle)
The contacts block and the EDUCATION section are copied from the master as they are.
"""

import re
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
MASTER = ROOT / "templates" / "cv_master.docx"
TEXT_WIDTH = 10080  # page 12240 minus two 1080 margins, in twips

GREY = ('<w:outline w:val="0"/><w:color w:val="555555"/><w:sz w:val="18"/><w:szCs w:val="18"/>'
        '<w:u w:color="555555"/>')
GREY_FILL = '<w14:textFill><w14:solidFill><w14:srgbClr w14:val="555555"/></w14:solidFill></w14:textFill>'


def run(text: str, bold: bool = False, italic: bool = False, grey: bool = False, date: bool = False) -> str:
    props = '<w:rStyle w:val="None"/>'
    if bold:
        props += '<w:b w:val="1"/><w:bCs w:val="1"/>'
    if italic or date:
        props += '<w:i w:val="1"/><w:iCs w:val="1"/>'
    if grey:
        props += GREY
    if date:
        props += '<w:outline w:val="0"/><w:color w:val="555555"/><w:u w:color="555555"/>'
    props += '<w:rtl w:val="0"/><w:lang w:val="en-US"/>'
    if grey or date:
        props += GREY_FILL
    return f'<w:r><w:rPr>{props}</w:rPr><w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


def rich(text: str, **style) -> str:
    """Runs for text with **bold** spans."""
    parts = re.split(r"\*\*(.+?)\*\*", text)
    return "".join(run(part, bold=index % 2 == 1, **style) for index, part in enumerate(parts) if part)


def paragraph(ppr: str, runs: str) -> str:
    return f'<w:p><w:pPr><w:pStyle w:val="Body"/>{ppr}</w:pPr>{runs}</w:p>'


def body(text: str, after: int = 60) -> str:
    return paragraph(f'<w:spacing w:after="{after}" w:line="276" w:lineRule="auto"/>', rich(text))


def subtitle(text: str) -> str:
    return paragraph('<w:spacing w:after="40" w:line="276" w:lineRule="auto"/>', run(text, italic=True, grey=True))


def bullet(text: str) -> str:
    ppr = ('<w:numPr><w:ilvl w:val="0"/><w:numId w:val="2"/></w:numPr>'
           '<w:spacing w:after="40" w:line="276" w:lineRule="auto"/>')
    return paragraph(ppr, rich(text))


def stack(text: str) -> str:
    label, _, rest = text.partition(":")
    ppr = '<w:spacing w:before="20" w:after="100" w:line="276" w:lineRule="auto"/>'
    return paragraph(ppr, run(label + ": ", bold=True, grey=True) + run(rest.strip(), grey=True))


def entry_header(text: str) -> str:
    """`A · B · C · Dates`: A bold, B bold when there are four parts or more, dates at the right edge."""
    parts = [part.strip() for part in text.split(" · ")]
    dates = parts.pop() if len(parts) > 1 else ""
    runs = ""
    for index, part in enumerate(parts):
        if index:
            runs += run("  ·  ")
        runs += run(part, bold=index == 0 or (index == 1 and len(parts) >= 3))
    if dates:
        runs += '<w:r><w:rPr><w:rStyle w:val="None"/></w:rPr><w:tab/></w:r>' + run(dates, date=True)
    ppr = (f'<w:keepNext/><w:tabs><w:tab w:val="right" w:pos="{TEXT_WIDTH}"/></w:tabs>'
           '<w:spacing w:before="140" w:after="20" w:line="276" w:lineRule="auto"/>')
    return paragraph(ppr, runs)


def skills_row(label: str, text: str) -> str:
    ppr = ('<w:tabs><w:tab w:val="left" w:pos="2000"/></w:tabs>'
           '<w:spacing w:after="60" w:line="276" w:lineRule="auto"/><w:ind w:left="2000" w:hanging="2000"/>')
    tab = '<w:r><w:rPr><w:rStyle w:val="None"/></w:rPr><w:tab/></w:r>'
    return paragraph(ppr, run(label, bold=True) + tab + run(text))


def blocks(markdown: str) -> list[str]:
    """Logical lines: wrapped continuation lines are joined to the line they continue."""
    result: list[str] = []
    open_block = False
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped:
            open_block = False
            continue
        starts_new = stripped.startswith(("#", "- ", "|", "Stack:")) or not open_block
        if starts_new:
            result.append(stripped)
            open_block = not stripped.startswith(("#", "|"))
        else:
            result[-1] += " " + stripped
    return result


def build(markdown: str, master_paragraphs: list[str]) -> str:
    name, title_template, contacts_one, contacts_two = master_paragraphs[:4]
    education = master_paragraphs[-2:]
    section_template = master_paragraphs[5]
    out = [name]
    section = ""
    after_header = False
    seen_summary = False
    for block in blocks(markdown):
        if block.startswith("# "):
            continue
        if block.startswith("## "):
            section = block[3:].strip()
            out.append(re.sub(r"<w:t>[^<]*</w:t>", f"<w:t>{escape(section)}</w:t>", section_template))
            after_header = False
            if section.startswith("EDUCATION"):
                out.extend(education)
            continue
        if section.startswith("EDUCATION"):
            continue
        if block.startswith("### "):
            out.append(entry_header(block[4:]))
            after_header = True
            continue
        if block.startswith("- "):
            out.append(bullet(block[2:]))
        elif block.startswith("Stack:"):
            out.append(stack(block))
        elif block.startswith("|"):
            cells = [cell.strip() for cell in block.strip("|").split("|")]
            if len(cells) == 2 and cells[0] and not set(cells[0]) <= set("-: "):
                out.append(skills_row(cells[0], cells[1]))
        elif not section and block.startswith("**") and block.endswith("**"):
            out.append(re.sub(r"<w:t>[^<]*</w:t>", f"<w:t>{escape(block.strip('*'))}</w:t>", title_template))
            portfolio = run("dmitrysachkov.com  ").replace("<w:rtl", '<w:sz w:val="18"/><w:szCs w:val="18"/><w:rtl')
            out.append(contacts_one)
            out.append(contacts_two.replace("</w:pPr>", "</w:pPr>" + portfolio, 1))
        elif not section and not seen_summary and block.startswith("+"):
            continue  # contacts come from the master
        elif not section:
            seen_summary = True
            out.append(body(block, after=120))
        elif after_header:
            out.append(subtitle(block))
        else:
            out.append(body(block))
        if not block.startswith("### "):
            after_header = False
    return "".join(out)


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    draft, output = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    if output == MASTER.resolve():
        sys.exit("Refusing to overwrite templates/cv_master.docx.")
    with zipfile.ZipFile(MASTER) as master:
        document = master.read("word/document.xml").decode("utf-8")
        head = document[: document.index("<w:body>") + len("<w:body>")]
        tail = document[document.index("<w:sectPr>"):]
        master_paragraphs = re.findall(r"<w:p[ >].*?</w:p>", document, flags=re.S)
        new_document = head + build(draft.read_text(encoding="utf-8"), master_paragraphs) + tail
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as result:
            for item in master.infolist():
                if item.is_dir():
                    continue
                data = new_document.encode("utf-8") if item.filename == "word/document.xml" else master.read(item)
                result.writestr(item.filename, data)
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()

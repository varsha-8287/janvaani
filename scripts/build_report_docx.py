import os
import re
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def generate_docx():
    md_path = os.path.join("docs", "Janvaani_Final_Implementation_Report.md")
    docx_path = os.path.join("docs", "Janvaani_Final_Implementation_Report.docx")

    print(f"Reading markdown from: {md_path}")
    doc = Document()

    # Configure 1-inch margins
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    # Configure default style
    style_normal = doc.styles["Normal"]
    font = style_normal.font
    font.name = "Calibri"
    font.size = Pt(11)
    font.color.rgb = RGBColor(0x22, 0x22, 0x22)

    with open(md_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    in_code_block = False
    code_lines = []
    in_table = False
    table_lines = []

    def set_cell_background(cell, fill_hex):
        shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
        cell._tc.get_or_add_tcPr().append(shading_elm)

    def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
        tcPr = cell._tc.get_or_add_tcPr()
        tcMar = OxmlElement("w:tcMar")
        for m, val in [("top", top), ("bottom", bottom), ("left", left), ("right", right)]:
            node = OxmlElement(f"w:{m}")
            node.set(qn("w:w"), str(val))
            node.set(qn("w:type"), "dxa")
            tcMar.append(node)
        tcPr.append(tcMar)

    def flush_table(lines_to_flush):
        if not lines_to_flush:
            return
        rows_data = []
        for l in lines_to_flush:
            stripped = l.strip()
            if stripped.startswith("|") and stripped.endswith("|"):
                cells = [c.strip() for c in stripped[1:-1].split("|")]
                if all(re.match(r"^:?-+:?$", c) for c in cells if c):
                    continue
                rows_data.append(cells)
        if not rows_data:
            return

        col_count = max(len(r) for r in rows_data)
        table = doc.add_table(rows=len(rows_data), cols=col_count)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = True

        for r_idx, row in enumerate(rows_data):
            is_header = (r_idx == 0)
            tr = table.rows[r_idx]._tr.get_or_add_trPr()
            trPr = parse_xml(f'<w:cantSplit {nsdecls("w")}/>')
            tr.append(trPr)
            if is_header:
                trHeader = parse_xml(f'<w:tblHeader {nsdecls("w")}/>')
                tr.append(trHeader)

            for c_idx in range(col_count):
                cell = table.cell(r_idx, c_idx)
                text = row[c_idx] if c_idx < len(row) else ""
                cell.text = ""
                p = cell.paragraphs[0]
                p.paragraph_format.space_before = Pt(3)
                p.paragraph_format.space_after = Pt(3)
                p.paragraph_format.line_spacing = 1.15
                run = p.add_run(text)
                if is_header:
                    run.bold = True
                    run.font.color.rgb = RGBColor(0x1B, 0x36, 0x5D)
                    set_cell_background(cell, "E8EEF5")
                else:
                    if r_idx % 2 == 1:
                        set_cell_background(cell, "FAFAFA")
                    else:
                        set_cell_background(cell, "FFFFFF")
                set_cell_margins(cell, 80, 80, 120, 120)

        p_after = doc.add_paragraph()
        p_after.paragraph_format.space_before = Pt(0)
        p_after.paragraph_format.space_after = Pt(6)

    def add_styled_paragraph(text, style_name="Normal", bullet=False, space_after=6):
        p = doc.add_paragraph(style="List Bullet" if bullet else style_name)
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.line_spacing = 1.15

        pattern = re.compile(r"(\*\*.*?\*\*|\*.*?\*|`.*?`)")
        tokens = pattern.split(text)
        for token in tokens:
            if not token:
                continue
            if token.startswith("**") and token.endswith("**"):
                run = p.add_run(token[2:-2])
                run.bold = True
            elif token.startswith("*") and token.endswith("*"):
                run = p.add_run(token[1:-1])
                run.italic = True
            elif token.startswith("`") and token.endswith("`"):
                run = p.add_run(token[1:-1])
                run.font.name = "Consolas"
                run.font.size = Pt(9.5)
                run.font.color.rgb = RGBColor(0x8A, 0x2B, 0x0E)
            else:
                p.add_run(token)

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code_block:
                in_code_block = False
                code_text = "".join(code_lines)
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(4)
                p.paragraph_format.space_after = Pt(6)
                run = p.add_run(code_text.rstrip())
                run.font.name = "Consolas"
                run.font.size = Pt(8.5)
                run.font.color.rgb = RGBColor(0x1E, 0x29, 0x3B)
                pPr = p._p.get_or_add_pPr()
                pBdr = parse_xml(f'<w:pBdr {nsdecls("w")}><w:left w:val="single" w:sz="24" w:space="12" w:color="1B365D"/></w:pBdr>')
                shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="F1F5F9"/>')
                pPr.append(pBdr)
                pPr.append(shd)
                code_lines = []
            else:
                if in_table:
                    flush_table(table_lines)
                    table_lines = []
                    in_table = False
                in_code_block = True
                code_lines = []
            i += 1
            continue

        if in_code_block:
            code_lines.append(line)
            i += 1
            continue

        if stripped.startswith("|") and stripped.endswith("|"):
            in_table = True
            table_lines.append(line)
            i += 1
            continue
        else:
            if in_table:
                flush_table(table_lines)
                table_lines = []
                in_table = False

        if not stripped:
            i += 1
            continue

        if stripped.startswith("# "):
            h = doc.add_heading(stripped[2:], level=1)
            h.paragraph_format.space_before = Pt(18)
            h.paragraph_format.space_after = Pt(8)
        elif stripped.startswith("## "):
            h = doc.add_heading(stripped[3:], level=2)
            h.paragraph_format.space_before = Pt(14)
            h.paragraph_format.space_after = Pt(6)
        elif stripped.startswith("### "):
            h = doc.add_heading(stripped[4:], level=3)
            h.paragraph_format.space_before = Pt(10)
            h.paragraph_format.space_after = Pt(4)
        elif stripped.startswith("#### "):
            h = doc.add_heading(stripped[5:], level=4)
            h.paragraph_format.space_before = Pt(8)
            h.paragraph_format.space_after = Pt(3)
        elif stripped.startswith("- ") or stripped.startswith("* "):
            add_styled_paragraph(stripped[2:], bullet=True)
        elif re.match(r"^\d+\.\s", stripped):
            m = re.match(r"^\d+\.\s(.*)", stripped)
            add_styled_paragraph(m.group(1), bullet=True)
        elif stripped == "---":
            p = doc.add_paragraph()
            pPr = p._p.get_or_add_pPr()
            pBdr = parse_xml(f'<w:pBdr {nsdecls("w")}><w:bottom w:val="single" w:sz="6" w:space="6" w:color="CCCCCC"/></w:pBdr>')
            pPr.append(pBdr)
            p.paragraph_format.space_after = Pt(6)
        else:
            add_styled_paragraph(stripped)

        i += 1

    if in_table:
        flush_table(table_lines)

    doc.save(docx_path)
    print(f"DOCX successfully saved at: {docx_path} ({os.path.getsize(docx_path)} bytes)")

if __name__ == "__main__":
    generate_docx()

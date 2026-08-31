from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    LongTable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "submissions" / "initial_round" / "project_creative_book_1000.md"
OUT = ROOT / "submissions" / "initial_round" / "01-作品说明文档-待填写队伍名称.pdf"
FONT_PATH = Path(r"C:\Windows\Fonts\STSONG.TTF")
FONT_NAME = "STSongLocal"
PLACEHOLDER = "（待按官网报名信息填写）"
WORK_NAME = "考研各专业知识库问答智能体"
DIRECTION = "千问3.5模型优化创新"


def parse_markdown() -> tuple[str, list[tuple[str, list[str]]], list[list[str]]]:
    raw = SOURCE.read_text(encoding="utf-8")
    project_line = next(line for line in raw.splitlines() if line.startswith("项目名称："))
    sections: list[tuple[str, list[str]]] = []
    current_title = ""
    current_paragraphs: list[str] = []
    table_rows: list[list[str]] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            if current_title:
                sections.append((current_title, current_paragraphs))
            current_title = stripped[3:]
            current_paragraphs = []
        elif stripped.startswith("|"):
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if cells and not all(set(cell) <= {"-", ":"} for cell in cells):
                table_rows.append(cells)
        elif stripped and not stripped.startswith("#") and not stripped.startswith("项目名称："):
            current_paragraphs.append(stripped)
    if current_title:
        sections.append((current_title, current_paragraphs))
    return project_line, sections, table_rows


def page_number(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont(FONT_NAME, 9)
    page = canvas.getPageNumber()
    if page % 2 == 0:
        canvas.drawString(3 * cm, 1.5 * cm, str(page))
    else:
        canvas.drawRightString(A4[0] - 3 * cm, 1.5 * cm, str(page))
    canvas.restoreState()


def p(text: str, style) -> Paragraph:
    return Paragraph(text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), style)


def table_style(header=True, font_size=8.5) -> TableStyle:
    commands = [
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        commands.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E7E6E6")),
                ("FONTNAME", (0, 0), (-1, 0), FONT_NAME),
            ]
        )
    return TableStyle(commands)


def main() -> None:
    pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH)))
    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "BodyCn",
        parent=styles["BodyText"],
        fontName=FONT_NAME,
        fontSize=10.5,
        leading=10.5,
        alignment=TA_JUSTIFY,
        firstLineIndent=21,
        spaceAfter=5,
        wordWrap="CJK",
    )
    body_no_indent = ParagraphStyle("BodyNoIndent", parent=body, firstLineIndent=0, alignment=TA_LEFT)
    note = ParagraphStyle("Note", parent=body, fontSize=9, leading=10, firstLineIndent=0)
    title2 = ParagraphStyle(
        "Title2",
        fontName=FONT_NAME,
        fontSize=22,
        leading=28,
        alignment=TA_CENTER,
        spaceAfter=14,
    )
    title3 = ParagraphStyle(
        "Title3",
        fontName=FONT_NAME,
        fontSize=16,
        leading=20,
        alignment=TA_CENTER,
        spaceAfter=8,
    )
    h1 = ParagraphStyle(
        "H1Cn",
        fontName=FONT_NAME,
        fontSize=16,
        leading=19,
        alignment=TA_LEFT,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True,
    )
    cover_field = ParagraphStyle(
        "CoverField",
        fontName=FONT_NAME,
        fontSize=15,
        leading=22,
        leftIndent=2.2 * cm,
        spaceAfter=10,
    )
    cell = ParagraphStyle("Cell", fontName=FONT_NAME, fontSize=8.2, leading=9.2, wordWrap="CJK")
    cell_center = ParagraphStyle("CellCenter", parent=cell, alignment=TA_CENTER)

    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=A4,
        leftMargin=3 * cm,
        rightMargin=3 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
        title=WORK_NAME,
        author="参赛团队",
    )
    story = []

    story.extend(
        [
            Spacer(1, 0.5 * cm),
            p("2026中国高校计算机大赛-人工智能创意赛", title3),
            Spacer(1, 0.8 * cm),
            p("昇腾赛道项目创意书（初赛）", title2),
            Spacer(1, 1.0 * cm),
        ]
    )
    for label, value in [
        ("参赛学校", PLACEHOLDER),
        ("团队名称", PLACEHOLDER),
        ("作品名称", WORK_NAME),
        ("赛题方向", DIRECTION),
        ("联系人（队长）", PLACEHOLDER),
        ("联系电话（队长）", PLACEHOLDER),
    ]:
        story.append(p(f"{label}：{value}", cover_field))
    story.extend(
        [
            Spacer(1, 2.4 * cm),
            p("中国高校计算机大赛-人工智能创意赛（昇腾赛道）组委会编制    2026.05", note),
            PageBreak(),
        ]
    )

    story.extend(
        [
            p("2026中国高校计算机大赛-人工智能创意赛", title3),
            p("参赛团队信息表", title2),
            p("注：报名信息须与官网保持一致。以下占位符必须在提交前全部替换。", note),
        ]
    )
    overview_data = [
        [p("作品名称", cell_center), p(WORK_NAME, cell)],
        [p("团队名称", cell_center), p(PLACEHOLDER, cell)],
        [p("参赛学校", cell_center), p(PLACEHOLDER, cell)],
    ]
    overview = Table(overview_data, colWidths=[3.2 * cm, 11.8 * cm], repeatRows=1)
    overview.setStyle(table_style(header=False, font_size=9.5))
    overview.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E7E6E6"))]))
    story.extend([overview, Spacer(1, 0.25 * cm), p("团队队员基本信息（最多3人）", h1)])

    member_headers = ["姓名", "学校全称", "院（系）", "专业全称", "年级", "毕业时间", "联系电话", "邮箱", "团队分工"]
    member_data = [[p(item, cell_center) for item in member_headers]]
    member_data.extend([[p("待填", cell_center) for _ in member_headers] for _ in range(3)])
    members = LongTable(
        member_data,
        colWidths=[value * cm for value in [1.25, 1.75, 1.75, 1.75, 1.05, 1.3, 1.55, 1.65, 1.35]],
        repeatRows=1,
    )
    members.setStyle(table_style())
    story.extend([members, Spacer(1, 0.18 * cm), p("团队指导教师信息（指导老师须与队长同校）", h1)])

    teacher_headers = ["姓名", "院（系）全称", "职称", "研究方向", "联系电话", "联系邮箱"]
    teacher_data = [[p(item, cell_center) for item in teacher_headers], [p("待填", cell_center) for _ in teacher_headers]]
    teacher = Table(teacher_data, colWidths=[1.5 * cm, 2.5 * cm, 1.5 * cm, 3.4 * cm, 2.4 * cm, 3.7 * cm], repeatRows=1)
    teacher.setStyle(table_style())
    story.extend(
        [
            teacher,
            Spacer(1, 0.18 * cm),
            p("团队成员优势描述", h1),
            p(
                f"{PLACEHOLDER}。建议只填写团队真实成果、项目经历、专业能力和成员分工，突出技术实现、数据整理、材料撰写及汇报答辩等能力的互补性。",
                body,
            ),
            PageBreak(),
        ]
    )

    story.extend([p(f"《{WORK_NAME}》作品原创性声明", title3), Spacer(1, 0.3 * cm)])
    story.append(
        p(
            "郑重声明：承诺本参赛队伍报名信息真实有效；呈交的参赛作品相关资料以及所完成的作品实物等相关成果，是本团队独立进行研究工作所取得的成果，除文中已经注明引用的内容外，本作品说明文档不包含任何其他个人或集体已经发表或撰写过的作品成果，不侵犯任何第三方的知识产权或其他权利。本声明的法律结果由本参赛队承担。",
            body,
        )
    )
    for line in [
        "参赛队员签名（团队全部成员）：________________________________________",
        "日期：________年______月______日",
        "指导老师审核签名：_______________________________________________",
        "日期：________年______月______日",
    ]:
        story.extend([Spacer(1, 0.35 * cm), p(line, body_no_indent)])
    story.extend(
        [
            Spacer(1, 0.8 * cm),
            p("注：本页可打印后签名并扫描，或使用电子签名。须保证内容完整、字迹清晰，并与项目创意书作为同一文档提交。", note),
            PageBreak(),
        ]
    )

    project_line, sections, table_rows = parse_markdown()
    story.extend(
        [
            p(WORK_NAME, title2),
            p("项目创意书正文（初赛）", title3),
            p(f"团队名称：{PLACEHOLDER}", title3),
            p(project_line, body_no_indent),
        ]
    )
    for section_title, paragraphs in sections:
        story.append(p(section_title, h1))
        for text in paragraphs:
            story.append(p(text, body))
        if section_title == "功能与进展" and table_rows:
            data = [[p(value, cell if index == 1 else cell_center) for index, value in enumerate(row)] for row in table_rows]
            table = LongTable(data, colWidths=[3.0 * cm, 8.7 * cm, 3.3 * cm], repeatRows=1)
            table.setStyle(table_style())
            story.append(table)
    story.append(p("最小可运行Demo说明（选交）", h1))
    for text in [
        "随文提交源码压缩包 kaoyan-knowledge-agent-initial-round.zip。压缩包内不包含任何嵌套ZIP、Qwen3.5权重、COCO数据集或虚构的NPU实测结果。",
        "Windows环境在项目根目录运行 .\\run.ps1；Linux环境运行 ./run.sh；浏览器访问 http://127.0.0.1:7860。网页支持知识问答、真题解析、院校咨询和复习规划四种模式。",
        "HTTP Skill接口为 POST /api/skill/invoke，响应包含引用来源、风险提示、模型提供方和耗时。默认显示local-template；配置真实模型服务后才会标记为外部模型连接。",
        "本地规则回归日志只用于检验固定样例上的工程行为，不作为Qwen3.5模型精度或昇腾NPU性能结论。复赛阶段将按官方流程补充真实训练、推理、精度和性能证据。",
    ]:
        story.append(p(text, body))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.build(story, onFirstPage=page_number, onLaterPages=page_number)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()

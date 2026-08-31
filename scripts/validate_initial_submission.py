from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
SUBMISSION = ROOT / "submissions" / "initial_round"
ZIP_PATH = ROOT / "dist" / "kaoyan-knowledge-agent-initial-round.zip"
CREATIVE_MD = SUBMISSION / "project_creative_book_1000.md"
DOCX_PATH = SUBMISSION / "01-作品说明文档-待填写队伍名称.docx"
PDF_PATH = SUBMISSION / "01-作品说明文档-待填写队伍名称.pdf"
REPORT_PATH = ROOT / "reports" / "initial_submission_validation.md"
ARCHIVE_SUFFIXES = {".zip", ".rar", ".7z"}


def creative_character_count() -> int:
    text = CREATIVE_MD.read_text(encoding="utf-8")
    text = re.sub(r"(?m)^#.*$", "", text)
    text = re.sub(r"(?m)^\|.*$", "", text)
    return len(re.sub(r"\s", "", text))


def zip_checks(require_zip: bool) -> tuple[list[str], list[str], list[str]]:
    if not ZIP_PATH.exists():
        if require_zip:
            return [], ["源码压缩包不存在"], []
        return [], [], ["当前是解压目录，跳过外层源码ZIP存在性检查"]
    with zipfile.ZipFile(ZIP_PATH) as zf:
        names = zf.namelist()
    nested = [name for name in names if Path(name).suffix.lower() in ARCHIVE_SUFFIXES]
    required_prefixes = ["src/", "static/", "data/", "scripts/", "ascend/", "docs/", "reports/"]
    missing = [prefix for prefix in required_prefixes if not any(name.startswith(prefix) for name in names)]
    return nested, [f"压缩包缺少目录：{prefix}" for prefix in missing], []


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate initial-round submission artifacts.")
    parser.add_argument("--require-zip", action="store_true", help="Fail if the outer source ZIP is missing.")
    args = parser.parse_args()
    failures: list[str] = []
    warnings: list[str] = []
    count = creative_character_count()
    if not 900 <= count <= 1100:
        failures.append(f"创意书正文非空白字符数为 {count}，不在 900-1100 建议范围")

    for path in (DOCX_PATH, PDF_PATH):
        if not path.exists() or path.stat().st_size == 0:
            failures.append(f"缺少正式文件：{path.name}")

    page_count = 0
    if PDF_PATH.exists():
        page_count = len(PdfReader(PDF_PATH).pages)
        if page_count > 10:
            failures.append(f"正式 PDF 共 {page_count} 页，超过模板要求的10页")

    nested, zip_failures, zip_warnings = zip_checks(args.require_zip)
    failures.extend(zip_failures)
    warnings.extend(zip_warnings)
    if nested:
        failures.append(f"源码包包含嵌套归档：{nested}")

    if "待填写" in DOCX_PATH.name or "待填写" in PDF_PATH.name:
        warnings.append("文件名和文档内仍有报名信息占位符，提交前必须替换并完成签名")

    lines = [
        "# 初赛提交自检报告",
        "",
        "| 检查项 | 结果 |",
        "| --- | --- |",
        f"| 创意书正文字符数 | {count}（建议900-1100） |",
        f"| 正式 DOCX | {'存在' if DOCX_PATH.exists() else '缺失'} |",
        f"| 正式 PDF | {'存在' if PDF_PATH.exists() else '缺失'}，{page_count}页 |",
        f"| 源码 ZIP | {'存在' if ZIP_PATH.exists() else '缺失'} |",
        f"| 嵌套归档 | {'无' if not nested else '有'} |",
        f"| 自动检查结论 | {'通过' if not failures else '未通过'} |",
        "",
        "## 失败项",
        "",
        *(f"- {item}" for item in failures),
        *( ["- 无"] if not failures else [] ),
        "",
        "## 提交前人工项",
        "",
        *(f"- {item}" for item in warnings),
        "- 核对官网报名信息与团队信息表完全一致。",
        "- 完成全体队员及指导教师签名。",
        "- 将PDF重命名为 `01-作品说明文档+参赛队伍名称.pdf`。",
        "- 本地规则回归结果不得表述为Qwen3.5模型精度。",
        "- 真实昇腾NPU性能、模型精度和COCO/官方验证仍待上机完成。",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"passed": not failures, "failures": failures, "warnings": warnings}, ensure_ascii=False))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

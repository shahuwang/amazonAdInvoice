#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
解析亚马逊广告发票PDF，提取关键字段并输出CSV，同时重命名PDF文件。

用法:
    python3 parse_amazon_invoices.py -folder /path/to/invoices

输出:
    在当前目录生成 invoices_summary.csv
    重命名后的PDF保留在原文件夹内，格式: 发票日期-发票金额-发票id.pdf
"""

import os
import re
import sys
import argparse
from datetime import datetime
from pathlib import Path

import pdfplumber
import pandas as pd

# ---------------------------------------------------------------------------
# 配置：多种正则尝试，提升不同模板的兼容性
# ---------------------------------------------------------------------------

AMOUNT_PATTERNS = [
    re.compile(
        r"(?:Invoice Amount Due)\s*[:：]?\s*[\$¥€£]?\s*([0-9,]+\.\d{2})",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:Amount Due|Invoice Total|Total Amount|Total)\s*[:：]?\s*[\$¥€£]?\s*([0-9,]+\.\d{2})",
        re.IGNORECASE,
    ),
    re.compile(r"\$\s*([0-9,]+\.\d{2})\s*(?:USD|EUR|GBP|CNY)?", re.IGNORECASE),
]

INVOICE_ID_PATTERNS = [
    re.compile(
        r"(?:Invoice\s*Number)\s*[:：]?\s*([A-Za-z0-9\-]+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:Invoice\s*(?:#|No\.?)|发票号码|发票编号|Invoice ID)\s*[:：]?\s*([A-Za-z0-9\-]+)",
        re.IGNORECASE,
    ),
]

INVOICE_DATE_PATTERNS = [
    re.compile(
        r"(?:Invoice Date)\s*[:：]?\s*(\d{4}[/-]\d{1,2}[/-]\d{1,2})",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:Invoice Date)\s*[:：]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:Invoice Date)\s*[:：]?\s*(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:Invoice Date)\s*[:：]?\s*([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:Invoice Date)\s*[:：]?\s*(\d{1,2}-[A-Za-z]{3,9}-\d{4})",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:Invoice\s*Date|发票日期|Date\s*of\s*Invoice)\s*[:：]\s*(\d{4}[/-]\d{1,2}[/-]\d{1,2})",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:Invoice\s*Date|发票日期|Date\s*of\s*Invoice)\s*[:：]\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:Invoice\s*Date|发票日期|Date\s*of\s*Invoice)\s*[:：]\s*(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:Invoice\s*Date|发票日期|Date\s*of\s*Invoice)\s*[:：]\s*([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:Invoice\s*Date|发票日期|Date\s*of\s*Invoice)\s*[:：]\s*(\d{1,2}-[A-Za-z]{3,9}-\d{4})",
        re.IGNORECASE,
    ),
]

PERIOD_PATTERNS = [
    re.compile(
        r"(?:Invoice Period)\s*[:：]?\s*(.+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:Billing\s*Period|Service\s*Period|Period|账单周期|账期)\s*[:：]?\s*(.+)",
        re.IGNORECASE,
    ),
]

DATE_SEPARATORS = re.compile(r"\s*[-–—~～]\s*")

# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def normalize_date(date_str):
    """把多种日期字符串统一转为 yyyy-mm-dd，失败返回原字符串。"""
    date_str = date_str.strip()
    for fmt in (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%m/%d/%Y",
        "%m-%d-%Y",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d %b %Y",
        "%d %B %Y",
        "%d-%b-%Y",
        "%d-%B-%Y",
        "%b %d %Y",
        "%B %d %Y",
        "%b %d, %Y",
        "%B %d, %Y",
    ):
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return date_str


def extract_all_text(pdf_path):
    """提取PDF所有页面的纯文本。"""
    parts = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                txt = page.extract_text()
                if txt:
                    parts.append(txt)
    except Exception as exc:
        print(f"[WARN] 读取PDF失败: {pdf_path} -> {exc}")
        return ""
    return "\n".join(parts)


def try_match(patterns, text, group=1):
    for pat in patterns:
        m = pat.search(text)
        if m:
            return m.group(group).strip()
    return None


def parse_period(period_line):
    """
    从类似 '2024/01/01 - 2024/01/31' 或 'Jan 1, 2024 - Jan 31, 2024'
    提取开始日期和结束日期。
    """
    if not period_line:
        return None, None

    # 先尝试常见的 "日期 - 日期" 拆分
    parts = DATE_SEPARATORS.split(period_line)
    if len(parts) == 2:
        start = normalize_date(parts[0])
        end = normalize_date(parts[1])
        return start, end

    # 再尝试匹配两个独立日期
    date_candidates = re.findall(
        r"\d{4}[/-]\d{1,2}[/-]\d{1,2}|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}|\d{1,2}-[A-Za-z]{3,9}-\d{4}|[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}",
        period_line,
    )
    if len(date_candidates) >= 2:
        return normalize_date(date_candidates[0]), normalize_date(date_candidates[-1])

    return None, None


def parse_invoice(pdf_path):
    text = extract_all_text(pdf_path)
    if not text:
        return None, "无法提取文本"

    # ---- 匹配字段 ----
    invoice_id = try_match(INVOICE_ID_PATTERNS, text)
    amount = try_match(AMOUNT_PATTERNS, text)
    invoice_date = try_match(INVOICE_DATE_PATTERNS, text)
    period_line = try_match(PERIOD_PATTERNS, text)

    period_start, period_end = (
        parse_period(period_line) if period_line else (None, None)
    )

    # ---- 清理金额 ----
    if amount:
        amount = amount.replace(",", "")

    # ---- 清理日期 ----
    if invoice_date:
        invoice_date = normalize_date(invoice_date)

    # ---- 构建结果 ----
    result = {
        "file_name": os.path.basename(pdf_path),
        "invoice_id": invoice_id,
        "amount": amount,
        "invoice_date": invoice_date,
        "period_start": period_start,
        "period_end": period_end,
        "period_raw": period_line,
    }

    missing = [
        k
        for k in ("invoice_id", "amount", "invoice_date", "period_start", "period_end")
        if not result[k]
    ]
    if missing:
        return result, f"字段缺失: {', '.join(missing)}"
    return result, None


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="解析亚马逊广告发票PDF并输出Excel")
    parser.add_argument(
        "-folder", "--folder", required=True, help="包含PDF发票的文件夹路径"
    )
    parser.add_argument(
        "-o",
        "--output",
        default="invoices_summary.xlsx",
        help="输出Excel文件名（默认: invoices_summary.xlsx）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅打印将要执行的重命名操作，不实际修改文件",
    )
    args = parser.parse_args()

    folder = Path(args.folder).expanduser().resolve()
    if not folder.is_dir():
        print(f"[ERROR] 指定的路径不是文件夹: {folder}")
        sys.exit(1)

    pdf_files = sorted(folder.glob("*.pdf"))
    if not pdf_files:
        print(f"[WARN] 文件夹内未找到任何PDF文件: {folder}")
        sys.exit(0)

    rows = []
    errors = []

    for pdf_path in pdf_files:
        print(f"[INFO] 正在解析: {pdf_path.name} ...")
        result, err = parse_invoice(pdf_path)

        if result is None:
            errors.append({"file": pdf_path.name, "error": err})
            continue

        if err:
            print(f"[WARN] {pdf_path.name} -> {err}")
            errors.append({"file": pdf_path.name, "error": err})
            # 仍然将部分解析结果写入CSV，方便手动补全

        rows.append(
            {
                "发票id": result["invoice_id"] or "",
                "发票金额": result["amount"] or "",
                "发票开出时间": result["invoice_date"] or "",
                "发票对应支出开始时间": result["period_start"] or "",
                "发票对应支出结束时间": result["period_end"] or "",
            }
        )

        # ---- 重命名PDF ----
        date_for_rename = (
            result["invoice_date"].replace("-", "") if result["invoice_date"] else None
        )
        new_name = None
        if date_for_rename and result["amount"] and result["invoice_id"]:
            new_name = (
                f"{date_for_rename}-{result['amount']}-{result['invoice_id']}.pdf"
            )
        elif date_for_rename and result["amount"]:
            new_name = f"{date_for_rename}-{result['amount']}.pdf"
        elif date_for_rename and result["invoice_id"]:
            new_name = f"{date_for_rename}-{result['invoice_id']}.pdf"

        if new_name:
            new_path = pdf_path.with_name(new_name)
            if new_path.resolve() == pdf_path.resolve():
                print(f"[INFO] 无需重命名（名称已是目标格式）: {pdf_path.name}")
            elif new_path.exists():
                print(f"[WARN] 目标文件名已存在，跳过重命名: {new_name}")
            else:
                if args.dry_run:
                    print(f"[DRY-RUN] 将重命名: {pdf_path.name} -> {new_name}")
                else:
                    pdf_path.rename(new_path)
                    print(f"[INFO] 已重命名: {pdf_path.name} -> {new_name}")
        else:
            print(f"[WARN] 信息不足以重命名: {pdf_path.name}")

    # ---- 按发票开出时间从早到晚排序 ----
    rows.sort(key=lambda x: x["发票开出时间"])

    # ---- 写入Excel ----
    output_excel = Path(args.output).expanduser().resolve()
    df = pd.DataFrame(
        rows,
        columns=[
            "发票id",
            "发票金额",
            "发票开出时间",
            "发票对应支出开始时间",
            "发票对应支出结束时间",
        ],
    )
    # 将金额转为数值类型
    df["发票金额"] = pd.to_numeric(df["发票金额"], errors="coerce")

    with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")
        worksheet = writer.sheets["Sheet1"]
        col_idx = df.columns.get_loc("发票金额") + 1
        for row in range(2, len(df) + 2):
            worksheet.cell(row=row, column=col_idx).number_format = "0.00"

    print(f"\n[INFO] Excel已输出: {output_excel}")
    print(
        f"[INFO] 共处理 {len(pdf_files)} 个PDF，成功提取完整信息 {len(rows) - len(errors)} 个，有问题 {len(errors)} 个。"
    )

    if errors:
        print(
            "\n[ERROR] 以下文件解析异常（可能是模板不匹配），请检查正则规则或字段名称:"
        )
        for e in errors:
            print(f"    - {e['file']}: {e['error']}")


if __name__ == "__main__":
    main()

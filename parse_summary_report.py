#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
解析亚马逊月度汇总报告PDF（批量），每个PDF为一行，按账期月份排序输出Excel。

用法:
    python3 parse_summary_report.py -folder=/path/to/pdfs
    python3 parse_summary_report.py -folder=/path/to/pdfs -o result.xlsx
"""

import re
import sys
import argparse
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from datetime import datetime

import pdfplumber
import pandas as pd


def extract_text(pdf_path: str) -> str:
    parts = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                txt = page.extract_text()
                if txt:
                    parts.append(txt)
    except Exception as exc:
        raise RuntimeError(f"读取PDF失败: {pdf_path} -> {exc}") from exc
    return "\n".join(parts)


def parse_amount(s: str) -> Decimal:
    return Decimal(s.replace(",", ""))


def format_amount(d: Decimal) -> str:
    return str(d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def parse_pdf(pdf_path: str) -> dict:
    text = extract_text(pdf_path)

    # 账期月份
    activity_match = re.search(
        r"Account activity from\s+([A-Za-z]+ \d{1,2},? \d{4}) \d{2}:\d{2} \w+ through",
        text,
    )
    statement_month = None
    if activity_match:
        raw_date = activity_match.group(1).strip()
        for fmt in ("%b %d, %Y", "%B %d, %Y", "%b %d %Y", "%B %d %Y"):
            try:
                parsed = datetime.strptime(raw_date, fmt)
                statement_month = parsed.strftime("%Y-%m")
                break
            except ValueError:
                continue

    # 币种
    currency_match = re.search(r"All amounts in (\w+)", text)
    currency = currency_match.group(1) if currency_match else None

    # Totals
    totals_pattern = re.compile(
        r"^(Income|Expenses|Tax|Transfers)\b\s+.+?\s+(-?\d{1,3}(?:,\d{3})*\.\d{2}|-?\d+)\s*$",
        re.MULTILINE | re.IGNORECASE,
    )
    totals = {}
    for m in totals_pattern.finditer(text):
        key = m.group(1).strip().capitalize()
        raw_val = m.group(2).strip()
        try:
            val = parse_amount(raw_val)
        except InvalidOperation:
            continue
        if key not in totals:
            totals[key] = val

    required_keys = {"Income", "Expenses", "Tax", "Transfers"}
    missing = required_keys - set(totals.keys())
    if missing:
        raise ValueError(f"缺少必填项: {', '.join(sorted(missing))}")

    # 广告支出
    adv_match = re.search(
        r"Cost of Advertising\s+(-?\d[\d,]*\.\d{2}|-?\d+)", text, re.IGNORECASE
    )
    advertising = parse_amount(adv_match.group(1)) if adv_match else Decimal("0")

    # 运费支出
    shipping_items = [
        "FBA transaction fees",
        "FBA transaction fee refunds",
        "Other transaction fees",
        "Other transaction fee refunds",
        "FBA inventory and inbound services fees",
    ]
    shipping = Decimal("0")
    for item in shipping_items:
        pattern = rf"{re.escape(item)}\s+(-?\d[\d,]*\.\d{{2}}|-?\d+)"
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            shipping += parse_amount(m.group(1))

    # 平台费用项目
    expenses_total = totals["Expenses"]
    platform_fees = expenses_total - advertising - shipping

    # 验证
    expected_expenses = advertising + shipping + platform_fees
    diff = (expenses_total - expected_expenses).quantize(
        Decimal("0.001"), rounding=ROUND_HALF_UP
    )
    if diff != Decimal("0.000"):
        raise ValueError(
            f"验证失败: Expenses({format_amount(expenses_total)}) 不等于 细分之和({format_amount(expected_expenses)}), 差额 {format_amount(diff)}"
        )

    result = {
        "账期月份": statement_month or "",
        "币种": currency or "",
        "营业收入": format_amount(totals["Income"]),
        "税费": format_amount(totals["Tax"]),
        "提现金额": format_amount(-totals["Transfers"]),
        "平台扣减总费用": format_amount(totals["Expenses"]),
        "广告支出": format_amount(advertising),
        "运费支出": format_amount(shipping),
        "平台费用项目": format_amount(platform_fees),
    }

    # 其他新增大项
    for k, v in totals.items():
        if k not in required_keys:
            result[k] = format_amount(v)

    return result


def main():
    parser = argparse.ArgumentParser(description="批量解析亚马逊月度汇总报告PDF")
    parser.add_argument(
        "-folder", "--folder", required=True, help="包含PDF的文件夹路径"
    )
    parser.add_argument(
        "-o", "--output", default="summary_report.xlsx", help="输出Excel文件名"
    )
    args = parser.parse_args()

    folder = Path(args.folder).expanduser().resolve()
    if not folder.is_dir():
        print(f"[ERROR] 指定的路径不是文件夹: {folder}")
        sys.exit(1)

    pdf_files = sorted(folder.glob("*.pdf"))
    if not pdf_files:
        print(f"[WARN] 文件夹内未找到PDF文件: {folder}")
        sys.exit(0)

    rows = []
    errors = []
    extra_keys = set()

    for pdf_path in pdf_files:
        print(f"[INFO] 正在解析: {pdf_path.name} ...")
        try:
            result = parse_pdf(str(pdf_path))
            rows.append(result)
            extra_keys.update(
                set(result.keys())
                - {
                    "账期月份",
                    "币种",
                    "营业收入",
                    "平台扣减总费用",
                    "税费",
                    "提现金额",
                    "广告支出",
                    "运费支出",
                    "平台费用项目",
                }
            )
        except Exception as exc:
            print(f"[ERROR] {pdf_path.name} -> {exc}")
            errors.append({"file": pdf_path.name, "error": str(exc)})

    if errors:
        print("\n[ERROR] 以下文件解析失败:")
        for e in errors:
            print(f"    - {e['file']}: {e['error']}")
        sys.exit(1)

    # 组装DataFrame
    base_columns = [
        "账期月份",
        "币种",
        "营业收入",
        "税费",
        "提现金额",
        "平台扣减总费用",
    ]
    extra_columns = sorted(extra_keys)
    detail_columns = ["广告支出", "运费支出", "平台费用项目"]
    all_columns = base_columns + extra_columns + detail_columns

    # 确保每行都有所有列
    for row in rows:
        for col in all_columns:
            if col not in row:
                row[col] = "0.00"

    # 按账期月份排序
    rows.sort(key=lambda x: x["账期月份"])

    df = pd.DataFrame(rows, columns=all_columns)

    # 金额列转为数字格式
    numeric_cols = [c for c in df.columns if c not in ("账期月份", "币种")]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    output_path = Path(args.output).expanduser().resolve()
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="汇总")
        worksheet = writer.sheets["汇总"]
        for col_idx, col_name in enumerate(df.columns, start=1):
            if col_name in numeric_cols:
                for row_idx in range(2, len(df) + 2):
                    cell = worksheet.cell(row=row_idx, column=col_idx)
                    if (
                        isinstance(cell.value, (int, float))
                        or str(cell.value)
                        .replace(".", "", 1)
                        .replace("-", "", 1)
                        .isdigit()
                    ):
                        cell.number_format = "0.00"

    print(f"\n[INFO] Excel已输出: {output_path}")


if __name__ == "__main__":
    main()

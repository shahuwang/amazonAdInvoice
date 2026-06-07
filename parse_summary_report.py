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
        r"(?:Account activity from|Actividad de la cuenta desde)\s+([A-Za-z]+ \d{1,2},? \d{4}) \d{2}:\d{2} \w+ (?:through|hasta)",
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
    currency_match = re.search(r"(?:All amounts in|Todos los importes en)\s*(\w+)", text)
    currency = currency_match.group(1) if currency_match else None

    KEY_MAP = {
        "Income": "Income", "Ingresos": "Income",
        "Expenses": "Expenses", "Gastos": "Expenses",
        "Tax": "Tax", "Impuesto": "Tax",
        "Transfers": "Transfers", "Transferencias": "Transfers",
    }
    totals_pattern = re.compile(
        r"^(Income|Ingresos|Expenses|Gastos|Tax|Impuesto|Transfers|Transferencias)\b\s+.+?\s+(-?\d{1,3}(?:,\d{3})*\.\d{2}|-?\d+)\s*$",
        re.MULTILINE | re.IGNORECASE,
    )
    totals = {}
    for m in totals_pattern.finditer(text):
        raw_key = m.group(1).strip().capitalize()
        key = KEY_MAP.get(raw_key, raw_key)
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
        r"(?:Cost of Advertising|Costo de la publicidad)\s+(-?\d[\d,]*\.\d{2}|-?\d+)", text, re.IGNORECASE
    )
    advertising = parse_amount(adv_match.group(1)) if adv_match else Decimal("0")

    # 运费支出
    shipping_patterns = [
        r"(?:FBA transaction fees|Tarifas de transacción FBA)",
        r"(?:FBA transaction fee refunds|Reembolsos de tarifas de transacción FBA)",
        r"(?:Other transaction fees|Tarifas de otra transacción)",
        r"(?:Other transaction fee refunds|Reembolsos de tarifas de otras transacciones)",
    ]
    shipping = Decimal("0")
    for pattern in shipping_patterns:
        m = re.search(rf"{pattern}\s+(-?\d[\d,]*\.\d{{2}}|-?\d+)", text, re.IGNORECASE)
        if m:
            shipping += parse_amount(m.group(1))

    # 仓储费用
    storage = Decimal("0")
    m = re.search(
        r"(?:FBA inventory and inbound services fees|Tarifas de inventario y de servicios de Logística de Amazon)\s+(-?\d[\d,]*\.\d{2}|-?\d+)",
        text, re.IGNORECASE,
    )
    if m:
        storage += parse_amount(m.group(1))

    # 平台其他扣费
    expenses_total = totals["Expenses"]
    platform_fees = expenses_total - advertising - shipping - storage

    # 验证
    expected_expenses = advertising + shipping + storage + platform_fees
    diff = (expenses_total - expected_expenses).quantize(
        Decimal("0.001"), rounding=ROUND_HALF_UP
    )
    if diff != Decimal("0.000"):
        raise ValueError(
            f"验证失败: Expenses({format_amount(expenses_total)}) 不等于 细分之和({format_amount(expected_expenses)}), 差额 {format_amount(diff)}"
        )

    net_revenue = totals["Income"] + totals["Expenses"]
    result = {
        "账期月份": statement_month or "",
        "币种": currency or "",
        "提现金额": format_amount(-totals["Transfers"]),
        "税费": format_amount(totals["Tax"]),
        "营业收入": format_amount(totals["Income"]),
        "净营收总额": format_amount(net_revenue),
        "平台扣减总费用": format_amount(totals["Expenses"]),
        "广告支出": format_amount(advertising),
        "运费支出": format_amount(shipping),
        "仓储费用": format_amount(storage),
        "平台其他扣费": format_amount(platform_fees),
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
        "-o", "--output", default=None, help="输出Excel文件名或路径，默认保存到PDF目录"
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
                    "净营收总额",
                    "平台扣减总费用",
                    "税费",
                    "提现金额",
                    "广告支出",
                    "运费支出",
                    "仓储费用",
                    "平台其他扣费",
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
        "提现金额",
        "税费",
        "营业收入",
        "净营收总额",
        "平台扣减总费用",
    ]
    extra_columns = sorted(extra_keys)
    detail_columns = ["广告支出", "运费支出", "仓储费用", "平台其他扣费"]
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

    if args.output:
        output_path = Path(args.output).expanduser().resolve()
    else:
        output_path = folder / "收入汇总.xlsx"
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

        for col_cells in worksheet.columns:
            max_len = 0
            col_letter = col_cells[0].column_letter
            for cell in col_cells:
                val = str(cell.value) if cell.value is not None else ""
                # 中文字符按2倍宽度计算
                length = sum(2 if ord(c) > 127 else 1 for c in val)
                if length > max_len:
                    max_len = length
            worksheet.column_dimensions[col_letter].width = max_len + 3

    print(f"\n[INFO] Excel已输出: {output_path}")


if __name__ == "__main__":
    main()

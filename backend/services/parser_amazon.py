"""
Amazon 解析服务 - 复用 parse_summary_report.py 核心逻辑
支持文件对象输入，提供入库方法
"""

import re
import io
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from datetime import datetime

import pdfplumber
import pandas as pd


def parse_amount(s: str) -> Decimal:
    return Decimal(s.replace(",", ""))


def format_amount(d: Decimal) -> str:
    return str(d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def parse_pdf(file_obj) -> dict:
    """
    解析 Amazon 月度汇总报告 PDF
    
    Args:
        file_obj: 文件对象 (BytesIO, bytes, 或文件路径)
    
    Returns:
        dict: 解析结果
    """
    if isinstance(file_obj, (str, Path)):
        with pdfplumber.open(str(file_obj)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    elif isinstance(file_obj, bytes):
        with pdfplumber.open(io.BytesIO(file_obj)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    else:
        # 假设是 BytesIO 或类似文件对象
        file_obj.seek(0)
        with pdfplumber.open(file_obj) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    
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
    ]
    shipping = Decimal("0")
    for item in shipping_items:
        pattern = rf"{re.escape(item)}\s+(-?\d[\d,]*\.\d{{2}}|-?\d+)"
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            shipping += parse_amount(m.group(1))
    
    # 仓储费用
    storage = Decimal("0")
    storage_item = "FBA inventory and inbound services fees"
    pattern = rf"{re.escape(storage_item)}\s+(-?\d[\d,]*\.\d{{2}}|-?\d+)"
    m = re.search(pattern, text, re.IGNORECASE)
    if m:
        storage += parse_amount(m.group(1))
    
    # 平台费用项目
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
    
    result = {
        "statement_month": statement_month or "",
        "currency": currency or "",
        "income": float(totals["Income"]),
        "tax": float(totals["Tax"]),
        "transfers": float(-totals["Transfers"]),
        "total_expenses": float(totals["Expenses"]),
        "ad_cost": float(advertising),
        "shipping_cost": float(shipping),
        "storage_cost": float(storage),
        "platform_fees": float(platform_fees),
    }
    
    return result


class AmazonParser:
    """Amazon 数据解析器"""
    
    def __init__(self):
        self.result = None
    
    def parse(self, file_obj) -> dict:
        """
        解析 Amazon PDF 文件
        
        Args:
            file_obj: 文件对象
        """
        self.result = parse_pdf(file_obj)
        return self.result
    
    def save_to_db(self, upload_id: int, shop_id: int) -> int:
        """
        将解析结果保存到数据库
        
        Args:
            upload_id: 上传记录ID
            shop_id: 店铺ID
        
        Returns:
            int: 插入的记录ID
        """
        from backend.dao import AmazonSummaryDAO
        
        if not self.result:
            raise ValueError("请先调用 parse() 方法")
        
        data = {
            'upload_id': upload_id,
            'shop_id': shop_id,
            'statement_month': self.result['statement_month'],
            'currency': self.result['currency'],
            'income': self.result['income'],
            'tax': self.result['tax'],
            'transfers': self.result['transfers'],
            'total_expenses': self.result['total_expenses'],
            'ad_cost': self.result['ad_cost'],
            'shipping_cost': self.result['shipping_cost'],
            'storage_cost': self.result['storage_cost'],
            'platform_fees': self.result['platform_fees'],
        }
        
        return AmazonSummaryDAO.create(data)

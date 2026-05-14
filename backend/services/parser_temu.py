"""
Temu 解析服务 - 复用 parse_temu_fund.py 核心逻辑
支持文件对象输入，提供入库方法
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple
import io

# 从原脚本导入核心函数
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from parse_temu_fund import (
    read_sheets, read_settlement, read_compensation,
    build_pivot, build_metrics, merge_shop,
    build_region_data, enrich_region_calcs,
    build_shop_data, reconcile, build_order_income,
    seller_center_data as _seller_center_data,
    REGIONS
)


def process_region_file(file_obj) -> Tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    处理单个区域账务明细文件
    
    Args:
        file_obj: 文件对象 (BytesIO 或文件路径)
    
    Returns:
        (pivot_df, metrics_df, extra_dict)
    """
    if isinstance(file_obj, (str, Path)):
        xl = pd.ExcelFile(str(file_obj))
    else:
        xl = pd.ExcelFile(file_obj)
    
    names = set(xl.sheet_names)
    is_empty = not ({"交易结算", "结算"} & names)
    is_half = "结算" in names and "交易结算" not in names
    
    if is_empty:
        empty_pivot = pd.DataFrame(
            columns=["SKU ID", "SKU货号", "货品名称", "SKU属性", "净回款总额"]
        )
        empty_metrics = pd.DataFrame(
            columns=[
                "SKU ID", "SKU货号", "货品名称", "SKU属性",
                "销售数量", "销售回款总额", "回款订单数量", "退款订单数量",
                "退货率", "赔付订单数量", "赔付率", "退货总额",
                "退货金额比例", "赔付金额", "赔付金额比例",
            ]
        )
        return empty_pivot, empty_metrics, {}
    
    settle, extra = read_settlement(xl, is_half)
    comp_dfs, sku_sheets, extra_comp = read_compensation(xl, is_half)
    extra["赔付总额"] = extra_comp
    pivot = build_pivot(settle, comp_dfs, sku_sheets)
    metrics = build_metrics(settle, comp_dfs)
    return pivot, metrics, extra


def process_seller_center_file(file_obj) -> Tuple[dict, dict, float, float, float]:
    """
    处理卖家中心账务明细文件
    
    Args:
        file_obj: 文件对象 (BytesIO 或文件路径)
    
    Returns:
        (fees, check, subsidy_adj, sc_total, sc_comp)
    """
    if isinstance(file_obj, (str, Path)):
        df = pd.read_excel(str(file_obj), sheet_name="账务明细列表")
    else:
        df = pd.read_excel(file_obj, sheet_name="账务明细列表")
    
    fees = {
        "仓储综合服务费": 0.0,
        "EPR费用": 0.0,
        "推广服务费": 0.0,
        "发货面单费": 0.0,
        "退货面单费": 0.0,
        "提现总额": 0.0,
    }
    check = {"结算总额": 0.0, "支出总额": 0.0, "调整总额": 0.0}
    subsidy_adj = 0.0
    
    df["收支金额"] = pd.to_numeric(df["收支金额"], errors="coerce").fillna(0)
    df["备注"] = df["备注"].astype(str)
    
    check["结算总额"] = float(df.loc[df["账务类型"] == "结算", "收支金额"].sum())
    check["支出总额"] = float(df.loc[df["账务类型"] == "支出", "收支金额"].sum())
    check["调整总额"] = float(df.loc[df["账务类型"] == "调整", "收支金额"].sum())
    fees["提现总额"] = float(df.loc[df["账务类型"] == "提现", "收支金额"].sum())
    
    for key, kw in [
        ("仓储综合服务费", "仓储"),
        ("推广服务费", "推广服务费"),
        ("EPR费用", "EPR"),
        ("发货面单费", "发货面单费"),
        ("退货面单费", "退货面单费"),
    ]:
        fees[key] = abs(float(
            df.loc[(df["账务类型"] == "支出") & (df["备注"].str.contains(kw)), "收支金额"].sum()
        ))
    
    subsidy_adj = abs(float(
        df.loc[
            (df["账务类型"] == "支出") & (df["备注"].str.contains("非商责平台售后补贴调整")),
            "收支金额",
        ].sum()
    ))
    
    total_expense = abs(float(df.loc[df["账务类型"] == "支出", "收支金额"].sum()))
    comp_from_center = abs(float(
        df.loc[
            (df["账务类型"] == "支出") & (df["备注"].str.contains("履约保障")),
            "收支金额",
        ].sum()
    ))
    
    return fees, check, subsidy_adj, total_expense, comp_from_center


class TemuParser:
    """Temu 数据解析器"""
    
    def __init__(self):
        self.region_files = {}  # {region: file_obj}
        self.seller_center_file = None
        self.results = {}
    
    def add_region_file(self, region: str, file_obj):
        """添加区域账务明细文件"""
        self.region_files[region] = file_obj
    
    def set_seller_center_file(self, file_obj):
        """设置卖家中心账务明细文件"""
        self.seller_center_file = file_obj
    
    def parse(self) -> dict:
        """
        解析所有文件
        
        Returns:
            {
                'shop_pivot': DataFrame,
                'shop_metrics': DataFrame,
                'order_income': DataFrame,
                'region_pivots': {region: DataFrame},
                'region_metrics': {region: DataFrame},
                'shop_data': dict,
                'reconcile_diff': float
            }
        """
        # 1. 解析各区域文件
        pivots, metrics, extras = {}, {}, {}
        for region in REGIONS:
            if region in self.region_files:
                p, m, e = process_region_file(self.region_files[region])
                pivots[region] = p
                metrics[region] = m
                extras[region] = e
            else:
                # 创建空数据
                pivots[region] = pd.DataFrame(columns=["SKU ID", "SKU货号", "货品名称", "SKU属性", "净回款总额"])
                metrics[region] = pd.DataFrame(columns=[
                    "SKU ID", "SKU货号", "货品名称", "SKU属性",
                    "销售数量", "销售回款总额", "回款订单数量", "退款订单数量",
                    "退货率", "赔付订单数量", "赔付率", "退货总额",
                    "退货金额比例", "赔付金额", "赔付金额比例",
                ])
                extras[region] = {}
        
        # 2. 合并店铺数据
        shop_pivot, shop_metrics = merge_shop(
            [pivots[r] for r in REGIONS],
            [metrics[r] for r in REGIONS]
        )
        
        # 3. 构建区域数据汇总
        region_data = enrich_region_calcs(build_region_data(pivots, metrics, extras))
        
        # 4. 解析卖家中心数据
        if self.seller_center_file:
            fees, check, subsidy_adj, sc_total, sc_comp = process_seller_center_file(self.seller_center_file)
        else:
            fees = {"仓储综合服务费": 0.0, "EPR费用": 0.0, "推广服务费": 0.0, 
                   "发货面单费": 0.0, "退货面单费": 0.0, "提现总额": 0.0}
            check = {"结算总额": 0.0, "支出总额": 0.0, "调整总额": 0.0}
            subsidy_adj = 0.0
            sc_total = 0.0
            sc_comp = 0.0
        
        # 5. 构建店铺汇总数据
        shop = build_shop_data(region_data, fees, check, subsidy_adj, sc_total, sc_comp)
        
        # 6. 对账检查
        diff = reconcile(shop, check)
        
        # 7. 构建订单收入汇总
        order_income = build_order_income(region_data, shop)
        
        self.results = {
            'shop_pivot': shop_pivot,
            'shop_metrics': shop_metrics,
            'order_income': order_income,
            'region_pivots': pivots,
            'region_metrics': metrics,
            'shop_data': shop,
            'reconcile_diff': diff
        }
        
        return self.results
    
    def save_to_db(self, upload_id: int, shop_id: int, year_month: str):
        """
        将解析结果保存到数据库
        
        Args:
            upload_id: 上传记录ID
            shop_id: 店铺ID
            year_month: 年月 (YYYY-MM)
        """
        from backend.dao import TemuOrderIncomeDAO, TemuSkuMetricsDAO
        
        if not self.results:
            raise ValueError("请先调用 parse() 方法")
        
        # 1. 保存订单收入汇总
        order_income = self.results['order_income']
        income_data = []
        for _, row in order_income.iterrows():
            income_data.append({
                'upload_id': upload_id,
                'shop_id': shop_id,
                'year_month': year_month,
                'metric_name': row['列名'],
                'shop_data': row.get('店铺数据'),
                'eu_data': row.get('欧区数据'),
                'us_data': row.get('美区数据'),
                'global_data': row.get('全球区数据'),
            })
        
        if income_data:
            TemuOrderIncomeDAO.batch_create(income_data)
        
        # 2. 保存 SKU 指标分析（店铺汇总 + 各区域）
        sku_data = []
        
        # 店铺汇总
        shop_metrics = self.results['shop_metrics']
        for _, row in shop_metrics.iterrows():
            sku_data.append({
                'upload_id': upload_id,
                'shop_id': shop_id,
                'region': '店铺汇总',
                'sku_id': row['SKU ID'],
                'sku_no': row['SKU货号'],
                'goods_name': row.get('货品名称', ''),
                'sku_attr': row.get('SKU属性', ''),
                'sales_qty': row.get('销售数量', 0),
                'sales_amount': row.get('销售回款总额', 0),
                'back_orders': row.get('回款订单数量', 0),
                'refund_orders': row.get('退款订单数量', 0),
                'refund_rate': row.get('退货率', 0),
                'comp_orders': row.get('赔付订单数量', 0),
                'comp_rate': row.get('赔付率', 0),
                'refund_amount': row.get('退货总额', 0),
                'refund_ratio': row.get('退货金额比例', 0),
                'comp_amount': row.get('赔付金额', 0),
                'comp_ratio': row.get('赔付金额比例', 0),
            })
        
        # 各区域
        for region in REGIONS:
            region_metrics = self.results['region_metrics'][region]
            for _, row in region_metrics.iterrows():
                sku_data.append({
                    'upload_id': upload_id,
                    'shop_id': shop_id,
                    'region': region,
                    'sku_id': row['SKU ID'],
                    'sku_no': row['SKU货号'],
                    'goods_name': row.get('货品名称', ''),
                    'sku_attr': row.get('SKU属性', ''),
                    'sales_qty': row.get('销售数量', 0),
                    'sales_amount': row.get('销售回款总额', 0),
                    'back_orders': row.get('回款订单数量', 0),
                    'refund_orders': row.get('退款订单数量', 0),
                    'refund_rate': row.get('退货率', 0),
                    'comp_orders': row.get('赔付订单数量', 0),
                    'comp_rate': row.get('赔付率', 0),
                    'refund_amount': row.get('退货总额', 0),
                    'refund_ratio': row.get('退货金额比例', 0),
                    'comp_amount': row.get('赔付金额', 0),
                    'comp_ratio': row.get('赔付金额比例', 0),
                })
        
        if sku_data:
            TemuSkuMetricsDAO.batch_create(sku_data)
        
        return {
            'order_income_count': len(income_data),
            'sku_metrics_count': len(sku_data)
        }

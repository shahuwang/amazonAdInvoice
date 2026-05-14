from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import io
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill

from backend.dao import (
    TemuOrderIncomeDAO, TemuSkuMetricsDAO, 
    AmazonSummaryDAO, ShopDAO
)

router = APIRouter(prefix="/api/reports", tags=["reports"])

class TemuIncomeResponse(BaseModel):
    metric_name: str
    shop_data: Optional[float]
    eu_data: Optional[float]
    us_data: Optional[float]
    global_data: Optional[float]

class TemuSkuResponse(BaseModel):
    sku_id: str
    sku_no: str
    goods_name: Optional[str]
    sku_attr: Optional[str]
    sales_qty: int
    sales_amount: float
    back_orders: int
    refund_orders: int
    refund_rate: float
    comp_orders: int
    comp_rate: float
    refund_amount: float
    refund_ratio: float
    comp_amount: float
    comp_ratio: float

class AmazonSummaryResponse(BaseModel):
    statement_month: str
    currency: Optional[str]
    income: Optional[float]
    tax: Optional[float]
    transfers: Optional[float]
    total_expenses: Optional[float]
    ad_cost: Optional[float]
    shipping_cost: Optional[float]
    storage_cost: Optional[float]
    platform_fees: Optional[float]

@router.get("/temu/income", response_model=List[TemuIncomeResponse])
async def get_temu_income(
    shop_id: int = Query(...),
    year_month: str = Query(...)
):
    """获取 Temu 订单收入汇总"""
    data = TemuOrderIncomeDAO.get_by_shop_month(shop_id, year_month)
    return data

@router.get("/temu/sku", response_model=List[TemuSkuResponse])
async def get_temu_sku(
    shop_id: int = Query(...),
    year_month: str = Query(...),
    region: Optional[str] = Query(None)
):
    """获取 Temu SKU 指标分析"""
    data = TemuSkuMetricsDAO.get_by_shop_month(shop_id, year_month, region)
    return data

@router.get("/amazon", response_model=Optional[AmazonSummaryResponse])
async def get_amazon_summary(
    shop_id: int = Query(...),
    year_month: str = Query(...)
):
    """获取 Amazon 汇总报告"""
    data = AmazonSummaryDAO.get_by_shop_month(shop_id, year_month)
    return data

@router.get("/download")
async def download_excel(
    shop_id: int = Query(...),
    year_month: str = Query(...),
    platform: str = Query(...),  # 'temu' or 'amazon'
    type: str = Query("summary")  # 'summary' or 'detail'
):
    """
    下载 Excel 报告
    
    Args:
        shop_id: 店铺ID
        year_month: 年月 (YYYY-MM)
        platform: 平台 (temu/amazon)
        type: 报告类型 (summary/detail)
    """
    shop = ShopDAO.get_by_id(shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail="店铺不存在")
    
    if platform == 'temu':
        return _generate_temu_excel(shop_id, year_month)
    elif platform == 'amazon':
        return _generate_amazon_excel(shop_id, year_month)
    else:
        raise HTTPException(status_code=400, detail=f"不支持的平台: {platform}")

def _generate_temu_excel(shop_id: int, year_month: str):
    """生成 Temu Excel 报告"""
    # 获取数据
    income_data = TemuOrderIncomeDAO.get_by_shop_month(shop_id, year_month)
    sku_data = TemuSkuMetricsDAO.get_by_shop_month(shop_id, year_month)
    
    if not income_data and not sku_data:
        raise HTTPException(status_code=404, detail="未找到数据")
    
    # 创建 Excel
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Sheet 1: 订单收入汇总
        if income_data:
            df_income = pd.DataFrame(income_data)
            df_income = df_income.rename(columns={
                'metric_name': '指标名称',
                'shop_data': '店铺数据',
                'eu_data': '欧区数据',
                'us_data': '美区数据',
                'global_data': '全球区数据'
            })
            # 只保留需要的列
            cols = ['指标名称', '店铺数据', '欧区数据', '美区数据', '全球区数据']
            df_income = df_income[[c for c in cols if c in df_income.columns]]
            df_income.to_excel(writer, index=False, sheet_name='订单收入汇总')
        
        # Sheet 2: SKU指标分析（店铺汇总）
        if sku_data:
            df_sku = pd.DataFrame(sku_data)
            df_sku = df_sku.rename(columns={
                'sku_id': 'SKU ID',
                'sku_no': 'SKU货号',
                'goods_name': '货品名称',
                'sku_attr': 'SKU属性',
                'sales_qty': '销售数量',
                'sales_amount': '销售回款总额',
                'back_orders': '回款订单数量',
                'refund_orders': '退款订单数量',
                'refund_rate': '退货率',
                'comp_orders': '赔付订单数量',
                'comp_rate': '赔付率',
                'refund_amount': '退货总额',
                'refund_ratio': '退货金额比例',
                'comp_amount': '赔付金额',
                'comp_ratio': '赔付金额比例'
            })
            # 只保留店铺汇总数据
            df_shop = df_sku[df_sku['region'] == '店铺汇总'] if 'region' in df_sku.columns else df_sku
            cols = ['SKU ID', 'SKU货号', '货品名称', 'SKU属性', '销售数量', '销售回款总额',
                   '回款订单数量', '退款订单数量', '退货率', '赔付订单数量', '赔付率',
                   '退货总额', '退货金额比例', '赔付金额', '赔付金额比例']
            df_shop = df_shop[[c for c in cols if c in df_shop.columns]]
            df_shop.to_excel(writer, index=False, sheet_name='SKU指标分析')
    
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=temu_report_{year_month}.xlsx"
        }
    )

def _generate_amazon_excel(shop_id: int, year_month: str):
    """生成 Amazon Excel 报告"""
    data = AmazonSummaryDAO.get_by_shop_month(shop_id, year_month)
    
    if not data:
        raise HTTPException(status_code=404, detail="未找到数据")
    
    # 创建 Excel
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df = pd.DataFrame([data])
        df = df.rename(columns={
            'statement_month': '账期月份',
            'currency': '币种',
            'income': '营业收入',
            'tax': '税费',
            'transfers': '提现金额',
            'total_expenses': '平台扣减总费用',
            'ad_cost': '广告支出',
            'shipping_cost': '运费支出',
            'storage_cost': '仓储费用',
            'platform_fees': '平台费用项目'
        })
        df.to_excel(writer, index=False, sheet_name='汇总')
    
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=amazon_report_{year_month}.xlsx"
        }
    )

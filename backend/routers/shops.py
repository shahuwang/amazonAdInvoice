from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from backend.dao import ShopDAO

router = APIRouter(prefix="/api/shops", tags=["shops"])

class ShopCreate(BaseModel):
    company_id: int
    name: str
    platform: str  # 'temu' or 'amazon'
    region: Optional[str] = None

class ShopResponse(BaseModel):
    id: int
    company_id: int
    name: str
    platform: str
    region: Optional[str]
    created_at: Optional[str] = None
    company_name: Optional[str] = None

def _format_datetime(data):
    """格式化 datetime 字段"""
    if data and data.get('created_at'):
        dt = data['created_at']
        data['created_at'] = dt.isoformat() if hasattr(dt, 'isoformat') else str(dt)
    return data

def _format_datetime_list(data_list):
    """格式化 datetime 字段列表"""
    for item in data_list:
        if item.get('created_at'):
            dt = item['created_at']
            item['created_at'] = dt.isoformat() if hasattr(dt, 'isoformat') else str(dt)
    return data_list

@router.get("/", response_model=List[ShopResponse])
async def list_shops(
    company_id: Optional[int] = Query(None),
    platform: Optional[str] = Query(None)
):
    """获取店铺列表"""
    shops = ShopDAO.get_all(company_id=company_id, platform=platform)
    return _format_datetime_list(shops)

@router.post("/", response_model=ShopResponse)
async def create_shop(shop: ShopCreate):
    """创建新店铺"""
    shop_id = ShopDAO.create(
        company_id=shop.company_id,
        name=shop.name,
        platform=shop.platform,
        region=shop.region
    )
    return _format_datetime(ShopDAO.get_by_id(shop_id))

@router.get("/{shop_id}", response_model=ShopResponse)
async def get_shop(shop_id: int):
    """获取店铺详情"""
    shop = ShopDAO.get_by_id(shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail="店铺不存在")
    return _format_datetime(shop)

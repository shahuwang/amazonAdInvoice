from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from backend.dao import CompanyDAO

router = APIRouter(prefix="/api/companies", tags=["companies"])

class CompanyCreate(BaseModel):
    name: str

class CompanyResponse(BaseModel):
    id: int
    name: str
    created_at: str = None

@router.get("/", response_model=List[CompanyResponse])
async def list_companies():
    """获取所有公司列表"""
    companies = CompanyDAO.get_all()
    # 转换 datetime 为字符串
    for c in companies:
        if c.get('created_at'):
            c['created_at'] = c['created_at'].isoformat() if hasattr(c['created_at'], 'isoformat') else str(c['created_at'])
    return companies

@router.post("/", response_model=CompanyResponse)
async def create_company(company: CompanyCreate):
    """创建新公司"""
    company_id = CompanyDAO.create(company.name)
    result = CompanyDAO.get_by_id(company_id)
    if result.get('created_at'):
        result['created_at'] = result['created_at'].isoformat() if hasattr(result['created_at'], 'isoformat') else str(result['created_at'])
    return result

@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(company_id: int):
    """获取公司详情"""
    company = CompanyDAO.get_by_id(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="公司不存在")
    if company.get('created_at'):
        company['created_at'] = company['created_at'].isoformat() if hasattr(company['created_at'], 'isoformat') else str(company['created_at'])
    return company

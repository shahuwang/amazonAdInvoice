import os
import shutil
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.dao import UploadDAO, ShopDAO
from backend.services.parser_temu import TemuParser
from backend.services.parser_amazon import AmazonParser
from backend.config import settings

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

def _format_upload(upload):
    """格式化上传记录中的 datetime 字段"""
    if upload and upload.get('created_at'):
        dt = upload['created_at']
        upload['created_at'] = dt.isoformat() if hasattr(dt, 'isoformat') else str(dt)
    if upload and upload.get('parsed_at'):
        dt = upload['parsed_at']
        upload['parsed_at'] = dt.isoformat() if hasattr(dt, 'isoformat') else str(dt)
    return upload

@router.post("/")
async def upload_file(
    shop_id: int = Form(...),
    year_month: str = Form(...),
    file_type: str = Form(...),
    file: UploadFile = File(...)
):
    """
    上传文件
    
    Args:
        shop_id: 店铺ID
        year_month: 年月 (YYYY-MM)
        file_type: 文件类型 (temu_seller_center, temu_us, temu_eu, temu_global, amazon_summary, amazon_orders)
        file: 上传的文件
    """
    # 验证店铺存在
    shop = ShopDAO.get_by_id(shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail="店铺不存在")
    
    # 创建上传目录
    upload_dir = os.path.join(settings.UPLOAD_DIR, str(shop_id), year_month)
    os.makedirs(upload_dir, exist_ok=True)
    
    # 保存文件
    file_path = os.path.join(upload_dir, f"{file_type}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # 创建上传记录
    upload_id = UploadDAO.create(
        shop_id=shop_id,
        year_month=year_month,
        file_type=file_type,
        file_path=file_path
    )
    
    return _format_upload(UploadDAO.get_by_id(upload_id))

@router.post("/{upload_id}/parse")
async def parse_upload(upload_id: int):
    """
    触发解析
    
    Args:
        upload_id: 上传记录ID
    """
    upload = UploadDAO.get_by_id(upload_id)
    if not upload:
        raise HTTPException(status_code=404, detail="上传记录不存在")
    
    # 更新状态为解析中
    UploadDAO.update_status(upload_id, 'parsing')
    
    try:
        file_type = upload['file_type']
        shop_id = upload['shop_id']
        year_month = upload['year_month']
        file_path = upload['file_path']
        
        if file_type.startswith('temu_'):
            # Temu 文件 - 这里只处理单个文件
            # 实际使用时，前端应该先上传所有文件，然后调用批量解析
            UploadDAO.update_status(upload_id, 'success')
            return {"id": upload_id, "status": "success", "message": "文件上传成功，请调用批量解析接口"}
        
        elif file_type == 'amazon_summary':
            # Amazon 汇总报告
            parser = AmazonParser()
            parser.parse(file_path)
            parser.save_to_db(upload_id=upload_id, shop_id=shop_id)
            UploadDAO.update_status(upload_id, 'success')
            return {"id": upload_id, "status": "success", "message": "Amazon 解析完成"}
        
        else:
            UploadDAO.update_status(upload_id, 'failed', f"不支持的文件类型: {file_type}")
            raise HTTPException(status_code=400, detail=f"不支持的文件类型: {file_type}")
    
    except Exception as e:
        UploadDAO.update_status(upload_id, 'failed', str(e))
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")

@router.post("/batch-parse")
async def batch_parse(body: dict):
    upload_ids = body.get('upload_ids', [])
    """
    批量解析（主要用于 Temu 的多个文件一起解析）
    
    Args:
        upload_ids: 上传记录ID列表
    """
    uploads = []
    for uid in upload_ids:
        upload = UploadDAO.get_by_id(uid)
        if not upload:
            raise HTTPException(status_code=404, detail=f"上传记录不存在: {uid}")
        uploads.append(upload)
    
    # 按店铺和年月分组
    groups = {}
    for upload in uploads:
        key = (upload['shop_id'], upload['year_month'])
        if key not in groups:
            groups[key] = []
        groups[key].append(upload)
    
    results = []
    for (shop_id, year_month), group_uploads in groups.items():
        try:
            # 检查是否是 Temu
            shop = ShopDAO.get_by_id(shop_id)
            if shop['platform'] != 'temu':
                continue
            
            # 构建解析器
            parser = TemuParser()
            seller_center_upload = None
            
            for upload in group_uploads:
                UploadDAO.update_status(upload['id'], 'parsing')
                file_type = upload['file_type']
                file_path = upload['file_path']
                
                if file_type == 'temu_seller_center':
                    seller_center_upload = upload
                elif file_type == 'temu_eu':
                    parser.add_region_file('欧区', file_path)
                elif file_type == 'temu_us':
                    parser.add_region_file('美区', file_path)
                elif file_type == 'temu_global':
                    parser.add_region_file('全球区', file_path)
            
            # 设置卖家中心文件
            if seller_center_upload:
                parser.set_seller_center_file(seller_center_upload['file_path'])
            
            # 解析
            parser.parse()
            
            # 获取一个 upload_id 用于保存数据
            primary_upload = seller_center_upload or group_uploads[0]
            parser.save_to_db(
                upload_id=primary_upload['id'],
                shop_id=shop_id,
                year_month=year_month
            )
            
            # 更新所有上传记录为成功
            for upload in group_uploads:
                UploadDAO.update_status(upload['id'], 'success')
            
            results.append({
                'shop_id': shop_id,
                'year_month': year_month,
                'status': 'success'
            })
        
        except Exception as e:
            # 更新所有上传记录为失败
            for upload in group_uploads:
                UploadDAO.update_status(upload['id'], 'failed', str(e))
            
            results.append({
                'shop_id': shop_id,
                'year_month': year_month,
                'status': 'failed',
                'error': str(e)
            })
    
    return {"results": results}

@router.get("/{upload_id}")
async def get_upload(upload_id: int):
    """获取上传记录详情"""
    upload = UploadDAO.get_by_id(upload_id)
    if not upload:
        raise HTTPException(status_code=404, detail="上传记录不存在")
    return upload

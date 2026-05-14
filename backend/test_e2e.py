"""
端到端联调测试脚本
测试流程：创建公司/店铺 -> 上传文件 -> 解析 -> 查询 -> 下载
"""

import requests
import os
from pathlib import Path

BASE_URL = "http://localhost:8000"

class E2ETest:
    def __init__(self):
        self.company_id = None
        self.shop_id = None
        self.upload_ids = []
    
    def run(self):
        print("="*60)
        print("开始端到端联调测试")
        print("="*60)
        
        # 1. 创建公司
        self.create_company()
        
        # 2. 创建店铺
        self.create_shop()
        
        # 3. 测试 Amazon 流程
        self.test_amazon_flow()
        
        # 4. 测试 Temu 流程
        self.test_temu_flow()
        
        print("\n" + "="*60)
        print("联调测试完成！")
        print("="*60)
    
    def create_company(self):
        print("\n1. 创建测试公司...")
        r = requests.post(f"{BASE_URL}/api/companies/", json={"name": "呆鸥"})
        if r.status_code == 200:
            self.company_id = r.json()["id"]
            print(f"   ✓ 公司创建成功: id={self.company_id}")
        else:
            print(f"   ✗ 公司创建失败: {r.status_code}")
            raise Exception("创建公司失败")
    
    def create_shop(self):
        print("\n2. 创建测试店铺...")
        
        # Amazon 店铺
        r = requests.post(f"{BASE_URL}/api/shops/", json={
            "company_id": self.company_id,
            "name": "呆鸥亚马逊北美",
            "platform": "amazon",
            "region": "北美"
        })
        if r.status_code == 200:
            self.amazon_shop_id = r.json()["id"]
            print(f"   ✓ Amazon 店铺创建成功: id={self.amazon_shop_id}")
        else:
            print(f"   ✗ Amazon 店铺创建失败: {r.status_code}")
        
        # Temu 店铺
        r = requests.post(f"{BASE_URL}/api/shops/", json={
            "company_id": self.company_id,
            "name": "呆鸥 Temu",
            "platform": "temu",
            "region": "欧区"
        })
        if r.status_code == 200:
            self.temu_shop_id = r.json()["id"]
            print(f"   ✓ Temu 店铺创建成功: id={self.temu_shop_id}")
        else:
            print(f"   ✗ Temu 店铺创建失败: {r.status_code}")
    
    def test_amazon_flow(self):
        print("\n3. 测试 Amazon 流程...")
        
        # 上传 PDF
        pdf_file = Path(__file__).parent.parent / "report" / "呆鸥亚马逊北美3月汇总.pdf.pdf"
        if not pdf_file.exists():
            print(f"   ⚠ PDF 文件不存在，跳过 Amazon 测试")
            return
        
        with open(pdf_file, "rb") as f:
            files = {"file": ("report.pdf", f, "application/pdf")}
            data = {
                "shop_id": self.amazon_shop_id,
                "year_month": "2026-03",
                "file_type": "amazon_summary"
            }
            r = requests.post(f"{BASE_URL}/api/uploads/", data=data, files=files)
        
        if r.status_code == 200:
            upload_id = r.json()["id"]
            print(f"   ✓ 文件上传成功: upload_id={upload_id}")
            
            # 解析
            r = requests.post(f"{BASE_URL}/api/uploads/{upload_id}/parse")
            if r.status_code == 200:
                print(f"   ✓ 解析成功: {r.json()}")
                
                # 查询报告
                r = requests.get(f"{BASE_URL}/api/reports/amazon", params={
                    "shop_id": self.amazon_shop_id,
                    "year_month": "2026-03"
                })
                if r.status_code == 200:
                    print(f"   ✓ 查询成功: {r.json()}")
                    
                    # 下载 Excel
                    r = requests.get(f"{BASE_URL}/api/reports/download", params={
                        "shop_id": self.amazon_shop_id,
                        "year_month": "2026-03",
                        "platform": "amazon"
                    })
                    if r.status_code == 200:
                        print(f"   ✓ Excel 下载成功: {len(r.content)} bytes")
                    else:
                        print(f"   ✗ Excel 下载失败: {r.status_code}")
                else:
                    print(f"   ✗ 查询失败: {r.status_code}")
            else:
                print(f"   ✗ 解析失败: {r.status_code}, {r.text}")
        else:
            print(f"   ✗ 上传失败: {r.status_code}, {r.text}")
    
    def test_temu_flow(self):
        print("\n4. 测试 Temu 流程...")
        
        test_folder = Path(__file__).parent.parent / "temu" / "GZDAIOU" / "3月"
        if not test_folder.exists():
            print(f"   ⚠ 测试数据不存在，跳过 Temu 测试")
            return
        
        upload_ids = []
        
        # 上传各区域文件
        for file_type, filename in [
            ("temu_eu", "欧区账务明细.xlsx"),
            ("temu_us", "美区账务明细.xlsx"),
            ("temu_global", "全球区账务明细.xlsx"),
            ("temu_seller_center", "卖家中心账务明细.xlsx")
        ]:
            file_path = test_folder / filename
            if not file_path.exists():
                print(f"   ⚠ 文件不存在: {filename}")
                continue
            
            with open(file_path, "rb") as f:
                files = {"file": (filename, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
                data = {
                    "shop_id": self.temu_shop_id,
                    "year_month": "2025-03",
                    "file_type": file_type
                }
                r = requests.post(f"{BASE_URL}/api/uploads/", data=data, files=files)
            
            if r.status_code == 200:
                upload_id = r.json()["id"]
                upload_ids.append(upload_id)
                print(f"   ✓ {filename} 上传成功: upload_id={upload_id}")
            else:
                print(f"   ✗ {filename} 上传失败: {r.status_code}")
        
        if upload_ids:
            # 批量解析
            r = requests.post(f"{BASE_URL}/api/uploads/batch-parse", json={"upload_ids": upload_ids})
            if r.status_code == 200:
                print(f"   ✓ 批量解析成功: {r.json()}")
                
                # 查询报告
                r = requests.get(f"{BASE_URL}/api/reports/temu/income", params={
                    "shop_id": self.temu_shop_id,
                    "year_month": "2025-03"
                })
                if r.status_code == 200:
                    data = r.json()
                    print(f"   ✓ 订单收入查询成功: {len(data)} 条记录")
                    
                    # 查询 SKU
                    r = requests.get(f"{BASE_URL}/api/reports/temu/sku", params={
                        "shop_id": self.temu_shop_id,
                        "year_month": "2025-03"
                    })
                    if r.status_code == 200:
                        data = r.json()
                        print(f"   ✓ SKU 指标查询成功: {len(data)} 条记录")
                        
                        # 下载 Excel
                        r = requests.get(f"{BASE_URL}/api/reports/download", params={
                            "shop_id": self.temu_shop_id,
                            "year_month": "2025-03",
                            "platform": "temu"
                        })
                        if r.status_code == 200:
                            print(f"   ✓ Excel 下载成功: {len(r.content)} bytes")
                        else:
                            print(f"   ✗ Excel 下载失败: {r.status_code}")
                    else:
                        print(f"   ✗ SKU 指标查询失败: {r.status_code}")
                else:
                    print(f"   ✗ 订单收入查询失败: {r.status_code}")
            else:
                print(f"   ✗ 批量解析失败: {r.status_code}, {r.text}")


if __name__ == "__main__":
    test = E2ETest()
    test.run()

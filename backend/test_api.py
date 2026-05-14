# 测试 API
import requests
import time

BASE_URL = "http://localhost:8000"

def test_api():
    # 1. 健康检查
    print("1. 健康检查...")
    r = requests.get(f"{BASE_URL}/health")
    print(f"   Status: {r.status_code}, Response: {r.json()}")
    
    # 2. 创建公司
    print("\n2. 创建公司...")
    r = requests.post(f"{BASE_URL}/api/companies/", json={"name": "测试公司"})
    print(f"   Status: {r.status_code}")
    company_id = r.json()["id"] if r.status_code == 200 else None
    
    # 3. 创建店铺
    print("\n3. 创建店铺...")
    r = requests.post(f"{BASE_URL}/api/shops/", json={
        "company_id": company_id,
        "name": "测试Temu店铺",
        "platform": "temu",
        "region": "欧区"
    })
    print(f"   Status: {r.status_code}")
    shop_id = r.json()["id"] if r.status_code == 200 else None
    
    # 4. 上传文件（模拟）
    print("\n4. 上传文件...")
    # 这里需要实际的文件路径
    # files = {'file': open('test.xlsx', 'rb')}
    # r = requests.post(f"{BASE_URL}/api/uploads/", data={
    #     "shop_id": shop_id,
    #     "year_month": "2025-01",
    #     "file_type": "temu_eu"
    # }, files=files)
    # print(f"   Status: {r.status_code}")
    print("   (跳过文件上传测试，需要实际文件)")
    
    # 5. 查询店铺列表
    print("\n5. 查询店铺列表...")
    r = requests.get(f"{BASE_URL}/api/shops/")
    print(f"   Status: {r.status_code}, Count: {len(r.json())}")
    
    print("\nAPI 测试完成！")

if __name__ == "__main__":
    test_api()

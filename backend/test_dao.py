# 快速测试 DAO
from backend.dao import CompanyDAO, ShopDAO

# 测试公司 CRUD
company_id = CompanyDAO.create("测试公司")
print(f"创建公司: id={company_id}")

company = CompanyDAO.get_by_id(company_id)
print(f"查询公司: {company}")

companies = CompanyDAO.get_all()
print(f"所有公司: {len(companies)} 条")

# 测试店铺 CRUD
shop_id = ShopDAO.create(company_id, "测试店铺", "temu", "欧区")
print(f"创建店铺: id={shop_id}")

shop = ShopDAO.get_by_id(shop_id)
print(f"查询店铺: {shop}")

shops = ShopDAO.get_all()
print(f"所有店铺: {len(shops)} 条")

print("\nDAO 测试通过！")

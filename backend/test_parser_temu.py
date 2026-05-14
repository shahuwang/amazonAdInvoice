# 测试 Temu 解析器
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.parser_temu import TemuParser

# 测试数据路径
test_folder = Path(__file__).parent.parent / "temu" / "GZDAIOU" / "3月"

if not test_folder.exists():
    print(f"测试数据不存在: {test_folder}")
    sys.exit(1)

parser = TemuParser()

# 添加区域文件
for region in ["欧区", "美区", "全球区"]:
    file_path = test_folder / f"{region}账务明细.xlsx"
    if file_path.exists():
        parser.add_region_file(region, file_path)
        print(f"添加区域文件: {region}")

# 添加卖家中心文件
sc_file = test_folder / "卖家中心账务明细.xlsx"
if sc_file.exists():
    parser.set_seller_center_file(sc_file)
    print("添加卖家中心文件")

# 解析
results = parser.parse()
print(f"\n解析完成！")
print(f"店铺汇总行数: {len(results['shop_pivot'])}")
print(f"店铺指标行数: {len(results['shop_metrics'])}")
print(f"订单收入行数: {len(results['order_income'])}")
print(f"对账差异: {results['reconcile_diff']:.2f}")
print(f"\n店铺数据预览:")
for k, v in list(results['shop_data'].items())[:5]:
    print(f"  {k}: {v}")

# 测试入库（需要实际的 upload_id 和 shop_id）
# save_result = parser.save_to_db(upload_id=1, shop_id=1, year_month="2025-01")
# print(f"\n入库结果: {save_result}")

print("\nTemu 解析器测试通过！")

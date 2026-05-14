# 测试 Amazon 解析器
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.parser_amazon import AmazonParser

# 测试文件
test_file = Path(__file__).parent.parent / "report" / "呆鸥亚马逊北美3月汇总.pdf.pdf"

if not test_file.exists():
    print(f"测试文件不存在: {test_file}")
    sys.exit(1)

parser = AmazonParser()
result = parser.parse(test_file)

print("解析结果:")
for k, v in result.items():
    print(f"  {k}: {v}")

print("\nAmazon 解析器测试通过！")

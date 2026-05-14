"""
初始化脚本：插入默认公司和店铺数据
"""

import sys
sys.path.insert(0, '/home/shahuwang/workspace/amazonAdInvoice')

from backend.db import get_connection

COMPANIES = [
    '呆鸥',
    '捷湃'
]

SHOPS = [
    # 呆鸥 - Amazon
    {'company_name': '呆鸥', 'name': '呆鸥亚马逊美国店', 'platform': 'amazon', 'region': '美国'},
    {'company_name': '呆鸥', 'name': '呆鸥亚马逊加拿大店', 'platform': 'amazon', 'region': '加拿大'},
    
    # 呆鸥 - Temu
    {'company_name': '呆鸥', 'name': 'DAIOU', 'platform': 'temu', 'region': '欧区'},
    {'company_name': '呆鸥', 'name': 'GZDAIOU', 'platform': 'temu', 'region': '欧区'},
    
    # 捷湃 - Amazon
    {'company_name': '捷湃', 'name': '捷湃亚马逊美国店', 'platform': 'amazon', 'region': '美国'},
    {'company_name': '捷湃', 'name': '捷湃亚马逊加拿大店', 'platform': 'amazon', 'region': '加拿大'},
    
    # 捷湃 - Temu
    {'company_name': '捷湃', 'name': 'JAYPACT', 'platform': 'temu', 'region': '欧区'},
]

def init_data():
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 清空现有数据
        cursor.execute('DELETE FROM amazon_summary')
        cursor.execute('DELETE FROM temu_sku_metrics')
        cursor.execute('DELETE FROM temu_order_income')
        cursor.execute('DELETE FROM upload_records')
        cursor.execute('DELETE FROM shops')
        cursor.execute('DELETE FROM companies')
        
        # 插入公司
        company_map = {}
        for name in COMPANIES:
            cursor.execute('INSERT INTO companies (name) VALUES (%s)', (name,))
            company_map[name] = cursor.lastrowid
        
        # 插入店铺
        for shop in SHOPS:
            company_id = company_map[shop['company_name']]
            cursor.execute(
                'INSERT INTO shops (company_id, name, platform, region) VALUES (%s, %s, %s, %s)',
                (company_id, shop['name'], shop['platform'], shop['region'])
            )
        
        # 确认
        cursor.execute('SELECT * FROM companies')
        print('公司列表:')
        for row in cursor.fetchall():
            print(f"  {row['id']}: {row['name']}")
        
        cursor.execute('SELECT * FROM shops')
        print('\n店铺列表:')
        for row in cursor.fetchall():
            print(f"  {row['id']}: {row['name']} ({row['platform']})")
        
        conn.commit()
        print('\n初始化完成！')

if __name__ == '__main__':
    init_data()

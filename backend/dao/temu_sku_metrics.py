from typing import List
from backend.db import get_cursor

class TemuSkuMetricsDAO:
    @staticmethod
    def batch_create(data_list: List[dict]) -> int:
        with get_cursor() as cursor:
            sql = """INSERT INTO temu_sku_metrics 
                     (`upload_id`, `shop_id`, `region`, `sku_id`, `sku_no`, 
                      `goods_name`, `sku_attr`, `sales_qty`, `sales_amount`, 
                      `back_orders`, `refund_orders`, `refund_rate`, `comp_orders`, 
                      `comp_rate`, `refund_amount`, `refund_ratio`, `comp_amount`, `comp_ratio`) 
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
            values = [
                (
                    d['upload_id'], d['shop_id'], d['region'], d['sku_id'], d['sku_no'],
                    d.get('goods_name'), d.get('sku_attr'), d.get('sales_qty', 0),
                    d.get('sales_amount', 0), d.get('back_orders', 0), d.get('refund_orders', 0),
                    d.get('refund_rate', 0), d.get('comp_orders', 0), d.get('comp_rate', 0),
                    d.get('refund_amount', 0), d.get('refund_ratio', 0),
                    d.get('comp_amount', 0), d.get('comp_ratio', 0)
                )
                for d in data_list
            ]
            cursor.executemany(sql, values)
            return cursor.rowcount
    
    @staticmethod
    def get_by_upload(upload_id: int, region: str = None) -> List[dict]:
        with get_cursor() as cursor:
            sql = "SELECT * FROM temu_sku_metrics WHERE `upload_id` = %s"
            params = [upload_id]
            if region:
                sql += " AND `region` = %s"
                params.append(region)
            sql += " ORDER BY `sales_amount` DESC"
            cursor.execute(sql, params)
            return cursor.fetchall()
    
    @staticmethod
    def get_by_shop_month(shop_id: int, year_month: str, region: str = None) -> List[dict]:
        with get_cursor() as cursor:
            # 需要通过 upload_records 关联查询
            sql = """
                SELECT m.* FROM temu_sku_metrics m
                JOIN upload_records u ON m.upload_id = u.id
                WHERE m.`shop_id` = %s AND u.`year_month` = %s
            """
            params = [shop_id, year_month]
            if region:
                sql += " AND m.`region` = %s"
                params.append(region)
            sql += " ORDER BY m.`sales_amount` DESC"
            cursor.execute(sql, params)
            return cursor.fetchall()
    
    @staticmethod
    def delete_by_upload(upload_id: int) -> bool:
        with get_cursor() as cursor:
            cursor.execute("DELETE FROM temu_sku_metrics WHERE `upload_id` = %s", (upload_id,))
            return cursor.rowcount > 0

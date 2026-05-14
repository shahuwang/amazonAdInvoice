from typing import List
from backend.db import get_cursor

class TemuOrderIncomeDAO:
    @staticmethod
    def batch_create(data_list: List[dict]) -> int:
        with get_cursor() as cursor:
            sql = """INSERT INTO temu_order_income 
                     (`upload_id`, `shop_id`, `year_month`, `metric_name`, 
                      `shop_data`, `eu_data`, `us_data`, `global_data`) 
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
            values = [
                (
                    d['upload_id'], d['shop_id'], d['year_month'], d['metric_name'],
                    d.get('shop_data'), d.get('eu_data'), d.get('us_data'), d.get('global_data')
                )
                for d in data_list
            ]
            cursor.executemany(sql, values)
            return cursor.rowcount
    
    @staticmethod
    def get_by_upload(upload_id: int) -> List[dict]:
        with get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM temu_order_income WHERE `upload_id` = %s ORDER BY `id`",
                (upload_id,)
            )
            return cursor.fetchall()
    
    @staticmethod
    def get_by_shop_month(shop_id: int, year_month: str) -> List[dict]:
        with get_cursor() as cursor:
            cursor.execute(
                """SELECT * FROM temu_order_income 
                   WHERE `shop_id` = %s AND `year_month` = %s 
                   ORDER BY `id`""",
                (shop_id, year_month)
            )
            return cursor.fetchall()
    
    @staticmethod
    def delete_by_upload(upload_id: int) -> bool:
        with get_cursor() as cursor:
            cursor.execute("DELETE FROM temu_order_income WHERE `upload_id` = %s", (upload_id,))
            return cursor.rowcount > 0

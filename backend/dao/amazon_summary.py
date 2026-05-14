from typing import List, Optional
from backend.db import get_cursor

class AmazonSummaryDAO:
    @staticmethod
    def create(data: dict) -> int:
        with get_cursor() as cursor:
            cursor.execute(
                """INSERT INTO amazon_summary 
                   (`upload_id`, `shop_id`, `statement_month`, `currency`, 
                    `income`, `tax`, `transfers`, `total_expenses`, 
                    `ad_cost`, `shipping_cost`, `storage_cost`, `platform_fees`) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    data['upload_id'], data['shop_id'], data['statement_month'],
                    data.get('currency'), data.get('income'), data.get('tax'),
                    data.get('transfers'), data.get('total_expenses'),
                    data.get('ad_cost'), data.get('shipping_cost'),
                    data.get('storage_cost'), data.get('platform_fees')
                )
            )
            return cursor.lastrowid
    
    @staticmethod
    def get_by_upload(upload_id: int) -> Optional[dict]:
        with get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM amazon_summary WHERE `upload_id` = %s",
                (upload_id,)
            )
            return cursor.fetchone()
    
    @staticmethod
    def get_by_shop_month(shop_id: int, year_month: str) -> Optional[dict]:
        with get_cursor() as cursor:
            cursor.execute(
                """SELECT * FROM amazon_summary 
                   WHERE `shop_id` = %s AND `statement_month` = %s""",
                (shop_id, year_month)
            )
            return cursor.fetchone()
    
    @staticmethod
    def delete_by_upload(upload_id: int) -> bool:
        with get_cursor() as cursor:
            cursor.execute("DELETE FROM amazon_summary WHERE `upload_id` = %s", (upload_id,))
            return cursor.rowcount > 0

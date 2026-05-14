from typing import List, Optional
from backend.db import get_cursor

class UploadDAO:
    @staticmethod
    def create(shop_id: int, year_month: str, file_type: str, file_path: str) -> int:
        with get_cursor() as cursor:
            cursor.execute(
                """INSERT INTO upload_records 
                   (`shop_id`, `year_month`, `file_type`, `file_path`, `status`) 
                   VALUES (%s, %s, %s, %s, 'pending')""",
                (shop_id, year_month, file_type, file_path)
            )
            return cursor.lastrowid
    
    @staticmethod
    def get_by_id(upload_id: int) -> Optional[dict]:
        with get_cursor() as cursor:
            cursor.execute("SELECT * FROM upload_records WHERE `id` = %s", (upload_id,))
            return cursor.fetchone()
    
    @staticmethod
    def get_by_shop(shop_id: int, year_month: str = None) -> List[dict]:
        with get_cursor() as cursor:
            sql = "SELECT * FROM upload_records WHERE `shop_id` = %s"
            params = [shop_id]
            if year_month:
                sql += " AND `year_month` = %s"
                params.append(year_month)
            sql += " ORDER BY `created_at` DESC"
            cursor.execute(sql, params)
            return cursor.fetchall()
    
    @staticmethod
    def update_status(upload_id: int, status: str, error_msg: str = None) -> bool:
        with get_cursor() as cursor:
            if status == 'success':
                cursor.execute(
                    """UPDATE upload_records 
                       SET `status` = %s, `error_msg` = %s, `parsed_at` = NOW() 
                       WHERE `id` = %s""",
                    (status, error_msg, upload_id)
                )
            else:
                cursor.execute(
                    "UPDATE upload_records SET `status` = %s, `error_msg` = %s WHERE `id` = %s",
                    (status, error_msg, upload_id)
                )
            return cursor.rowcount > 0
    
    @staticmethod
    def delete(upload_id: int) -> bool:
        with get_cursor() as cursor:
            cursor.execute("DELETE FROM upload_records WHERE `id` = %s", (upload_id,))
            return cursor.rowcount > 0

from typing import List, Optional
from backend.db import get_cursor

class ShopDAO:
    @staticmethod
    def create(company_id: int, name: str, platform: str, region: str = None) -> int:
        with get_cursor() as cursor:
            cursor.execute(
                "INSERT INTO shops (`company_id`, `name`, `platform`, `region`) VALUES (%s, %s, %s, %s)",
                (company_id, name, platform, region)
            )
            return cursor.lastrowid
    
    @staticmethod
    def get_by_id(shop_id: int) -> Optional[dict]:
        with get_cursor() as cursor:
            cursor.execute("""
                SELECT s.*, c.name as company_name 
                FROM shops s 
                JOIN companies c ON s.company_id = c.id 
                WHERE s.`id` = %s
            """, (shop_id,))
            return cursor.fetchone()
    
    @staticmethod
    def get_all(company_id: int = None, platform: str = None) -> List[dict]:
        with get_cursor() as cursor:
            sql = """
                SELECT s.*, c.name as company_name 
                FROM shops s 
                JOIN companies c ON s.company_id = c.id 
                WHERE 1=1
            """
            params = []
            if company_id:
                sql += " AND s.`company_id` = %s"
                params.append(company_id)
            if platform:
                sql += " AND s.`platform` = %s"
                params.append(platform)
            sql += " ORDER BY s.`id` DESC"
            cursor.execute(sql, params)
            return cursor.fetchall()
    
    @staticmethod
    def get_by_company(company_id: int) -> List[dict]:
        with get_cursor() as cursor:
            cursor.execute("SELECT * FROM shops WHERE `company_id` = %s", (company_id,))
            return cursor.fetchall()
    
    @staticmethod
    def update(shop_id: int, name: str = None, region: str = None) -> bool:
        with get_cursor() as cursor:
            updates = []
            params = []
            if name:
                updates.append("`name` = %s")
                params.append(name)
            if region:
                updates.append("`region` = %s")
                params.append(region)
            if not updates:
                return False
            params.append(shop_id)
            sql = f"UPDATE shops SET {', '.join(updates)} WHERE `id` = %s"
            cursor.execute(sql, params)
            return cursor.rowcount > 0
    
    @staticmethod
    def delete(shop_id: int) -> bool:
        with get_cursor() as cursor:
            cursor.execute("DELETE FROM shops WHERE `id` = %s", (shop_id,))
            return cursor.rowcount > 0

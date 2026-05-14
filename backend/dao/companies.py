from typing import List, Optional
from backend.db import get_cursor

class CompanyDAO:
    @staticmethod
    def create(name: str) -> int:
        with get_cursor() as cursor:
            cursor.execute("INSERT INTO companies (`name`) VALUES (%s)", (name,))
            return cursor.lastrowid
    
    @staticmethod
    def get_by_id(company_id: int) -> Optional[dict]:
        with get_cursor() as cursor:
            cursor.execute("SELECT * FROM companies WHERE `id` = %s", (company_id,))
            return cursor.fetchone()
    
    @staticmethod
    def get_all() -> List[dict]:
        with get_cursor() as cursor:
            cursor.execute("SELECT * FROM companies ORDER BY `id` DESC")
            return cursor.fetchall()
    
    @staticmethod
    def update(company_id: int, name: str) -> bool:
        with get_cursor() as cursor:
            cursor.execute("UPDATE companies SET `name` = %s WHERE `id` = %s", (name, company_id))
            return cursor.rowcount > 0
    
    @staticmethod
    def delete(company_id: int) -> bool:
        with get_cursor() as cursor:
            cursor.execute("DELETE FROM companies WHERE `id` = %s", (company_id,))
            return cursor.rowcount > 0

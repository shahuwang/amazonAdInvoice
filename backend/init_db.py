import pymysql
from backend.config import settings

def get_conn():
    return pymysql.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def init_database():
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{settings.DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            cursor.execute(f"USE `{settings.DB_NAME}`")
            
            tables = [
                """
                CREATE TABLE IF NOT EXISTS companies (
                    `id`          INT PRIMARY KEY AUTO_INCREMENT,
                    `name`        VARCHAR(100) NOT NULL COMMENT '公司名称',
                    `created_at`  DATETIME DEFAULT CURRENT_TIMESTAMP
                ) COMMENT='公司表'
                """,
                """
                CREATE TABLE IF NOT EXISTS shops (
                    `id`          INT PRIMARY KEY AUTO_INCREMENT,
                    `company_id`  INT NOT NULL COMMENT '所属公司',
                    `name`        VARCHAR(100) NOT NULL COMMENT '店铺名称',
                    `platform`    ENUM('temu', 'amazon') NOT NULL COMMENT '平台',
                    `region`      VARCHAR(50) COMMENT '区域 (美国/加拿大/欧区/美区/全球区)',
                    `created_at`  DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (`company_id`) REFERENCES companies(`id`)
                ) COMMENT='店铺表'
                """,
                """
                CREATE TABLE IF NOT EXISTS upload_records (
                    `id`              INT PRIMARY KEY AUTO_INCREMENT,
                    `shop_id`         INT NOT NULL COMMENT '所属店铺',
                    `year_month`      VARCHAR(7) NOT NULL COMMENT '年月 (YYYY-MM)',
                    `file_type`       VARCHAR(50) NOT NULL COMMENT '文件类型',
                    `file_path`       VARCHAR(500) COMMENT '文件存储路径',
                    `status`          ENUM('pending', 'parsing', 'success', 'failed') DEFAULT 'pending',
                    `error_msg`       TEXT COMMENT '错误信息',
                    `created_at`      DATETIME DEFAULT CURRENT_TIMESTAMP,
                    `parsed_at`       DATETIME COMMENT '解析完成时间',
                    FOREIGN KEY (`shop_id`) REFERENCES shops(`id`)
                ) COMMENT='上传记录表'
                """,
                """
                CREATE TABLE IF NOT EXISTS temu_order_income (
                    `id`              INT PRIMARY KEY AUTO_INCREMENT,
                    `upload_id`       INT NOT NULL COMMENT '关联上传记录',
                    `shop_id`         INT NOT NULL COMMENT '关联店铺',
                    `year_month`      VARCHAR(7) NOT NULL,
                    `metric_name`     VARCHAR(50) NOT NULL COMMENT '指标名称 (订单数量/总销售额/退货总额/净回款额 等)',
                    `shop_data`       DECIMAL(18,2) COMMENT '店铺数据',
                    `eu_data`         DECIMAL(18,2) COMMENT '欧区数据',
                    `us_data`         DECIMAL(18,2) COMMENT '美区数据',
                    `global_data`     DECIMAL(18,2) COMMENT '全球区数据',
                    `created_at`      DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (`upload_id`) REFERENCES upload_records(`id`),
                    FOREIGN KEY (`shop_id`) REFERENCES shops(`id`)
                ) COMMENT='Temu 订单收入汇总'
                """,
                """
                CREATE TABLE IF NOT EXISTS temu_sku_metrics (
                    `id`              INT PRIMARY KEY AUTO_INCREMENT,
                    `upload_id`       INT NOT NULL,
                    `shop_id`         INT NOT NULL,
                    `region`          VARCHAR(20) NOT NULL COMMENT '区域 (欧区/美区/全球区/店铺汇总)',
                    `sku_id`          VARCHAR(50) NOT NULL,
                    `sku_no`          VARCHAR(50) NOT NULL,
                    `goods_name`      VARCHAR(200),
                    `sku_attr`        VARCHAR(100),
                    `sales_qty`       INT DEFAULT 0 COMMENT '销售数量',
                    `sales_amount`    DECIMAL(18,2) DEFAULT 0 COMMENT '销售回款总额',
                    `back_orders`     INT DEFAULT 0 COMMENT '回款订单数量',
                    `refund_orders`   INT DEFAULT 0 COMMENT '退款订单数量',
                    `refund_rate`     DECIMAL(5,4) DEFAULT 0 COMMENT '退货率',
                    `comp_orders`     INT DEFAULT 0 COMMENT '赔付订单数量',
                    `comp_rate`       DECIMAL(5,4) DEFAULT 0 COMMENT '赔付率',
                    `refund_amount`   DECIMAL(18,2) DEFAULT 0 COMMENT '退货总额',
                    `refund_ratio`    DECIMAL(5,4) DEFAULT 0 COMMENT '退货金额比例',
                    `comp_amount`     DECIMAL(18,2) DEFAULT 0 COMMENT '赔付金额',
                    `comp_ratio`      DECIMAL(5,4) DEFAULT 0 COMMENT '赔付金额比例',
                    `created_at`      DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (`upload_id`) REFERENCES upload_records(`id`),
                    FOREIGN KEY (`shop_id`) REFERENCES shops(`id`),
                    INDEX idx_sku (`sku_id`, `sku_no`),
                    INDEX idx_region (`region`)
                ) COMMENT='Temu SKU 指标分析'
                """,
                """
                CREATE TABLE IF NOT EXISTS amazon_summary (
                    `id`              INT PRIMARY KEY AUTO_INCREMENT,
                    `upload_id`       INT NOT NULL,
                    `shop_id`         INT NOT NULL,
                    `statement_month` VARCHAR(7) NOT NULL COMMENT '账期月份',
                    `currency`        VARCHAR(10) COMMENT '币种',
                    `income`          DECIMAL(18,2) COMMENT '营业收入',
                    `tax`             DECIMAL(18,2) COMMENT '税费',
                    `transfers`       DECIMAL(18,2) COMMENT '提现金额',
                    `total_expenses`  DECIMAL(18,2) COMMENT '平台扣减总费用',
                    `ad_cost`         DECIMAL(18,2) COMMENT '广告支出',
                    `shipping_cost`   DECIMAL(18,2) COMMENT '运费支出',
                    `storage_cost`    DECIMAL(18,2) COMMENT '仓储费用',
                    `platform_fees`   DECIMAL(18,2) COMMENT '平台费用项目',
                    `created_at`      DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (`upload_id`) REFERENCES upload_records(`id`),
                    FOREIGN KEY (`shop_id`) REFERENCES shops(`id`),
                    INDEX idx_month (`statement_month`)
                ) COMMENT='Amazon 汇总报告'
                """
            ]
            
            for sql in tables:
                cursor.execute(sql)
                
        conn.commit()
        print(f"数据库 {settings.DB_NAME} 初始化成功！")
    except Exception as e:
        conn.rollback()
        print(f"数据库初始化失败: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    init_database()

# Temu/Amazon 数据管理平台 - 实施计划

## 一、项目概述

构建一个基于 Vue 3 + Element Plus 前端 + FastAPI 后端 + MySQL 数据库的 Web 平台，用于：
- 上传并解析 Temu 账务明细（全托管/半托管）
- 上传并解析 Amazon 汇总报告 PDF
- 将解析结果存入 MySQL 并提供查询/下载 Excel 功能

## 二、技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Element Plus + Vite + Axios |
| 后端 | FastAPI + Uvicorn + Pydantic |
| 数据库驱动 | PyMySQL (裸写 SQL + 连接池) |
| 数据库 | MySQL (host: 127.0.0.1:3306, user: shahuwang, pwd: 5201314) |
| 解析库 | pandas, openpyxl, pdfplumber |
| Excel 生成 | openpyxl |

## 三、项目架构

```
amazonAdInvoice/
├── backend/                    # FastAPI 后端
│   ├── main.py                 # 入口 + CORS + 路由注册
│   ├── config.py               # 数据库配置 + 常量
│   ├── db.py                   # PyMySQL 连接池 + 连接管理
│   ├── dao/                    # 数据访问层 (裸写 SQL)
│   │   ├── companies.py        # 公司表 CRUD
│   │   ├── shops.py            # 店铺表 CRUD
│   │   ├── uploads.py          # 上传记录 CRUD
│   │   ├── temu_order_income.py
│   │   ├── temu_sku_metrics.py
│   │   └── amazon_summary.py
│   ├── routers/
│   │   ├── companies.py        # 公司 API
│   │   ├── shops.py            # 店铺 API
│   │   ├── uploads.py          # 文件上传 + 触发解析
│   │   └── reports.py          # 报告查询 + 下载 Excel
│   ├── services/
│   │   ├── parser_temu.py      # 复用 parse_temu_fund.py
│   │   ├── parser_amazon.py    # 复用 parse_summary_report.py
│   │   └── excel_generator.py  # 生成 Excel
│   └── uploads/                # 上传文件临时存储目录
│
├── frontend/                   # Vue 3 + Element Plus
│   ├── src/
│   │   ├── api/
│   │   │   ├── companies.js    # 公司 API
│   │   │   ├── shops.js        # 店铺 API
│   │   │   ├── uploads.js      # 上传 API
│   │   │   └── reports.js      # 报告 API
│   │   ├── views/
│   │   │   ├── UploadView.vue  # 上传页面 (主页面)
│   │   │   └── ReportView.vue  # 报告查询/下载页面
│   │   ├── components/
│   │   │   ├── UploadForm.vue      # 上传表单 (含动态文件区)
│   │   │   ├── ReportTable.vue     # 报告数据表格
│   │   │   ├── DataSelector.vue    # 公司/平台/店铺/年月选择器
│   │   │   └── UploadProgress.vue  # 上传进度/状态
│   │   ├── App.vue
│   │   └── main.js
│   ├── package.json
│   └── vite.config.js
│
├── parse_temu_fund.py          # 现有脚本 (保留)
├── parse_summary_report.py     # 现有脚本 (保留)
├── parse_ad_invoices.py        # 现有脚本 (保留)
└── requirements.txt            # 新增依赖清单
```

## 四、数据库设计

### 4.1 companies (公司表)
```sql
CREATE TABLE companies (
    id          INT PRIMARY KEY AUTO_INCREMENT,
    name        VARCHAR(100) NOT NULL COMMENT '公司名称',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 4.2 shops (店铺表)
```sql
CREATE TABLE shops (
    id          INT PRIMARY KEY AUTO_INCREMENT,
    company_id  INT NOT NULL COMMENT '所属公司',
    name        VARCHAR(100) NOT NULL COMMENT '店铺名称',
    platform    ENUM('temu', 'amazon') NOT NULL COMMENT '平台',
    region      VARCHAR(50) COMMENT '区域 (美国/加拿大/欧区/美区/全球区)',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);
```

### 4.3 upload_records (上传记录表)
```sql
CREATE TABLE upload_records (
    id              INT PRIMARY KEY AUTO_INCREMENT,
    shop_id         INT NOT NULL COMMENT '所属店铺',
    year_month      VARCHAR(7) NOT NULL COMMENT '年月 (YYYY-MM)',
    file_type       VARCHAR(50) NOT NULL COMMENT '文件类型',
    file_path       VARCHAR(500) COMMENT '文件存储路径',
    status          ENUM('pending', 'parsing', 'success', 'failed') DEFAULT 'pending',
    error_msg       TEXT COMMENT '错误信息',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    parsed_at       DATETIME COMMENT '解析完成时间',
    FOREIGN KEY (shop_id) REFERENCES shops(id)
);
```

### 4.4 temu_order_income (Temu 订单收入汇总)
```sql
CREATE TABLE temu_order_income (
    id              INT PRIMARY KEY AUTO_INCREMENT,
    upload_id       INT NOT NULL COMMENT '关联上传记录',
    shop_id         INT NOT NULL COMMENT '关联店铺',
    year_month      VARCHAR(7) NOT NULL,
    metric_name     VARCHAR(50) NOT NULL COMMENT '指标名称 (订单数量/总销售额/退货总额/净回款额 等)',
    shop_data       DECIMAL(18,2) COMMENT '店铺数据',
    eu_data         DECIMAL(18,2) COMMENT '欧区数据',
    us_data         DECIMAL(18,2) COMMENT '美区数据',
    global_data     DECIMAL(18,2) COMMENT '全球区数据',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (upload_id) REFERENCES upload_records(id),
    FOREIGN KEY (shop_id) REFERENCES shops(id)
);
```

### 4.5 temu_sku_metrics (Temu SKU 指标分析)
```sql
CREATE TABLE temu_sku_metrics (
    id              INT PRIMARY KEY AUTO_INCREMENT,
    upload_id       INT NOT NULL,
    shop_id         INT NOT NULL,
    region          VARCHAR(20) NOT NULL COMMENT '区域 (欧区/美区/全球区/店铺汇总)',
    sku_id          VARCHAR(50) NOT NULL,
    sku_no          VARCHAR(50) NOT NULL,
    goods_name      VARCHAR(200),
    sku_attr        VARCHAR(100),
    sales_qty       INT DEFAULT 0 COMMENT '销售数量',
    sales_amount    DECIMAL(18,2) DEFAULT 0 COMMENT '销售回款总额',
    back_orders     INT DEFAULT 0 COMMENT '回款订单数量',
    refund_orders   INT DEFAULT 0 COMMENT '退款订单数量',
    refund_rate     DECIMAL(5,4) DEFAULT 0 COMMENT '退货率',
    comp_orders     INT DEFAULT 0 COMMENT '赔付订单数量',
    comp_rate       DECIMAL(5,4) DEFAULT 0 COMMENT '赔付率',
    refund_amount   DECIMAL(18,2) DEFAULT 0 COMMENT '退货总额',
    refund_ratio    DECIMAL(5,4) DEFAULT 0 COMMENT '退货金额比例',
    comp_amount     DECIMAL(18,2) DEFAULT 0 COMMENT '赔付金额',
    comp_ratio      DECIMAL(5,4) DEFAULT 0 COMMENT '赔付金额比例',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (upload_id) REFERENCES upload_records(id),
    FOREIGN KEY (shop_id) REFERENCES shops(id),
    INDEX idx_sku (sku_id, sku_no),
    INDEX idx_region (region)
);
```

### 4.6 amazon_summary (Amazon 汇总报告)
```sql
CREATE TABLE amazon_summary (
    id              INT PRIMARY KEY AUTO_INCREMENT,
    upload_id       INT NOT NULL,
    shop_id         INT NOT NULL,
    statement_month VARCHAR(7) NOT NULL COMMENT '账期月份',
    currency        VARCHAR(10) COMMENT '币种',
    income          DECIMAL(18,2) COMMENT '营业收入',
    tax             DECIMAL(18,2) COMMENT '税费',
    transfers       DECIMAL(18,2) COMMENT '提现金额',
    total_expenses  DECIMAL(18,2) COMMENT '平台扣减总费用',
    ad_cost         DECIMAL(18,2) COMMENT '广告支出',
    shipping_cost   DECIMAL(18,2) COMMENT '运费支出',
    storage_cost    DECIMAL(18,2) COMMENT '仓储费用',
    platform_fees   DECIMAL(18,2) COMMENT '平台费用项目',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (upload_id) REFERENCES upload_records(id),
    FOREIGN KEY (shop_id) REFERENCES shops(id),
    INDEX idx_month (statement_month)
);
```

## 五、API 接口设计

### 5.1 公司管理

| 方法 | 路径 | 请求体 | 响应 |
|------|------|--------|------|
| GET | `/api/companies` | - | `[{id, name}]` |
| POST | `/api/companies` | `{name}` | `{id, name}` |

### 5.2 店铺管理

| 方法 | 路径 | 请求体/参数 | 响应 |
|------|------|-------------|------|
| GET | `/api/shops` | `?company_id=&platform=` | `[{id, company_id, name, platform, region}]` |
| POST | `/api/shops` | `{company_id, name, platform, region}` | `{id, ...}` |

### 5.3 文件上传

| 方法 | 路径 | 请求体 | 响应 |
|------|------|--------|------|
| POST | `/api/uploads` | multipart/form-data: `shop_id`, `year_month`, `file_type`, `file` | `{id, status, file_path}` |
| POST | `/api/uploads/{id}/parse` | - | `{id, status, message}` |
| GET | `/api/uploads/{id}` | - | `{id, status, error_msg, parsed_at}` |

**上传文件类型映射：**

| 平台 | file_type 值 | 说明 |
|------|-------------|------|
| Temu | `temu_seller_center` | 卖家中心账务明细 |
| Temu | `temu_us` | 美区账务明细 |
| Temu | `temu_eu` | 欧区账务明细 |
| Temu | `temu_global` | 全球区账务明细 |
| Amazon | `amazon_summary` | 汇总报告 PDF |
| Amazon | `amazon_orders` | 订单明细 CSV (可选) |

### 5.4 报告查询

| 方法 | 路径 | 参数 | 响应 |
|------|------|------|------|
| GET | `/api/reports/temu/income` | `?shop_id=&year_month=` | `[{metric_name, shop_data, eu_data, us_data, global_data}]` |
| GET | `/api/reports/temu/sku` | `?shop_id=&year_month=&region=` | `[{sku_id, sku_no, sales_qty, ...}]` |
| GET | `/api/reports/amazon` | `?shop_id=&year_month=` | `[{statement_month, income, ...}]` |
| GET | `/api/reports/download` | `?shop_id=&year_month=&platform=&type=` | Excel 文件流 |

## 六、解析服务封装策略

### 6.1 Temu 解析 (services/parser_temu.py)

**复用目标：** `parse_temu_fund.py`

**封装思路：**
1. 将 `process_region()` 改造为接受 `pd.ExcelFile` 对象而非文件路径
2. 将 `seller_center_data()` 改造为接受 `pd.DataFrame` 而非文件路径
3. 创建 `TemuParser` 类：
   - `parse_region(file_obj, region_name)` → 返回 pivot + metrics
   - `parse_seller_center(file_obj)` → 返回 fees + check
   - `merge_and_calculate(region_results, seller_center_result)` → 返回 shop_data + order_income
4. 入库方法：`save_to_db(upload_id, shop_id, results)`

**关键改造点：**
```python
# 原函数读取文件
xl = pd.ExcelFile(str(input_path))
df = pd.read_excel(xl, sheet_name="交易结算")

# 改造后接受文件对象
def read_settlement_from_obj(file_obj):
    xl = pd.ExcelFile(file_obj)
    # ... 原有逻辑不变
```

### 6.2 Amazon 解析 (services/parser_amazon.py)

**复用目标：** `parse_summary_report.py`

**封装思路：**
1. 将 `parse_pdf()` 改造为接受文件对象
2. 创建 `AmazonParser` 类：
   - `parse_summary(file_obj)` → 返回 dict
   - `save_to_db(upload_id, shop_id, result)`

### 6.3 Excel 生成 (services/excel_generator.py)

**生成目标：**
- Temu：保留原脚本的 3 个 sheet 格式（SKU回款汇总、SKU指标分析、订单收入汇总）
- Amazon：保留原脚本的单 sheet 格式（汇总）

**实现思路：**
1. 从 MySQL 查询数据
2. 用 `openpyxl` 创建 Workbook
3. 按原格式写入数据、设置列宽、数字格式、注释
4. 返回文件流供下载

## 七、前端页面设计

### 7.1 UploadView.vue (上传页面)

**布局：**
```
┌─────────────────────────────────────────┐
│  [公司名称▼]  [平台○Temu ○Amazon]      │
│  [店铺名称▼]  [区域▼]  [年月□□□□-□□]   │
├─────────────────────────────────────────┤
│                                         │
│  【动态文件上传区域】                     │
│                                         │
│  平台=Temu 时显示：                      │
│  ├─ 卖家中心账务明细  [选择文件] [上传] │
│  ├─ 美区账务明细      [选择文件] [上传] │
│  ├─ 欧区账务明细      [选择文件] [上传] │
│  └─ 全球区账务明细    [选择文件] [上传] │
│                                         │
│  平台=Amazon 时显示：                    │
│  ├─ 汇总报告 (PDF)    [选择文件] [上传] │
│  └─ 订单明细 (CSV)    [选择文件] [上传] │
│                                         │
├─────────────────────────────────────────┤
│  [一键解析并入库]                        │
│                                         │
│  状态：                                  │
│  ├─ 卖家中心明细  ✓ 已上传              │
│  ├─ 美区明细      ✓ 已上传              │
│  ├─ 欧区明细      ✓ 已上传              │
│  └─ 全球区明细    ⟳ 解析中...           │
└─────────────────────────────────────────┘
```

**交互逻辑：**
1. 选择公司 → 加载该公司下的店铺列表
2. 选择平台 → 切换文件上传区域
3. 选择店铺 → 自动填充区域
4. 上传文件 → 调用 `/api/uploads`，返回 upload_id
5. 点击"一键解析" → 批量调用 `/api/uploads/{id}/parse`
6. 轮询状态 → 显示进度

### 7.2 ReportView.vue (报告查询页面)

**布局：**
```
┌─────────────────────────────────────────┐
│  [公司名称▼]  [平台▼]  [店铺▼] [年月▼]  │
│  [查询]  [下载Excel]                    │
├─────────────────────────────────────────┤
│                                         │
│  【数据表格】                            │
│                                         │
│  平台=Temu 时显示：                      │
│  Tab1: 订单收入汇总                     │
│  Tab2: SKU指标分析                      │
│                                         │
│  平台=Amazon 时显示：                    │
│  汇总报告表格                            │
│                                         │
└─────────────────────────────────────────┘
```

## 八、执行步骤

### 第一批：基础搭建（后端框架 + 数据库）
1. [ ] 创建 `backend/` 目录结构（含 dao/ 目录）
2. [ ] 编写 `requirements.txt`（fastapi, uvicorn, pymysql, pandas, openpyxl, pdfplumber, python-multipart, dbutils）
3. [ ] 配置 `config.py`（数据库连接串、常量）
4. [ ] 编写 `db.py`（PyMySQL 连接池 + get_connection() / release_connection() 上下文管理器）
5. [ ] 编写建表脚本 `init_db.py`（6 张表，裸 SQL CREATE TABLE）
6. [ ] 运行建表脚本

### 第二批：DAO 层（裸 SQL CRUD）
7. [ ] 编写 `dao/companies.py`（SELECT / INSERT / UPDATE / DELETE 裸 SQL）
8. [ ] 编写 `dao/shops.py`（SELECT / INSERT / UPDATE / DELETE + 级联查询）
9. [ ] 编写 `dao/uploads.py`（上传记录 CRUD）
10. [ ] 编写 `dao/temu_order_income.py`
11. [ ] 编写 `dao/temu_sku_metrics.py`
12. [ ] 编写 `dao/amazon_summary.py`
13. [ ] 测试 DAO（用现有数据验证 SQL 正确性）

### 第三批：Temu 解析服务封装
14. [ ] 分析 `parse_temu_fund.py` 的依赖关系
15. [ ] 提取核心函数到 `services/parser_temu.py`
16. [ ] 改造文件读取逻辑（支持文件对象）
17. [ ] 添加入库方法（调用 DAO 层裸 SQL INSERT）
18. [ ] 编写单元测试（用现有数据测试）

### 第四批：Amazon 解析服务封装
19. [ ] 分析 `parse_summary_report.py`
20. [ ] 提取核心函数到 `services/parser_amazon.py`
21. [ ] 添加入库方法（调用 DAO 层裸 SQL INSERT）

### 第五批：上传 + 解析 API
22. [ ] 编写 `routers/uploads.py`（调用 DAO 层记录上传）
23. [ ] 实现文件保存逻辑
24. [ ] 实现解析触发逻辑（调用 parser + DAO 入库）
25. [ ] 测试端到端流程

### 第六批：报告查询 + Excel 下载 API
26. [ ] 编写 `routers/reports.py`（调用 DAO 层裸 SQL 查询）
27. [ ] 实现查询逻辑
28. [ ] 实现 Excel 生成逻辑
29. [ ] 测试下载功能

### 第七批：前端项目初始化
28. [ ] 创建 Vue 3 项目（vite + element-plus）
29. [ ] 配置 Axios（baseURL, interceptors）
30. [ ] 安装 Element Plus 图标库

### 第八批：前端页面开发
31. [ ] 开发 `DataSelector.vue`（公司/平台/店铺/年月选择器）
32. [ ] 开发 `UploadForm.vue`（动态文件上传区）
33. [ ] 开发 `UploadView.vue`（上传主页面）
34. [ ] 开发 `ReportTable.vue`（数据表格组件）
35. [ ] 开发 `ReportView.vue`（报告查询页面）

### 第九批：联调测试
36. [ ] 前后端联调（上传 → 解析 → 查询 → 下载）
37. [ ] 用 捷湃/呆鸥 数据测试
38. [ ] 修复边界问题（空文件、重复上传、解析失败等）
39. [ ] 性能优化（大文件上传、数据库索引）

### 第十批：部署与文档
40. [ ] 编写 README.md（安装、运行、使用说明）
41. [ ] 配置生产环境（环境变量、日志）
42. [ ] 部署测试

## 九、待确认问题清单

- [ ] **公司/店铺初始化**：是否需要预先插入 捷湃、呆鸥 等公司及其店铺？
- [ ] **Amazon 区域**：Amazon 汇总报告是按账期月份的，是否还需要区域字段？
- [ ] **文件保留策略**：上传的原始文件是否长期保留？保留多久？
- [ ] **重复上传处理**：同一店铺同一月份重复上传时，是覆盖旧数据还是拒绝？
- [ ] **权限控制**：是否需要用户登录系统？还是内部工具直接使用？
- [ ] **Amazon 订单明细**：CSV 格式未定，是否需要先提供样例文件？
- [ ] **数据展示粒度**：Temu 的 SKU 级数据量很大，是否需要分页？
- [ ] **并发处理**：是否支持同时解析多个上传文件？

## 十、风险与应对措施

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| parse_temu_fund.py 改造复杂 | 延期 | 先复用 main() 逻辑，逐步拆解 |
| 大文件上传超时 | 用户体验差 | 使用分片上传或后台异步任务 |
| 数据库连接数耗尽 | 系统崩溃 | 使用连接池，限制并发 |
| 解析结果与现有脚本不一致 | 数据错误 | 对比测试，确保输出一致 |
| 前端打包体积过大 | 加载慢 | 按需引入 Element Plus 组件 |

## 十一、时间预估

| 批次 | 内容 | 预估工时 |
|------|------|---------|
| 第一批 | 基础搭建（含连接池） | 1.5h |
| 第二批 | DAO 层（6张表裸 SQL） | 2h |
| 第三批 | Temu 解析封装 | 2.5h |
| 第四批 | Amazon 解析封装 | 1h |
| 第五批 | 上传 + 解析 API | 1.5h |
| 第六批 | 报告查询 + 下载 | 1.5h |
| 第七批 | 前端初始化 | 0.5h |
| 第八批 | 前端页面开发 | 2.5h |
| 第九批 | 联调测试 | 1.5h |
| 第十批 | 部署文档 | 1h |
| **总计** | | **~15.5h** |

---

*本计划为初步方案，将在需求确认后细化调整。*

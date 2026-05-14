# Temu/Amazon 数据管理平台

基于 Vue 3 + Element Plus + FastAPI + MySQL 的 Web 平台，用于上传、解析和查询 Temu/Amazon 财务数据。

## 功能特性

- **Temu 数据管理**
  - 上传并解析全托管/半托管账务明细（欧区、美区、全球区）
  - 上传卖家中心账务明细
  - 自动生成 SKU 回款汇总、SKU 指标分析、订单收入汇总
  - 支持对账检查

- **Amazon 数据管理**
  - 上传并解析月度汇总报告 PDF
  - 提取营业收入、税费、广告支出、运费、仓储费用等关键指标
  - 自动验证费用明细

- **数据查询与导出**
  - 按公司/平台/店铺/年月查询历史数据
  - 支持 Excel 下载

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Element Plus + Vite + Axios |
| 后端 | FastAPI + PyMySQL (裸写 SQL) |
| 数据库 | MySQL |
| 解析库 | pandas, openpyxl, pdfplumber |

## 快速开始

### 1. 环境准备

```bash
# Python 3.12+
python -m venv py3env
source py3env/bin/activate

# Node.js 18+
# 确保已安装 npm
```

### 2. 安装依赖

```bash
# 后端依赖
pip install -r requirements.txt

# 前端依赖
cd frontend
npm install
```

### 3. 数据库配置

编辑 `backend/config.py` 修改数据库连接信息：

```python
DB_HOST = "127.0.0.1"
DB_PORT = 3306
DB_USER = "shahuwang"
DB_PASSWORD = "5201314"
DB_NAME = "amazon_ad_invoice"
```

### 4. 初始化数据库

```bash
python backend/init_db.py
```

### 5. 启动服务

```bash
# 启动后端 (端口 8000)
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

# 启动前端 (端口 5173)
cd frontend
npm run dev
```

### 6. 访问系统

打开浏览器访问 http://localhost:5173

## 项目结构

```
amazonAdInvoice/
├── backend/                    # FastAPI 后端
│   ├── main.py                 # 入口 + 路由注册
│   ├── config.py               # 数据库配置
│   ├── db.py                   # PyMySQL 连接池
│   ├── dao/                    # 数据访问层 (裸写 SQL)
│   ├── routers/                # API 路由
│   ├── services/               # 解析服务
│   └── uploads/                # 上传文件存储
├── frontend/                   # Vue 3 前端
│   ├── src/
│   │   ├── api/                # API 接口
│   │   ├── views/              # 页面
│   │   └── components/         # 组件
│   └── package.json
├── parse_temu_fund.py          # Temu 解析脚本（原始）
├── parse_summary_report.py     # Amazon 解析脚本（原始）
└── requirements.txt
```

## 使用说明

### 数据上传

1. 选择公司、平台、店铺和年月
2. 根据平台类型上传对应的文件：
   - **Temu**: 需要上传卖家中心账务明细 + 欧区/美区/全球区账务明细
   - **Amazon**: 上传汇总报告 PDF
3. 点击"一键上传并解析"

### 报告查询

1. 选择查询条件（公司/平台/店铺/年月）
2. 点击"查询"查看数据
3. 点击"下载Excel"导出报告

## API 接口

### 公司管理
- `GET /api/companies` - 获取公司列表
- `POST /api/companies` - 创建公司

### 店铺管理
- `GET /api/shops` - 获取店铺列表
- `POST /api/shops` - 创建店铺

### 文件上传
- `POST /api/uploads` - 上传文件
- `POST /api/uploads/{id}/parse` - 触发解析
- `POST /api/uploads/batch-parse` - 批量解析

### 报告查询
- `GET /api/reports/temu/income` - Temu 订单收入
- `GET /api/reports/temu/sku` - Temu SKU 指标
- `GET /api/reports/amazon` - Amazon 汇总
- `GET /api/reports/download` - 下载 Excel

## 测试

```bash
# 运行端到端测试
python backend/test_e2e.py
```

## 注意事项

1. 首次使用前需要先创建公司和店铺
2. Temu 解析需要同时上传所有区域文件才能获得完整报告
3. 上传的原始文件会保存在 `backend/uploads/` 目录
4. 数据库使用连接池管理，默认最大连接数为 10

## 待完善功能

- [ ] 用户认证与权限控制
- [ ] 数据分页展示
- [ ] 重复上传处理（覆盖/拒绝）
- [ ] 异步任务队列（Celery）
- [ ] 日志系统
- [ ] 生产环境部署配置

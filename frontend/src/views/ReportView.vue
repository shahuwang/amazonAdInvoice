<template>
  <div class="report-view">
    <h2>数据查询</h2>
    
    <!-- 查询条件 -->
    <el-form :model="queryForm" label-width="120px" class="query-form">
      <el-row :gutter="20">
        <el-col :span="5">
          <el-form-item label="公司">
            <el-select v-model="queryForm.companyId" placeholder="选择公司" @change="onCompanyChange">
              <el-option
                v-for="item in companies"
                :key="item.id"
                :label="item.name"
                :value="item.id"
              />
            </el-select>
          </el-form-item>
        </el-col>
        
        <el-col :span="5">
          <el-form-item label="平台">
            <el-select v-model="queryForm.platform" placeholder="选择平台" @change="onPlatformChange">
              <el-option label="Temu" value="temu" />
              <el-option label="Amazon" value="amazon" />
            </el-select>
          </el-form-item>
        </el-col>
        
        <el-col :span="5">
          <el-form-item label="店铺">
            <el-select 
              v-model="queryForm.shopId" 
              placeholder="请先选择公司和平台"
              :disabled="!queryForm.companyId || !queryForm.platform"
            >
              <el-option
                v-for="item in filteredShops"
                :key="item.id"
                :label="item.name"
                :value="item.id"
              />
            </el-select>
          </el-form-item>
        </el-col>
        
        <el-col :span="5">
          <el-form-item label="年月">
            <el-date-picker
              v-model="queryForm.yearMonth"
              type="month"
              placeholder="选择年月"
              value-format="YYYY-MM"
            />
          </el-form-item>
        </el-col>
        
        <el-col :span="4">
          <el-button type="primary" @click="queryData" :loading="loading">
            <el-icon><Search /></el-icon> 查询
          </el-button>
          <el-button type="success" @click="downloadExcel" :loading="downloading">
            <el-icon><Download /></el-icon> 下载Excel
          </el-button>
        </el-col>
      </el-row>
    </el-form>
    
    <!-- 数据展示 -->
    <div v-if="queryForm.platform === 'temu' && hasData" class="data-area">
      <el-tabs v-model="activeTab">
        <!-- 订单收入汇总 -->
        <el-tab-pane label="订单收入汇总" name="income">
          <el-table :data="incomeData" border stripe style="width: 100%">
            <el-table-column prop="metric_name" label="指标名称" width="180" />
            <el-table-column prop="shop_data" label="店铺数据" align="right">
              <template #default="scope">
                {{ formatNumber(scope.row.shop_data) }}
              </template>
            </el-table-column>
            <el-table-column prop="eu_data" label="欧区数据" align="right">
              <template #default="scope">
                {{ formatNumber(scope.row.eu_data) }}
              </template>
            </el-table-column>
            <el-table-column prop="us_data" label="美区数据" align="right">
              <template #default="scope">
                {{ formatNumber(scope.row.us_data) }}
              </template>
            </el-table-column>
            <el-table-column prop="global_data" label="全球区数据" align="right">
              <template #default="scope">
                {{ formatNumber(scope.row.global_data) }}
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        
        <!-- SKU指标分析 -->
        <el-tab-pane label="SKU指标分析" name="sku">
          <el-table :data="skuData" border stripe style="width: 100%" height="500">
            <el-table-column prop="sku_id" label="SKU ID" width="120" />
            <el-table-column prop="sku_no" label="SKU货号" width="120" />
            <el-table-column prop="goods_name" label="货品名称" width="200" show-overflow-tooltip />
            <el-table-column prop="sales_qty" label="销售数量" align="right" />
            <el-table-column prop="sales_amount" label="销售回款" align="right">
              <template #default="scope">
                {{ formatNumber(scope.row.sales_amount) }}
              </template>
            </el-table-column>
            <el-table-column prop="refund_orders" label="退款订单" align="right" />
            <el-table-column prop="refund_rate" label="退货率" align="right">
              <template #default="scope">
                {{ formatPercent(scope.row.refund_rate) }}
              </template>
            </el-table-column>
            <el-table-column prop="comp_amount" label="赔付金额" align="right">
              <template #default="scope">
                {{ formatNumber(scope.row.comp_amount) }}
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </div>
    
    <!-- Amazon 数据展示 -->
    <div v-if="queryForm.platform === 'amazon' && amazonData" class="data-area">
      <el-descriptions title="Amazon 汇总报告" :column="2" border
        v-if="amazonData"
      >
        <el-descriptions-item label="账期月份">{{ amazonData.statement_month }}</el-descriptions-item>
        <el-descriptions-item label="币种">{{ amazonData.currency }}</el-descriptions-item>
        <el-descriptions-item label="营业收入">{{ formatNumber(amazonData.income) }}</el-descriptions-item>
        <el-descriptions-item label="税费">{{ formatNumber(amazonData.tax) }}</el-descriptions-item>
        <el-descriptions-item label="提现金额">{{ formatNumber(amazonData.transfers) }}</el-descriptions-item>
        <el-descriptions-item label="平台扣减总费用">{{ formatNumber(amazonData.total_expenses) }}</el-descriptions-item>
        <el-descriptions-item label="广告支出">{{ formatNumber(amazonData.ad_cost) }}</el-descriptions-item>
        <el-descriptions-item label="运费支出">{{ formatNumber(amazonData.shipping_cost) }}</el-descriptions-item>
        <el-descriptions-item label="仓储费用">{{ formatNumber(amazonData.storage_cost) }}</el-descriptions-item>
        <el-descriptions-item label="平台费用项目">{{ formatNumber(amazonData.platform_fees) }}</el-descriptions-item>
      </el-descriptions>
    </div>
    
    <div v-if="!hasData && !amazonData && queried" class="empty-tip">
      未找到数据
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { companyApi, shopApi, reportApi } from '../api'

// 查询表单
const queryForm = reactive({
  companyId: null,
  platform: 'temu',
  shopId: null,
  yearMonth: ''
})

// 数据
const companies = ref([])
const shops = ref([])
const loading = ref(false)
const downloading = ref(false)
const queried = ref(false)
const activeTab = ref('income')

// 查询结果
const incomeData = ref([])
const skuData = ref([])
const amazonData = ref(null)

// 计算属性
const filteredShops = computed(() => {
  return shops.value.filter(s => {
    if (queryForm.companyId && s.company_id !== queryForm.companyId) return false
    if (queryForm.platform && s.platform !== queryForm.platform) return false
    return true
  })
})

const hasData = computed(() => {
  return incomeData.value.length > 0 || skuData.value.length > 0
})

// 方法
const loadCompanies = async () => {
  try {
    companies.value = await companyApi.getAll()
  } catch (error) {
    console.error('加载公司失败:', error)
  }
}

const loadShops = async () => {
  try {
    shops.value = await shopApi.getAll()
  } catch (error) {
    console.error('加载店铺失败:', error)
  }
}

const onCompanyChange = () => {
  queryForm.shopId = null
}

const onPlatformChange = () => {
  queryForm.shopId = null
  incomeData.value = []
  skuData.value = []
  amazonData.value = null
}

const queryData = async () => {
  if (!queryForm.shopId || !queryForm.yearMonth) {
    ElMessage.warning('请选择店铺和年月')
    return
  }
  
  loading.value = true
  queried.value = true
  
  try {
    if (queryForm.platform === 'temu') {
      const [income, sku] = await Promise.all([
        reportApi.getTemuIncome({
          shop_id: queryForm.shopId,
          year_month: queryForm.yearMonth
        }),
        reportApi.getTemuSku({
          shop_id: queryForm.shopId,
          year_month: queryForm.yearMonth
        })
      ])
      incomeData.value = income || []
      skuData.value = sku || []
    } else if (queryForm.platform === 'amazon') {
      const result = await reportApi.getAmazonSummary({
        shop_id: queryForm.shopId,
        year_month: queryForm.yearMonth
      })
      amazonData.value = result
    }
  } catch (error) {
    console.error('查询失败:', error)
    ElMessage.error('查询失败')
  } finally {
    loading.value = false
  }
}

const downloadExcel = async () => {
  if (!queryForm.shopId || !queryForm.yearMonth) {
    ElMessage.warning('请选择店铺和年月')
    return
  }
  
  downloading.value = true
  
  try {
    const blob = await reportApi.downloadExcel({
      shop_id: queryForm.shopId,
      year_month: queryForm.yearMonth,
      platform: queryForm.platform
    })
    
    // 创建下载链接
    const url = window.URL.createObjectURL(new Blob([blob]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `${queryForm.platform}_report_${queryForm.yearMonth}.xlsx`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    
    ElMessage.success('下载成功')
  } catch (error) {
    console.error('下载失败:', error)
    ElMessage.error('下载失败')
  } finally {
    downloading.value = false
  }
}

const formatNumber = (val) => {
  if (val === null || val === undefined) return '-'
  return Number(val).toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })
}

const formatPercent = (val) => {
  if (val === null || val === undefined) return '-'
  return (Number(val) * 100).toFixed(2) + '%'
}

onMounted(() => {
  loadCompanies()
  loadShops()
})
</script>

<style scoped>
.report-view {
  padding: 20px;
}

.query-form {
  background: #f5f7fa;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.data-area {
  margin-top: 20px;
}

.empty-tip {
  text-align: center;
  color: #909399;
  padding: 40px;
  font-size: 14px;
}
</style>

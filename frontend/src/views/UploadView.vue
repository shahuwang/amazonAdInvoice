<template>
  <div class="upload-view">
    <h2>月度数据上传</h2>
    
    <!-- 选择器 -->
    <el-form :model="form" label-width="120px" class="selector-form">
      <el-row :gutter="20">
        <el-col :span="6">
          <el-form-item label="公司">
            <el-select v-model="form.companyId" placeholder="选择公司" @change="onCompanyChange">
              <el-option
                v-for="item in companies"
                :key="item.id"
                :label="item.name"
                :value="item.id"
              />
            </el-select>
          </el-form-item>
        </el-col>
        
        <el-col :span="6">
          <el-form-item label="平台">
            <el-select v-model="form.platform" placeholder="选择平台" @change="onPlatformChange">
              <el-option label="Temu" value="temu" />
              <el-option label="Amazon" value="amazon" />
            </el-select>
          </el-form-item>
        </el-col>
        
        <el-col :span="6">
          <el-form-item label="店铺">
            <el-select 
              v-model="form.shopId" 
              placeholder="请先选择公司和平台"
              :disabled="!form.companyId || !form.platform"
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
        
        <el-col :span="6">
          <el-form-item label="年月">
            <el-date-picker
              v-model="form.yearMonth"
              type="month"
              placeholder="选择年月"
              value-format="YYYY-MM"
            />
          </el-form-item>
        </el-col>
      </el-row>
    </el-form>
    
    <!-- 文件上传区域 -->
    <div v-if="form.shopId" class="upload-area">
      <!-- Temu 上传 -->
      <template v-if="form.platform === 'temu'">
        <div class="file-list">
          <div v-for="item in temuFileTypes" :key="item.type" class="file-row">
            <div class="file-label">{{ item.label }}</div>
            <div class="file-upload">
              <input
                type="file"
                style="display: none"
                :accept="getAcceptType(item.type)"
                @change="(e) => handleNativeFileChange(e, item.type)"
                :ref="el => { if (el) fileInputs[item.type] = el }"
              />
              <el-button type="primary" size="small" @click="triggerFileInput(item.type)">
                选择文件
              </el-button>
            </div>
            <div class="file-status">
              <el-tag v-if="uploadStatus[item.type]" :type="uploadStatus[item.type].type" size="small">
                {{ uploadStatus[item.type].message }}
              </el-tag>
              <span v-else class="status-placeholder">未选择文件</span>
            </div>
          </div>
        </div>
        
        <div class="action-bar">
          <el-button type="success" size="large" @click="batchUploadTemu" :loading="uploading">
            <el-icon><Upload /></el-icon>
            一键上传并解析
          </el-button>
        </div>
      </template>
      
      <!-- Amazon 上传 -->
      <template v-if="form.platform === 'amazon'">
        <div class="file-list">
          <div v-for="item in amazonFileTypes" :key="item.type" class="file-row">
            <div class="file-label">{{ item.label }}</div>
            <div class="file-upload">
              <input
                type="file"
                style="display: none"
                :accept="getAcceptType(item.type)"
                @change="(e) => handleNativeFileChange(e, item.type)"
                :ref="el => { if (el) fileInputs[item.type] = el }"
              />
              <el-button type="primary" size="small" @click="triggerFileInput(item.type)">
                选择文件
              </el-button>
            </div>
            <div class="file-status">
              <el-tag v-if="uploadStatus[item.type]" :type="uploadStatus[item.type].type" size="small">
                {{ uploadStatus[item.type].message }}
              </el-tag>
              <span v-else class="status-placeholder">未选择文件</span>
            </div>
          </div>
        </div>
        
        <div class="action-bar">
          <el-button type="success" size="large" @click="uploadAmazon" :loading="uploading">
            <el-icon><Upload /></el-icon>
            上传并解析
          </el-button>
        </div>
      </template>
    </div>
    
    <div v-else class="tip">
      请先选择公司、平台和店铺
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { companyApi, shopApi, uploadApi } from '../api'

// 获取上个月（YYYY-MM）
const getLastMonth = () => {
  const now = new Date()
  now.setMonth(now.getMonth() - 1)
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  return `${year}-${month}`
}

// 表单数据
const form = reactive({
  companyId: null,
  platform: 'temu',
  shopId: null,
  yearMonth: getLastMonth()
})

// 数据列表
const companies = ref([])
const shops = ref([])
const uploading = ref(false)
const selectedFiles = reactive({})
const uploadStatus = reactive({})
const uploadedIds = reactive({})
const fileInputs = reactive({})

// 文件类型配置
const temuFileTypes = [
  { type: 'temu_seller_center', label: '卖家中心账务明细' },
  { type: 'temu_eu', label: '欧区账务明细' },
  { type: 'temu_us', label: '美区账务明细' },
  { type: 'temu_global', label: '全球区账务明细' }
]

const amazonFileTypes = [
  { type: 'amazon_summary', label: '汇总报告 (PDF)' },
  { type: 'amazon_orders', label: '订单明细 (CSV，可选)' }
]

// 计算属性
const filteredShops = computed(() => {
  return shops.value.filter(s => {
    if (form.companyId && s.company_id !== form.companyId) return false
    if (form.platform && s.platform !== form.platform) return false
    return true
  })
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
  form.shopId = null
}

const onPlatformChange = () => {
  form.shopId = null
}

const getAcceptType = (type) => {
  if (type.startsWith('amazon')) {
    if (type === 'amazon_summary') return '.pdf'
    return '.csv'
  }
  return '.xlsx,.xls'
}

const triggerFileInput = (type) => {
  const input = fileInputs[type]
  if (input) {
    input.value = ''
    input.click()
  }
}

const handleNativeFileChange = (event, type) => {
  const file = event.target.files[0]
  if (file) {
    selectedFiles[type] = file
    uploadStatus[type] = { type: 'info', message: `已选择: ${file.name}` }
  }
}

const uploadSingleFile = async (file, fileType) => {
  const formData = new FormData()
  formData.append('shop_id', form.shopId)
  formData.append('year_month', form.yearMonth)
  formData.append('file_type', fileType)
  formData.append('file', file)
  
  const result = await uploadApi.upload(formData)
  return result.id
}

const batchUploadTemu = async () => {
  if (!form.shopId) {
    ElMessage.warning('请先选择店铺')
    return
  }
  if (!form.yearMonth) {
    ElMessage.warning('请先选择年月')
    return
  }
  
  uploading.value = true
  const uploadIds = []
  
  try {
    // 上传所有文件
    for (const item of temuFileTypes) {
      const file = selectedFiles[item.type]
      if (file) {
        const id = await uploadSingleFile(file, item.type)
        uploadIds.push(id)
        uploadedIds[item.type] = id
        uploadStatus[item.type] = { type: 'success', message: '上传成功' }
      }
    }
    
    if (uploadIds.length === 0) {
      ElMessage.warning('请至少选择一个文件')
      return
    }
    
    // 批量解析
    ElMessage.info('开始解析...')
    const result = await uploadApi.batchParse(uploadIds)
    
    const allSuccess = result.results.every(r => r.status === 'success')
    if (allSuccess) {
      ElMessage.success('解析完成！')
    } else {
      const errors = result.results.filter(r => r.status === 'failed')
      ElMessage.error(`解析失败: ${errors.map(e => e.error).join(', ')}`)
    }
  } catch (error) {
    console.error('上传失败:', error)
    ElMessage.error('上传或解析失败')
  } finally {
    uploading.value = false
  }
}

const uploadAmazon = async () => {
  if (!form.shopId) {
    ElMessage.warning('请先选择店铺')
    return
  }
  if (!form.yearMonth) {
    ElMessage.warning('请先选择年月')
    return
  }
  
  uploading.value = true
  
  try {
    const file = selectedFiles['amazon_summary']
    if (!file) {
      ElMessage.warning('请选择汇总报告 PDF')
      return
    }
    
    const uploadId = await uploadSingleFile(file, 'amazon_summary')
    uploadStatus['amazon_summary'] = { type: 'success', message: '上传成功' }
    
    // 解析
    ElMessage.info('开始解析...')
    await uploadApi.parse(uploadId)
    
    ElMessage.success('解析完成！')
  } catch (error) {
    console.error('上传失败:', error)
    ElMessage.error('上传或解析失败')
  } finally {
    uploading.value = false
  }
}

onMounted(() => {
  loadCompanies()
  loadShops()
})
</script>

<style scoped>
.upload-view {
  padding: 20px;
}

.selector-form {
  background: #f5f7fa;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.upload-area {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.file-list {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
}

.file-row {
  display: flex;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #ebeef5;
  transition: background-color 0.2s;
}

.file-row:last-child {
  border-bottom: none;
}

.file-row:hover {
  background-color: #f5f7fa;
}

.file-label {
  width: 200px;
  font-weight: 500;
  color: #303133;
  font-size: 14px;
}

.file-upload {
  width: 120px;
}

.file-status {
  flex: 1;
  padding-left: 20px;
}

.status-placeholder {
  color: #c0c4cc;
  font-size: 13px;
}

.action-bar {
  display: flex;
  justify-content: center;
  padding: 20px 0;
}

.tip {
  text-align: center;
  color: #909399;
  padding: 40px;
  font-size: 14px;
}
</style>

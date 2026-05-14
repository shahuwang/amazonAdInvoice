import api from './request'

export const companyApi = {
  getAll: () => api.get('/companies/'),
  create: (name) => api.post('/companies/', { name }),
  getById: (id) => api.get(`/companies/${id}`)
}

export const shopApi = {
  getAll: (params = {}) => api.get('/shops/', { params }),
  create: (data) => api.post('/shops/', data),
  getById: (id) => api.get(`/shops/${id}`)
}

export const uploadApi = {
  upload: (formData) => api.post('/uploads/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  parse: (id) => api.post(`/uploads/${id}/parse`),
  batchParse: (uploadIds) => api.post('/uploads/batch-parse', {upload_ids: uploadIds}),
  getById: (id) => api.get(`/uploads/${id}`)
}

export const reportApi = {
  getTemuIncome: (params) => api.get('/reports/temu/income', { params }),
  getTemuSku: (params) => api.get('/reports/temu/sku', { params }),
  getAmazonSummary: (params) => api.get('/reports/amazon', { params }),
  downloadExcel: (params) => api.get('/reports/download', { 
    params,
    responseType: 'blob'
  })
}

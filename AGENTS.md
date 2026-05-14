# Agent 注意事项

## Vue 3 + Element Plus 前端开发

### 1. 禁止在 v-for 中使用函数式 ref 绑定
**问题：** 在 `v-for` 中使用 `:ref="el => setRef(el, item)"` 会导致无限重渲染循环。

**原因：** Vue 3 的函数式 ref 在每次组件更新时都会重新执行，如果函数内部修改了响应式状态（reactive/ref），会再次触发更新，形成死循环。

**错误示例：**
```vue
<!-- 危险！会导致页面卡死 -->
<div v-for="item in list" :key="item.id">
  <el-upload :ref="el => setUploadRef(el, item.type)">
</div>
```

**正确做法：**
- 方案 A：使用原生 HTML `<input type="file">` + `ref` 替代 `el-upload`
- 方案 B：如果必须用 `el-upload`，不要在 v-for 中使用函数式 ref，改用静态 ref 或其他方式管理

### 2. el-upload 组件的文件状态管理
**问题：** `el-upload` 的 `on-change` 回调在 `limit=1` 时，选择新文件会先触发旧文件的 `status='removed'` 事件，可能导致状态覆盖或混乱。

**原因：** Element Plus 内部会先移除旧文件再添加新文件，会触发两次回调。

**正确做法：**
- 方案 A（推荐）：使用原生 `<input type="file">` 替代 `el-upload`，避免组件内部状态管理问题
- 方案 B：如果必须用 `el-upload`，在 `on-change` 中判断 `uploadFile.status === 'ready'` 只处理新文件，不处理 removed 事件

### 3. 原生文件上传实现规范
使用原生 `<input type="file">` 的标准模式：
```vue
<template>
  <input
    type="file"
    style="display: none"
    accept=".xlsx,.xls"
    @change="handleFileChange"
    ref="fileInput"
  />
  <el-button @click="triggerUpload">选择文件</el-button>
</template>

<script setup>
const fileInput = ref(null)

const triggerUpload = () => {
  fileInput.value.value = ''  // 清空，确保能重复选择同一个文件
  fileInput.value.click()
}

const handleFileChange = (event) => {
  const file = event.target.files[0]
  if (file) {
    // 处理文件
  }
}
</script>
```

## FastAPI 后端开发

### 1. datetime 字段序列化
**问题：** PyMySQL 查询返回的 `datetime` 对象无法直接被 FastAPI 的 Pydantic 模型序列化为 JSON。

**正确做法：** 在返回数据前手动转换 datetime 字段：
```python
def _format_datetime(data):
    if data and data.get('created_at'):
        dt = data['created_at']
        data['created_at'] = dt.isoformat() if hasattr(dt, 'isoformat') else str(dt)
    return data
```

### 2. API 请求体格式
**问题：** FastAPI 的 `list` 类型参数在 POST 请求中需要特定的 JSON 格式。

**正确做法：** 使用 `dict` 类型接收请求体，内部提取字段：
```python
@router.post("/batch-parse")
async def batch_parse(body: dict):
    upload_ids = body.get('upload_ids', [])
```

## 项目规范

### 1. 文件路径处理
- 始终使用 `Path(__file__).parent` 而不是硬编码相对路径
- 跨平台使用 `pathlib.Path` 而非字符串拼接

### 2. 数据库初始化
- 测试数据和生产数据要严格区分
- 初始化脚本应幂等（可重复执行）
- 公司/店铺等基础数据应通过 `init_data.py` 统一管理

### 3. Vue Router 页面缓存
**问题：** 切换路由页面后，原页面的数据会丢失（组件被销毁重建）。

**正确做法：** Vue 3 中 `<keep-alive>` 需配合 `v-slot` 语法使用，直接包裹 `<router-view>` 不生效：
```vue
<router-view v-slot="{ Component }">
  <keep-alive>
    <component :is="Component" />
  </keep-alive>
</router-view>
```

### 4. 代码审查清单
修改前端上传组件前检查：
- [ ] 是否使用了函数式 ref 绑定？
- [ ] 是否在 v-for 中使用了 ref？
- [ ] 文件状态管理是否清晰？
- [ ] 重复选择文件是否能正常更新？
- [ ] 路由页面是否需要 keep-alive 缓存？

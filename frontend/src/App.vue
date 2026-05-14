<template>
  <div id="app">
    <el-container class="layout-container">
      <!-- 侧边栏 -->
      <el-aside width="220px" class="sidebar">
        <div class="logo">
          <h2>Temu/Amazon<br><small>数据管理平台</small></h2>
        </div>
        
        <el-menu
          :default-active="activeMenu"
          class="sidebar-menu"
          background-color="#304156"
          text-color="#bfcbd9"
          active-text-color="#409eff"
          router
          @select="handleSelect"
        >
          <el-menu-item index="/upload">
            <el-icon><Upload /></el-icon>
            <span>月度数据上传</span>
          </el-menu-item>
          
          <el-menu-item index="/report">
            <el-icon><Document /></el-icon>
            <span>数据查询</span>
          </el-menu-item>
        </el-menu>
      </el-aside>
      
      <!-- 主内容区 -->
      <el-container>
        <el-header class="main-header">
          <div class="breadcrumb">
            {{ pageTitle }}
          </div>
        </el-header>
        
        <el-main class="main-content">
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const activeMenu = ref('/upload')

const pageTitle = computed(() => {
  const titles = {
    '/upload': '月度数据上传',
    '/report': '数据查询'
  }
  return titles[route.path] || ''
})

watch(() => route.path, (newPath) => {
  activeMenu.value = newPath
}, { immediate: true })

const handleSelect = (index) => {
  activeMenu.value = index
}
</script>

<style>
#app {
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB',
    'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
  height: 100vh;
}

.layout-container {
  height: 100vh;
}

/* 侧边栏 */
.sidebar {
  background-color: #304156;
  color: #bfcbd9;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #263445;
  border-bottom: 1px solid #1f2d3d;
}

.logo h2 {
  margin: 0;
  color: #fff;
  font-size: 16px;
  text-align: center;
  line-height: 1.4;
}

.logo h2 small {
  font-size: 12px;
  color: #bfcbd9;
  font-weight: normal;
}

.sidebar-menu {
  border-right: none;
}

.sidebar-menu .el-menu-item {
  font-size: 14px;
}

.sidebar-menu .el-menu-item .el-icon {
  margin-right: 8px;
}

/* 主内容区 */
.main-header {
  background-color: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  padding: 0 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.breadcrumb {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
}

.main-content {
  background-color: #f0f2f5;
  padding: 20px;
  overflow-y: auto;
}

/* 全局样式重置 */
body {
  margin: 0;
  padding: 0;
}
</style>

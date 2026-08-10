// Taro 环境变量必须带 TARO_APP_ 前缀；本地开发默认连后端 FastAPI
export const BASE: string =
  process.env.TARO_APP_API_BASE || 'http://127.0.0.1:8000'

// 订阅消息模板 ID（与后端 .env 的 WECHAT_TEMPLATE_DUE 保持一致）
export const TEMPLATE_DUE: string =
  process.env.TARO_APP_TEMPLATE_DUE || ''

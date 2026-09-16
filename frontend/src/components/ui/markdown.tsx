import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { cn } from '../../lib/cn'

/**
 * 统一的 Markdown 渲染入口。
 *
 * 背景：AI 产出（运行记录、工作流步骤输出、副驾回复、知识库回答）本身就是
 * Markdown 文本，历史上直接塞进 <pre> 或 whitespace-pre-wrap 的 div，
 * 结果 `# 标题`、`**加粗**`、`---` 全部以源码形式裸露给用户。
 * 凡是要展示 AI 正文的地方，一律走这个组件。
 *
 * 注意：react-markdown v10 移除了 className prop，
 * 自定义样式只能挂在 wrapper 上（见 index.css 的 .md-body / .md-body-compact）。
 *
 * @param compact 面板 / 运行记录等密集区域用紧凑排版（12px、标题与间距压紧）；
 *                文档预览场景（DocEditor）保持默认的常规排版（13px）。
 */
export function Markdown({
  children,
  compact = false,
  className,
}: {
  children: string
  compact?: boolean
  className?: string
}) {
  return (
    <div className={cn('md-body', compact && 'md-body-compact', className)}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
    </div>
  )
}

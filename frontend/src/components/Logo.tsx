import { cn } from '../lib/cn'

export function Logo({ size = 26, className }: { size?: number; className?: string }) {
  return (
    <div
      className={cn(
        'flex shrink-0 items-center justify-center rounded-[7px] bg-gradient-to-br from-gold to-gold-deep shadow-gold',
        className,
      )}
      style={{ width: size, height: size }}
    >
      <svg width={size * 0.58} height={size * 0.58} viewBox="0 0 24 24" fill="none">
        <path d="M12 2 22 12 12 22 2 12Z" stroke="#1A1406" strokeWidth="2.2" strokeLinejoin="round" />
        <circle cx="12" cy="12" r="2.2" fill="#1A1406" />
      </svg>
    </div>
  )
}

export function Brand() {
  return (
    <div className="flex items-center gap-2.5">
      <Logo />
      <span className="text-[14px] font-semibold tracking-tight text-ink">
        Veya<span className="text-gold">Work</span> 雅秩
      </span>
    </div>
  )
}

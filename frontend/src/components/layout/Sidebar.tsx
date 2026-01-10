import { NavLink } from 'react-router-dom'
import { BarChart3, Eye, Gamepad2 } from 'lucide-react'
import { cn } from '@/lib/utils'

const navItems = [
  { to: '/dashboard', icon: BarChart3, label: 'Dashboard' },
  { to: '/watch', icon: Eye, label: 'Watch Game' },
]

export function Sidebar() {
  return (
    <aside className="hidden lg:flex w-64 flex-col border-r bg-card">
      <div className="flex h-14 items-center border-b px-6">
        <Gamepad2 className="h-6 w-6 text-primary mr-2" />
        <span className="font-semibold text-lg">Monopoly</span>
      </div>

      <nav className="flex-1 space-y-1 p-4">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-muted hover:text-foreground'
              )
            }
          >
            <item.icon className="h-4 w-4" />
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t p-4">
        <p className="text-xs text-muted-foreground">
          Monopoly Analytics v1.0
        </p>
      </div>
    </aside>
  )
}

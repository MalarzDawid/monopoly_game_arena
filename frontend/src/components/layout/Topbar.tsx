import { NavLink, useLocation } from 'react-router-dom'
import { BarChart3, Eye, Gamepad2, Menu } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { useState } from 'react'

const navItems = [
  { to: '/dashboard', icon: BarChart3, label: 'Dashboard' },
  { to: '/watch', icon: Eye, label: 'Watch' },
]

export function Topbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const location = useLocation()

  const currentPage = navItems.find((item) => location.pathname.startsWith(item.to))

  return (
    <header className="sticky top-0 z-50 border-b bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/60">
      <div className="flex h-14 items-center justify-between px-4 lg:px-6">
        {/* Mobile menu button */}
        <div className="flex items-center gap-4 lg:hidden">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            <Menu className="h-5 w-5" />
          </Button>
          <div className="flex items-center gap-2">
            <Gamepad2 className="h-5 w-5 text-primary" />
            <span className="font-semibold">Monopoly</span>
          </div>
        </div>

        {/* Desktop: current page title */}
        <div className="hidden lg:block">
          <h1 className="text-lg font-semibold">
            {currentPage?.label || 'Monopoly Analytics'}
          </h1>
        </div>

        {/* Right side actions */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground hidden sm:block">
            Real-time Analytics
          </span>
        </div>
      </div>

      {/* Mobile navigation */}
      {mobileMenuOpen && (
        <nav className="border-t p-4 lg:hidden">
          <div className="space-y-2">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={() => setMobileMenuOpen(false)}
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
          </div>
        </nav>
      )}
    </header>
  )
}

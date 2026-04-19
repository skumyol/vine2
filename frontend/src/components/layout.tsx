import { NavLink } from 'react-router-dom'
import { Wine } from 'lucide-react'

interface Props {
  children: React.ReactNode
}

export function Layout({ children }: Props) {
  const navClass = ({ isActive }: { isActive: boolean }) =>
    `px-3 py-1.5 rounded-md transition-colors ${isActive ? 'bg-accent text-foreground' : 'text-foreground hover:bg-accent'}`

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-50 border-b border-border bg-card/80 backdrop-blur-sm">
        <div className="mx-auto max-w-6xl flex items-center justify-between px-4 h-14">
          <div className="flex items-center gap-2">
            <Wine className="h-5 w-5 text-primary" />
            <span className="font-semibold text-foreground">VinoBuzz</span>
            <span className="text-xs text-muted-foreground hidden sm:inline">Photo Pipeline</span>
          </div>
          <nav className="flex items-center gap-1 text-sm">
            <NavLink to="/" end className={navClass}>
              Dashboard
            </NavLink>
            <NavLink to="/architecture" className={navClass}>
              Architecture
            </NavLink>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>
    </div>
  )
}

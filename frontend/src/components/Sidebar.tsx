import { NavLink } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { clsx } from 'clsx'

const publicItems = [
  { to: '/', label: 'One Pager', icon: 'M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5V6.75A3.75 3.75 0 0 0 10.875 3h-4.5A1.875 1.875 0 0 0 4.5 4.875v14.25A1.875 1.875 0 0 0 6.375 21h11.25a1.875 1.875 0 0 0 1.875-1.875v-4.875Z M14.25 3.75V8.25H18.75' },
  { to: '/architecture', label: 'Architecture', icon: 'M6.75 3v2.25m10.5-2.25v2.25M3 18.75V8.25A2.25 2.25 0 0 1 5.25 6h13.5A2.25 2.25 0 0 1 21 8.25v10.5A2.25 2.25 0 0 1 18.75 21H5.25A2.25 2.25 0 0 1 3 18.75Z M7.5 11.25h9m-9 3h6' },
  { to: '/demo', label: 'Guided Scenario', icon: 'M5.25 5.653c0-1.427 1.529-2.33 2.779-1.643l11.54 6.347c1.295.712 1.295 2.573 0 3.286L8.03 19.99c-1.25.687-2.779-.217-2.779-1.643V5.653Z' },
]

const navItems = [
  { to: '/app', label: 'Dashboard', icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-4 0a1 1 0 01-1-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 01-1 1' },
  { to: '/app/review', label: 'Review Queue', icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2' },
  { to: '/app/cases', label: 'Cases', icon: 'M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10' },
  { to: '/app/admin', label: 'Configuration', icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z' },
  { to: '/app/wellbeing', label: 'Wellbeing', icon: 'M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z' },
  { to: '/app/getting-started', label: 'Getting Started', icon: 'M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25' },
]

export function Sidebar() {
  const user = useAuthStore((s) => s.user)

  return (
    <aside className="flex w-64 flex-col bg-[#1A1A1A]">
      <div className="flex h-16 items-center gap-2 border-b border-white/10 px-6">
        <div className="h-8 w-8 rounded-lg bg-midnight flex items-center justify-center">
          <span className="text-sm font-bold text-white">TG</span>
        </div>
        <span className="text-lg font-semibold text-white">SafetyAgent</span>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-4">
        {publicItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-white/10 text-white'
                  : 'text-gray-400 hover:bg-white/5 hover:text-white',
              )
            }
          >
            <svg className="h-5 w-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d={item.icon} />
            </svg>
            {item.label}
          </NavLink>
        ))}

        <div className="my-3 border-t border-white/10" />

        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/app'}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-midnight/20 text-mauve'
                  : 'text-gray-400 hover:bg-white/5 hover:text-white',
              )
            }
          >
            <svg className="h-5 w-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d={item.icon} />
            </svg>
            {item.label}
          </NavLink>
        ))}
      </nav>

      {user && (
        <div className="border-t border-white/10 p-4">
          <div className="text-sm font-medium text-gray-200">{user.email}</div>
          <div className="text-xs text-gray-500 capitalize">{user.role}</div>
        </div>
      )}
    </aside>
  )
}

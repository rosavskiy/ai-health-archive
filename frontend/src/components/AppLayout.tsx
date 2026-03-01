"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clsx } from "clsx";

const NAV = [
  { href: "/dashboard", label: "Дашборд", icon: "🏠" },
  { href: "/archive", label: "Архив", icon: "📁" },
  { href: "/trends", label: "Динамика", icon: "📈" },
  { href: "/chat", label: "AI-Врач", icon: "🤖" },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    router.push("/login");
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Top bar */}
      <header className="bg-white border-b border-gray-100 px-4 py-3 flex items-center justify-between sticky top-0 z-30">
        <div className="flex items-center gap-2 font-bold text-brand-700">
          <span className="text-xl">🏥</span>
          <span className="hidden sm:inline">AI Health Archive</span>
        </div>
        <button onClick={handleLogout} className="text-sm text-gray-500 hover:text-gray-700">
          Выйти
        </button>
      </header>

      {/* Content */}
      <main className="flex-1 container max-w-4xl mx-auto px-4 py-6 pb-24">{children}</main>

      {/* Bottom Nav (mobile) */}
      <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-100 z-30 safe-area-pb">
        <div className="flex items-center justify-around max-w-md mx-auto">
          {NAV.map(({ href, label, icon }) => (
            <Link
              key={href}
              href={href}
              className={clsx(
                "flex flex-col items-center py-2 px-3 text-xs font-medium transition-colors",
                pathname === href ? "text-brand-600" : "text-gray-400 hover:text-gray-600"
              )}
            >
              <span className="text-xl mb-0.5">{icon}</span>
              {label}
            </Link>
          ))}
        </div>
      </nav>
    </div>
  );
}

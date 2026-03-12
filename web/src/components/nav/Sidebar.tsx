"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const navLinks = [
  { href: "/tasks", label: "Task List" },
  { href: "/tasks/new", label: "Submit Task" },
  { href: "/workers", label: "Workers" },
  { href: "/sandboxes", label: "Sandboxes" },
  { href: "/settings", label: "Settings" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 min-h-screen bg-gray-100 dark:bg-gray-900 text-gray-800 dark:text-white flex flex-col">
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <h1 className="text-lg font-bold text-gray-900 dark:text-white">Coding Machine</h1>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Multi-Agent Development</p>
      </div>
      <nav className="flex-1 p-4">
        <ul className="space-y-1">
          {navLinks.map((link) => (
            <li key={link.href}>
              <Link
                href={link.href}
                className={cn(
                  "block px-4 py-2 rounded-md text-sm transition-colors",
                  pathname === link.href || pathname.startsWith(link.href + "/")
                    ? "bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white"
                    : "text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white"
                )}
              >
                {link.label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </aside>
  );
}

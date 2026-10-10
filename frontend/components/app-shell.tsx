"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BookOpen,
  Brain,
  CameraOff,
  History,
  LayoutDashboard,
  Settings,
  FileText,
  Target,
} from "lucide-react";

import { ApiError } from "@/lib/api/client";
import { useMe } from "@/lib/api/hooks";
import { cn } from "@/lib/utils";
import { Alert, AlertDescription } from "@/components/ui/alert";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/resume", label: "Resume workspace", icon: FileText },
  { href: "/interview", label: "Interview setup", icon: Brain },
  { href: "/skill-gaps", label: "Skill gaps", icon: Target },
  { href: "/learning-plan", label: "Learning plan", icon: BookOpen },
  { href: "/history", label: "History", icon: History },
  { href: "/settings", label: "Privacy", icon: Settings },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const me = useMe();
  const apiDown = me.isError && !(me.error instanceof ApiError && me.error.status === 401);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="mx-auto flex min-h-screen max-w-7xl">
        <aside className="hidden w-64 shrink-0 border-r border-border p-6 md:block">
          <Link href="/dashboard" className="block font-semibold tracking-tight">
            karanVerse InterviewOS AI
          </Link>
          <p className="mt-1 text-xs text-muted-foreground">Career intelligence, not a chatbot.</p>
          <nav className="mt-8 space-y-1">
            {NAV.map((item) => {
              const Icon = item.icon;
              const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-2 rounded-md px-3 py-2 text-sm",
                    active ? "bg-secondary text-foreground" : "text-muted-foreground hover:bg-secondary/70",
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
          <div className="mt-6 space-y-2 text-xs text-muted-foreground">
            <p>{me.data?.display_name ?? "Local workspace"}</p>
            <p className="flex items-center gap-1">
              <CameraOff className="h-3 w-3" />
              Webcam is optional and off by default.
            </p>
          </div>
        </aside>
        <div className="flex min-w-0 flex-1 flex-col">
          <header className="flex items-center justify-between border-b border-border px-4 py-3 md:hidden">
            <span className="font-medium">karanVerse InterviewOS AI</span>
            <Link href="/settings" className="text-sm text-muted-foreground">
              Privacy
            </Link>
          </header>
          <main className="flex-1 p-4 md:p-8">
            {apiDown ? (
              <Alert variant="destructive" className="mb-4">
                <AlertDescription>
                  {me.error instanceof Error
                    ? me.error.message
                    : "The InterviewOS API is unreachable. Confirm the backend is running."}
                </AlertDescription>
              </Alert>
            ) : null}
            {children}
          </main>
        </div>
      </div>
    </div>
  );
}

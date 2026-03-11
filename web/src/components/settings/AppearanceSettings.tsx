"use client";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";

export function AppearanceSettings() {
  const { theme, setTheme } = useTheme();
  return (
    <div className="space-y-4 max-w-md">
      <div>
        <h3 className="text-sm font-medium mb-1">Theme</h3>
        <p className="text-sm text-muted-foreground mb-3">
          Select your preferred colour scheme.
        </p>
        <div className="flex gap-2">
          <Button
            variant={theme === "light" ? "default" : "outline"}
            size="sm"
            onClick={() => setTheme("light")}
          >
            Light
          </Button>
          <Button
            variant={theme === "dark" ? "default" : "outline"}
            size="sm"
            onClick={() => setTheme("dark")}
          >
            Dark
          </Button>
        </div>
      </div>
    </div>
  );
}

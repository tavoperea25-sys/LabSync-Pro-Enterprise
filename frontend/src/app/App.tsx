import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MotionConfig } from "motion/react";
import { Suspense } from "react";
import { RouterProvider } from "react-router";

import { AuthProvider } from "@/features/auth/hooks/AuthProvider";
import { ThemeProvider } from "@/shared/hooks/ThemeProvider";

import { router } from "./router";
import { RouteFallback } from "./RouteFallback";

const queryClient = new QueryClient();

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <MotionConfig reducedMotion="user">
        <ThemeProvider>
          <AuthProvider>
            {/* `AuthProvider` y este `Suspense` no dependen de ningún hook
                de router (ver router.tsx) — envuelven `<RouterProvider>`
                desde afuera con el mismo efecto que antes tenían envolviendo
                `<Routes>` desde dentro de `<BrowserRouter>`. */}
            <Suspense fallback={<RouteFallback />}>
              <RouterProvider router={router} />
            </Suspense>
          </AuthProvider>
        </ThemeProvider>
      </MotionConfig>
    </QueryClientProvider>
  );
}

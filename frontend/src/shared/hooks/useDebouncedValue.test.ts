import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useDebouncedValue } from "./useDebouncedValue";

describe("useDebouncedValue", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("devuelve el valor inicial de inmediato, sin esperar el debounce", () => {
    const { result } = renderHook(() => useDebouncedValue("inicial"));
    expect(result.current).toBe("inicial");
  });

  it("no actualiza el valor hasta que pasa el retraso configurado", () => {
    const { result, rerender } = renderHook(({ valor }) => useDebouncedValue(valor, 300), {
      initialProps: { valor: "a" },
    });

    rerender({ valor: "b" });
    expect(result.current).toBe("a"); // todavía no pasó el retraso

    act(() => {
      vi.advanceTimersByTime(299);
    });
    expect(result.current).toBe("a");

    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(result.current).toBe("b");
  });

  it("reinicia el temporizador si el valor cambia antes de que se cumpla el retraso", () => {
    const { result, rerender } = renderHook(({ valor }) => useDebouncedValue(valor, 300), {
      initialProps: { valor: "a" },
    });

    rerender({ valor: "b" });
    act(() => {
      vi.advanceTimersByTime(200);
    });
    rerender({ valor: "c" });
    act(() => {
      vi.advanceTimersByTime(200);
    });
    // Pasaron 400ms desde "b", pero solo 200ms desde "c" -> no se actualizó a "c" todavía,
    // y nunca llegó a asentarse en "b" porque el cambio a "c" reinició el temporizador.
    expect(result.current).toBe("a");

    act(() => {
      vi.advanceTimersByTime(100);
    });
    expect(result.current).toBe("c");
  });
});

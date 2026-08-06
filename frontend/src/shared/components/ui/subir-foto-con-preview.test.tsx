import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Camera } from "lucide-react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/httpClient";

import { SubirFotoConPreview } from "./subir-foto-con-preview";

function archivoDePrueba(nombre = "foto.png"): File {
  return new File(["contenido"], nombre, { type: "image/png" });
}

function inputDeArchivo(container: HTMLElement): HTMLInputElement {
  const input = container.querySelector('input[type="file"]');
  if (!input) throw new Error("No se encontró el input de archivo.");
  return input as HTMLInputElement;
}

const PROPS_BASE = {
  etiqueta: "Fotografía",
  iconoVacio: Camera,
  textoAyuda: "Máximo 5MB.",
  altTexto: "Fotografía de prueba",
};

beforeEach(() => {
  // jsdom no implementa createObjectURL/revokeObjectURL — se stubean con un
  // generador determinista para poder verificar exactamente qué blob se
  // creó y cuál se revocó en cada paso (M8, Fase 2, docs/22).
  let contador = 0;
  URL.createObjectURL = vi.fn(() => `blob:mock-${++contador}`);
  URL.revokeObjectURL = vi.fn();
});

describe("SubirFotoConPreview", () => {
  it("preview inicial: muestra la URL persistida sin crear ningún blob", () => {
    render(
      <SubirFotoConPreview
        {...PROPS_BASE}
        urlActual="https://minio.local/foto-actual.jpg"
        onSubir={vi.fn()}
        onSubidoExitosamente={vi.fn()}
      />,
    );

    expect(screen.getByAltText("Fotografía de prueba")).toHaveAttribute(
      "src",
      "https://minio.local/foto-actual.jpg",
    );
    expect(URL.createObjectURL).not.toHaveBeenCalled();
  });

  it("preview inicial: sin URL persistida, muestra el ícono vacío en vez de una imagen", () => {
    render(
      <SubirFotoConPreview {...PROPS_BASE} urlActual={null} onSubir={vi.fn()} onSubidoExitosamente={vi.fn()} />,
    );
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  it("cambio de archivo: sube, reemplaza el preview por un blob y notifica el nuevo object_key", async () => {
    const onSubir = vi.fn().mockResolvedValue("nuevo-object-key.png");
    const onSubidoExitosamente = vi.fn();
    const { container } = render(
      <SubirFotoConPreview
        {...PROPS_BASE}
        urlActual={null}
        onSubir={onSubir}
        onSubidoExitosamente={onSubidoExitosamente}
      />,
    );
    const usuario = userEvent.setup();
    const archivo = archivoDePrueba();

    await usuario.upload(inputDeArchivo(container), archivo);

    await waitFor(() => expect(onSubir).toHaveBeenCalledWith(archivo));
    expect(onSubidoExitosamente).toHaveBeenCalledWith("nuevo-object-key.png");
    expect(URL.createObjectURL).toHaveBeenCalledWith(archivo);
    expect(await screen.findByAltText("Fotografía de prueba")).toHaveAttribute("src", "blob:mock-1");
  });

  it("eliminación/cambio de preview: subir un segundo archivo revoca el blob anterior antes de mostrar el nuevo", async () => {
    const onSubir = vi.fn().mockResolvedValue("object-key");
    const { container } = render(
      <SubirFotoConPreview {...PROPS_BASE} urlActual={null} onSubir={onSubir} onSubidoExitosamente={vi.fn()} />,
    );
    const usuario = userEvent.setup();
    const input = inputDeArchivo(container);

    await usuario.upload(input, archivoDePrueba("uno.png"));
    await waitFor(() => expect(onSubir).toHaveBeenCalledTimes(1));

    await usuario.upload(input, archivoDePrueba("dos.png"));
    await waitFor(() => expect(onSubir).toHaveBeenCalledTimes(2));

    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:mock-1");
    expect(await screen.findByAltText("Fotografía de prueba")).toHaveAttribute("src", "blob:mock-2");
  });

  it("verificación de revokeObjectURL: al desmontar el componente se libera el blob vigente", async () => {
    const onSubir = vi.fn().mockResolvedValue("object-key");
    const { container, unmount } = render(
      <SubirFotoConPreview {...PROPS_BASE} urlActual={null} onSubir={onSubir} onSubidoExitosamente={vi.fn()} />,
    );
    const usuario = userEvent.setup();
    await usuario.upload(inputDeArchivo(container), archivoDePrueba());
    await waitFor(() => expect(onSubir).toHaveBeenCalledTimes(1));

    unmount();

    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:mock-1");
  });

  it("no revoca nada al desmontar si nunca se subió un archivo nuevo (solo había una URL persistida, no un blob propio)", () => {
    const { unmount } = render(
      <SubirFotoConPreview
        {...PROPS_BASE}
        urlActual="https://minio.local/foto-actual.jpg"
        onSubir={vi.fn()}
        onSubidoExitosamente={vi.fn()}
      />,
    );
    unmount();
    expect(URL.revokeObjectURL).not.toHaveBeenCalled();
  });

  it("si la subida falla, muestra el error, conserva el preview anterior y no notifica éxito", async () => {
    const onSubir = vi.fn().mockRejectedValue(new ApiError("archivo_invalido", "Formato no soportado.", 422));
    const onSubidoExitosamente = vi.fn();
    const { container } = render(
      <SubirFotoConPreview
        {...PROPS_BASE}
        urlActual="https://minio.local/foto-actual.jpg"
        onSubir={onSubir}
        onSubidoExitosamente={onSubidoExitosamente}
      />,
    );
    const usuario = userEvent.setup();
    await usuario.upload(inputDeArchivo(container), archivoDePrueba());

    expect(await screen.findByRole("alert")).toHaveTextContent(/formato no soportado/i);
    expect(onSubidoExitosamente).not.toHaveBeenCalled();
    expect(screen.getByAltText("Fotografía de prueba")).toHaveAttribute(
      "src",
      "https://minio.local/foto-actual.jpg",
    );
    expect(URL.createObjectURL).not.toHaveBeenCalled();
  });
});

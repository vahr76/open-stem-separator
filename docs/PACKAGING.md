# Packaging de ytd / OSS Downloader Core

Este documento define cómo convertir el núcleo `ytd` en el primer asset publicable de OSS: un descargador simple para audio/video de YouTube y otros sitios soportados por yt-dlp.

## Objetivo de la primera entrega

El primer entregable debe instalar un comando simple:

```sh
ytd
```

El usuario no debería tener que recordar una línea larga de Python. El flujo base pide solo la URL, permite elegir audio, video o ambos, y después el formato cuando corresponde. La calidad no se pregunta: el programa siempre selecciona la mejor fuente disponible para el formato elegido.

## Variantes de paquete

### 1. Paquete fuente con instalador

Es el estado actual. Incluye `oss.py`, instaladores por sistema operativo y un comando de usuario llamado `ytd`. Requiere Python 3 y dependencias del sistema o descargadas durante la instalación.

Sirve para probar rápido y depurar porque el código queda visible.

### 2. Paquete autocontenido

Es la variante objetivo para usuarios finales. Debe incluir:

- ejecutable `ytd` generado con PyInstaller o herramienta equivalente;
- `yt-dlp` fijado a una versión concreta;
- `ffmpeg` y `ffprobe`;
- `deno` para compatibilidad con extractores de YouTube que requieren EJS;
- `README.md`;
- `dependencies.json`;
- avisos y licencias de terceros.

En esa variante el usuario descarga un paquete para su sistema, ejecuta el instalador y obtiene el comando `ytd` sin instalar Python manualmente.

## Regla de calidad

La selección de calidad vive en el código, no en el instalador. Para mantener el comportamiento consistente:

- audio original usa `bestaudio`;
- WAV/FLAC/MP3 usan `bestaudio/best` antes de convertir;
- MP3 convierte a `320K`;
- video usa `bestvideo+bestaudio/best[vcodec!=none][acodec!=none]`;
- ambos ejecuta dos descargas: video completo y audio separado.

Si una plataforma solo ofrece audio comprimido, convertir a WAV o FLAC conserva el resultado sin pérdida adicional, pero no recupera información que la fuente no traía.

## Builds por sistema operativo

Los binarios autocontenidos deben generarse en cada sistema operativo de destino:

- Linux x64 en Linux;
- Windows x64 en Windows;
- macOS arm64/x64 en macOS.

La razón es práctica: PyInstaller y los binarios nativos de FFmpeg/Deno no producen un ejecutable universal desde un solo sistema. Para releases reales conviene usar CI con una matriz por OS.

## Build Linux local

Desde la carpeta `outputs/oss`:

```sh
chmod +x tools/build-linux.sh
tools/build-linux.sh
```

Si PyInstaller está disponible, crea un ejecutable `ytd`. Si no está disponible, genera un paquete fuente con wrapper `ytd` que requiere Python 3. En ambos casos intenta copiar `yt-dlp`, `ffmpeg`, `ffprobe` y `deno` desde PATH hacia `bin/`.

El script escribe en `release/dist-linux-x64-<fecha>/` para no pisar builds anteriores.

## Checklist antes de publicar

1. Ejecutar pruebas unitarias.
2. Probar `ytd doctor`.
3. Probar audio original, FLAC, MP3, video y ambos.
4. Verificar que los archivos quedan en `artista/tema`.
5. Verificar que un error de cookies reintenta automáticamente con navegador local.
6. Verificar que una falla de miniatura no corta la descarga base.
7. Fijar versiones exactas de dependencias en `dependencies.json`.
8. Guardar hashes SHA-256 de cada binario incluido.
9. Incluir textos de licencia requeridos por cada binario distribuido.
10. Probar instalación limpia en Windows, macOS y Linux con usuario sin permisos de administrador.

# OSS — Open Stem Separator

Primer prototipo del núcleo de descarga. Nombre provisional. El diagrama BASS es una referencia de producto; sus motores y afirmaciones no se consideran decisiones definitivas.

## Ejecutar el prototipo

Requiere Python 3.10+ y yt-dlp. FFmpeg y ffprobe para convertir o combinar pistas; Deno y EJS compatible para soporte completo de YouTube. Busca ejecutables primero en `bin/` junto a OSS y después en PATH. No instala ni modifica el proyecto BASS existente.

Uso después de instalar:

```sh
ytd
ytd 'URL'
ytd flac 'URL'
ytd video 'URL'
ytd both 'URL'
ytd mp3 'URL'
ytd doctor
ytd history
```

El instalador crea el comando `ytd` en una carpeta de comandos de usuario. En Linux/macOS el valor predeterminado es `~/.local/bin`; en Windows se crea `ytd.cmd`.

Desde la carpeta fuente también se puede ejecutar:

```sh
python3 oss.py
python3 oss.py doctor
python3 oss.py configure --downloads-dir '/carpeta/con permisos'
python3 oss.py formats 'URL'
python3 oss.py download 'URL' --profile original --output '/carpeta/con permisos'
python3 oss.py download 'URL' --profile flac --output '/carpeta/con permisos'
python3 -m unittest discover -s tests -v
```

En Windows usar `py` en lugar de `python3`. Sin argumentos abre el flujo interactivo. Primero verifica si hay nueva versión de yt-dlp, pide la URL, pregunta si se quiere audio, video o ambos, y después muestra solo los formatos que corresponden. Video siempre incluye audio. Ambos descarga dos archivos: un video completo en la mejor calidad posible y un audio separado en el formato elegido. La calidad no se pregunta: OSS siempre le pide a yt-dlp la mejor fuente disponible; el formato solo decide si se conserva, se empaqueta o se convierte. Los perfiles directos son original, wav, flac, mp3, video y mp4. `--playlist` habilita listas explícitamente. `--dry-run` muestra los argumentos sin descargar ni crear carpetas.

La carpeta predeterminada es Music/OSS/downloads dentro del directorio personal. Se puede cambiar con `configure` o con `--output` en modo avanzado. Para pruebas aisladas se puede usar `--config /tmp/oss-test/config.json` o `OSS_CONFIG_DIR=/tmp/oss-test/config`, evitando tocar la configuración real del usuario. Antes de ejecutar el motor se crea la carpeta si corresponde y se prueba la escritura con un archivo temporal. Si falla, se informa el problema sin elevar privilegios. Esta prueba no garantiza espacio libre durante toda la descarga ni evita cambios de permisos posteriores.

Las URLs pegadas como enlace Markdown, por ejemplo `[https://...](https://...)`, se normalizan antes de pasarlas a yt-dlp. Los nombres de archivo usan modo restringido para evitar comillas, caracteres Unicode raros o símbolos incómodos en terminales y scripts. El ID del video no se agrega al nombre visible; cuando se descarga video + audio separados, OSS agrega los sufijos ` - video` y ` - audio`.

Cada descarga crea una carpeta de proyecto. OSS intenta detectar `artista/tema` desde metadata real de yt-dlp o desde títulos con forma `Artista - Tema`. Si no hay confianza suficiente, guarda en `_unsorted/Titulo`. También escribe `metadata.json` con URL, título, uploader, duración, ID y el origen/confianza de la detección.

Además mantiene un historial local en `history.jsonl` junto a la configuración de OSS. `ytd history` muestra las últimas entradas. Cada línea registra fecha, URL, perfil, estado, código de salida, carpeta de proyecto y datos detectados como artista/tema cuando existen. En pruebas se puede aislar con `--config /tmp/oss-test/config.json` u `OSS_CONFIG_DIR=/tmp/oss-test/config`.

```text
downloads/
  Iron_Butterfly/
    In_A_Gadda_Da_Vida/
      metadata.json
      IRON_BUTTERFLY_-_IN_A_GADDA_DA_VIDA... - video.mkv
      IRON_BUTTERFLY_-_IN_A_GADDA_DA_VIDA... - audio.flac
```

Original conserva el mejor stream de audio que selecciona yt-dlp sin recodificar. WAV/FLAC toman la mejor fuente de audio disponible y convierten sin pérdida adicional, aunque no recuperan información perdida en la fuente. MP3 toma la mejor fuente de audio disponible y convierte a 320 kbps, que es el máximo práctico para MP3. Video descarga un archivo completo con video y audio en la mejor calidad disponible. Ambos descarga ese video completo y además un archivo de audio separado en el formato elegido. MP4 limita la selección a streams MP4/M4A y puede ofrecer menor calidad o no estar disponible. MP4 no garantiza compatibilidad de códecs con todos los reproductores.

Las descargas usan archivos parciales y reanudación de yt-dlp, reintentos limitados y protección contra sobrescritura. Un error del motor se devuelve como error de OSS. La consulta de formatos permite inspeccionar lo disponible; la selección manual por ID todavía no está implementada.

## Cookies y miniaturas

Las cookies no forman parte del flujo de usuario. OSS intenta primero la descarga normal; si yt-dlp devuelve un error compatible con sesión, login, cookies, 403 o verificación, OSS detecta navegadores conocidos y reintenta automáticamente con `--cookies-from-browser`. El orden actual es Firefox, Chrome, Chromium, Edge, Brave y Vivaldi, priorizando un navegador guardado en configuración si existiera. La detección mira ejecutables en PATH y carpetas de perfil habituales del sistema.

Las miniaturas están desactivadas por defecto con `--thumbnails none`, porque no deben cortar una descarga de audio/video. Si se quieren conservar como ayuda visual:

```sh
python3 oss.py download 'URL' --thumbnails write
python3 oss.py configure --downloads-dir '/carpeta/con permisos' --thumbnails write
```

`write` guarda la miniatura como archivo adicional. `embed` intenta incrustarla dentro del archivo final y queda como modo avanzado: puede fallar por formato/códecs aunque la descarga principal esté bien. Para el flujo base de estudio conviene `none` o `write`.

## Instalación

Los scripts iniciales son:

```sh
./install-linux.sh
./install-macos.sh
pwsh ./install-windows.ps1
```

El instalador crea el comando `ytd`, instala en una carpeta de usuario y pregunta solo la carpeta de descargas. Usa PATH o descarga dependencias faltantes cuando el sistema y la red lo permitan. Comprueba escritura sin administrador y guarda la selección en configuración por usuario. El manifiesto `dependencies.json` deja preparada la lista de fuentes; antes de publicar paquetes reales hay que fijar versiones exactas y hashes.

**Estado real:** se entrega código fuente funcional y scripts de instalación iniciales. Todavía no es un paquete autocontenido terminado. Faltan bootstrap nativo sin Python, dependencias offline completas, versiones y hashes definitivos, paquetes por OS/arquitectura, avisos de terceros y validación en Windows/macOS. No se declara licencia de distribución definitiva en este prototipo.

Para avanzar hacia un paquete autocontenido, ver `docs/PACKAGING.md`. En Linux hay un primer script de build en `tools/build-linux.sh`; genera un artefacto en `release/dist-linux-x64-<fecha>/` y no pisa builds anteriores. La matriz completa de distribución multiplataforma está en `docs/DISTRIBUTION_MATRIX.md`: Windows, macOS, Linux genérico, y futuros paquetes `.deb`, `.rpm`, SUSE/openSUSE, Arch y AppImage.

## Validación realizada

36 pruebas unitarias: argumentos, URL, normalización de enlaces, nombres seguros sin ID visible, metadata/proyectos, MP3 320 kbps, dependencias ausentes, playlists, recuperación automática con cookies, miniaturas, flujo interactivo, error del motor, cancelación, configuración y escritura en carpeta. Integración Linux con servidor HTTP local y audio sintético: descarga original, conversión FLAC y MP3 y decodificación de los tres resultados mediante FFmpeg. No se verificaron descargas reales de YouTube ni paquetes en Windows/macOS.

## Fuentes técnicas

- https://github.com/yt-dlp/yt-dlp#readme
- https://github.com/yt-dlp/yt-dlp/wiki/EJS

La distribución de binarios tiene dependencias y licencias propias; gratis y redistribuible no son equivalentes. Revisar los avisos de cada versión antes de publicar paquetes.

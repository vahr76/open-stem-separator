# Evolución de OSS

## Decisiones propuestas

Interfaz web en localhost y servicio local para archivos, descargas e inferencia CPU/GPU. La CLI y la futura API deben compartir el núcleo; la interfaz no debe construir comandos de shell. Empezar con un proceso de trabajo y trabajos serializados; añadir concurrencia al medir memoria y rendimiento, sin exigir Celery/Redis inicialmente.

La reproducción tendrá prioridad dentro de OSS: suspender o limitar la inferencia mientras se reproduce si hay cortes. Una web no puede garantizar prioridad sobre todos los procesos del sistema. Licenciamiento y planificación de recursos son decisiones distintas.

## Etapas y criterios de aceptación

1. Descarga e instalación: asistente con modo completo/ligero, carpeta configurable y persistente, versiones verificadas, cancelación, disco lleno, pérdida de red, errores de conversión y prueba nativa en Windows/Linux/macOS. Elegir calidad máxima dentro de las restricciones del formato solicitado.
2. Separación: interfaz intercambiable para motores y modelos con versiones identificadas. Evaluar bajo, voz y batería con canciones de referencia antes de seleccionar motor. Soportar 2 stems (instrumento/resto), 4 stems y 5 stems con piano sólo cuando el modelo lo permita. Restar un stem de la mezcla no elimina sus errores; evaluar también el acompañamiento.
3. Reproductor de estudio: mixer sincronizado, mute/solo, loop A/B, exportación. Tempo y tono con un reloj compartido para todos los stems. Medir latencia real, cortes y artefactos en varios equipos; no prometer cero absoluto.
4. Análisis musical: BPM y rejilla editable, tonalidad/acordes con confianza y corrección manual, click como pista exportable. Cambios de tempo y compás deben representarse explícitamente.
5. Transcripción: notas de bajo/voz como eventos con inicio, fin, altura y confianza. Un transiente no necesariamente es una nota nueva. Batería requiere detección de golpes y clasificación por instrumento, con mapa MIDI adaptable a EZdrummer; no asumir que el motor de transcripción melódica resuelve percusión.
6. Letras: transcripción más alineación con posibilidad de corregir texto/tiempos. Exportar LRC/WebVTT. Sincronizar a la misma posición musical del reproductor.
7. Metrónomo externo: identificar dispositivo y protocolo real antes de elegir implementación. Considerar reloj, deriva y compensación de latencia.
8. UI: estética de estudio oscura inspirada en Logic, con controles propios y navegación accesible. PixiJS es una opción a medir, no un requisito inicial.

## Límites de producto

La separación no recupera pistas maestras perfectas. Los modelos, pesos y motores se evaluarán por calidad, recursos y condiciones de distribución por separado. No tomar la afirmación del diagrama sobre el “mejor modelo actual” como hecho verificado. La exportación debe declarar formato, sample rate y profundidad; evitar normalización destructiva silenciosa y clipping de la mezcla.

## Distribución multiplataforma

La primera etapa no se considera cerrada hasta que `ytd` tenga una estrategia clara para Windows, macOS y Linux. Linux debe incluir paquete genérico `.tar.gz` y luego paquetes por familia: `.deb`, `.rpm`, SUSE/openSUSE, Arch y AppImage. Ver `docs/DISTRIBUTION_MATRIX.md`.

# Aguacate Pomodoro

## Objetivo
App de escritorio para **Windows**: temporizador pomodoro con forma de aguacate que,
durante el tiempo de trabajo, bloquea webs que distraen editando el archivo `hosts`.

## Stack
- Python 3.14.5 (en el PC del usuario) + PySide6 6.12.0.
- Sonido generado por código con `QAudioSink` (QtMultimedia), sin archivos de audio.
- Empaquetado a `.exe` con PyInstaller (Fase 3).
- Configuración en `%APPDATA%\Aguacate\config.json` (Fase 3).
- Entorno virtual `.venv` + `requirements.txt`. Tests con `unittest` (sin dependencias extra).

## Cómo se trabaja
- El usuario tiene poca experiencia con vibe coding: explicar cada paso brevemente.
- **Pedir confirmación antes de cualquier cosa que cambie el sistema** (hosts, UAC, DNS, tareas programadas).
- Trabajo por fases; parar al final de cada una y dar al usuario los comandos exactos
  (y la carpeta) para probarla en Windows.
- Claude trabaja en un contenedor Linux: no puede probar UAC, hosts real ni `.exe`.
  La lógica de hosts se prueba con un archivo falso.
- Código entregado por GitHub: `muelean/aguacate-pomodoro-vibecoded`. Carpeta local del usuario:
  `C:\proyectos-claude\aguacate-pomodoro-vibecoded`.
- Idioma: español de España. Datos concretos antes que adjetivos.

## Decisiones tomadas
| Tema | Decisión |
|---|---|
| Forma | Aguacate dibujado con QPainter (curvas Bézier), sin imágenes. |
| Progreso | Anillo circular en la pulpa que se vacía + el hueso se encoge hasta desaparecer. |
| Contador | MM:SS en una pastilla encima del aguacate, con el estado debajo. |
| Clic | Clic izquierdo en **cualquier parte del aguacate** = iniciar/pausar/parar alarma. Arrastrar (>5 px) mueve la ventana sin contar como clic. |
| Fin del trabajo | Pitido repetido + vibración hasta clic. El clic para la alarma y **empieza el descanso**. |
| Fin del descanso | Sonido corto y suave una vez. El siguiente trabajo **espera a un clic**. |
| Siempre encima | Interruptor en el menú contextual. Activado por defecto. |
| Tiempo | Basado en `time.monotonic()` (no se desfasa aunque se retrasen los ticks). |
| Permisos admin | Relanzarse con `ShellExecuteW "runas"` al arrancar; si se rechaza, funciona sin bloqueo (no usar `--uac-admin`). (Fase 2) |
| Bloqueo | Bloque `# AGUACATE-START` / `# AGUACATE-END` en hosts, solo en trabajo en marcha; se quita al pausar, en descanso y al cerrar. Copia de seguridad única en `%APPDATA%\Aguacate\hosts.backup`. `ipconfig /flushdns` tras cada cambio. (Fase 2) |
| Modo demo | `python main.py --demo` = 10 s trabajo / 5 s descanso, para probar rápido. |

## Estructura
- `main.py` – punto de entrada.
- `aguacate/timer.py` – máquina de estados (sin Qt, testeable).
- `aguacate/painter.py` – dibujo del aguacate.
- `aguacate/beeper.py` – generación y reproducción de sonidos.
- `aguacate/window.py` – ventana, ratón, menú, vibración.
- `aguacate/config.py` – valores por defecto (en Fase 3, lectura/escritura de config.json).
- `tests/` – tests con `python -m unittest`.

## Estado
- [x] Fase 1: ventana + temporizador + pitido + vibración (pendiente de prueba del usuario).
- [ ] Fase 2: bloqueo con hosts + recuperación.
- [ ] Fase 3: ajustes, config.json, .exe.

## Limitaciones conocidas
- DNS seguro (DoH) del navegador, VPN o proxy pueden saltarse hosts.
- Pestañas/conexiones ya abiertas pueden seguir funcionando hasta cerrarlas (caché DNS del navegador).
- hosts no admite comodines: cada subdominio hay que listarlo.
- Defender puede avisar al modificar hosts o al ejecutar un `.exe` sin firmar.
- Si la app se cuelga, las webs siguen bloqueadas hasta reabrirla (o desbloqueo manual, ver README).

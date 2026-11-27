# Aguacate Pomodoro

## Objetivo
App de escritorio para **Windows**: temporizador pomodoro con forma de aguacate que,
durante el tiempo de trabajo, bloquea webs que distraen editando el archivo `hosts`.

## Stack
- Python 3.14.5 (en el PC del usuario) + PySide6 6.12.0.
- Sonido generado por código (síntesis PCM) y guardado como WAV en `%TEMP%\aguacate\` al arrancar.
  En Windows se reproduce con `winsound` (PlaySound, bucle con SND_LOOP); fuera de Windows (solo desarrollo) con QSoundEffect.
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
| Forma | Todo en **pixel art**: silueta Bézier rasterizada en celdas de 8 px; el hueso usa la misma rejilla. Sin imágenes. |
| Progreso | Sin anillo. El hueso se borra celda a celda con un **barrido en sentido horario** desde las 12; queda el hueco de la pulpa. El hueso no se encoge. |
| Contador | MM:SS en un **recuadro oscuro pixelado** dentro de la pulpa, encima del hueso, con fuente de píxeles 5x7 propia. Texto crema = trabajo, cian = descanso. Icono ▶ = listo, ❚❚ = pausa (debajo del recuadro). Parpadea en alarma. |
| Clic | Clic izquierdo en **cualquier parte del aguacate** = iniciar/pausar/parar alarma. Arrastrar (>5 px) mueve la ventana sin contar como clic. |
| Fin del trabajo | «Ding-dong» suave (Do5 + Mi5, caída tipo marimba, volumen 0.45) repetido + vibración hasta clic. El clic para la alarma y **empieza el descanso**. |
| Fin del descanso | Sonido corto y suave una vez. El siguiente trabajo **espera a un clic**. |
| Siempre encima | Interruptor en el menú. **Desactivado por defecto** (otras ventanas lo tapan). Al acabar el trabajo **o el descanso**, se activa «encima» temporalmente hasta el siguiente clic (no depende de que Windows deje robar el foco). |
| Tiempo | Basado en `time.monotonic()` (no se desfasa aunque se retrasen los ticks). |
| Permisos admin | Relanzarse con `ShellExecuteW "runas"` al arrancar; si se rechaza, funciona sin bloqueo (no usar `--uac-admin`). (Fase 2) |
| Bloqueo | Bloque `# AGUACATE-START` / `# AGUACATE-END` en hosts, solo en trabajo en marcha; se quita al pausar, en descanso y al cerrar. Copia de seguridad única en `%APPDATA%\Aguacate\hosts.backup`. `ipconfig /flushdns` tras cada cambio. (Fase 2) |
| Bloqueo: detalles | Además de `127.0.0.1` se añade `::1` por dominio (IPv6). Dominios validados con regex: lo que no sea un dominio válido se descarta (config.json no puede inyectar líneas). Escritura atómica (`.aguacate.tmp` + `os.replace`). Marcas rotas → `HostsCorrupt`, no se toca nada. Se respeta codificación (UTF-8/BOM/cp1252) y CRLF. El candado sustituye al icono mientras bloquea. Se bloquea solo en `phase == work and status == running` (la alarma ya no bloquea). |
| Relanzado con permisos | `python main.py` → `ShellExecuteW runas` con **pythonw.exe** (sin consola que se pueda cerrar por error). `--elevado` evita bucles. Errores a `%TEMP%\aguacate\errores.log`. |
| Limpieza al salir | `closeEvent`, `aboutToQuit`, `commitDataRequest` (apagado/cierre de sesión), `atexit`, SIGINT/SIGBREAK. Kill duro → limpieza al siguiente arranque con aviso. |
| Una sola instancia | `QLockFile` en `%TEMP%` (dos copias se pelearían por el hosts). |
| Opciones | `--demo`, `--sin-admin`, `--desbloquear` (limpia y sale). Desarrollo: `AGUACATE_HOSTS=ruta` usa un hosts falso. |
| Modo demo | `python main.py --demo` = 10 s trabajo / 5 s descanso, para probar rápido. |

## Estructura
- `main.py` – punto de entrada.
- `aguacate/timer.py` – máquina de estados (sin Qt, testeable).
- `aguacate/painter.py` – dibujo del aguacate.
- `aguacate/beeper.py` – generación y reproducción de sonidos.
- `aguacate/window.py` – ventana, ratón, menú, vibración.
- `aguacate/blocker.py` – hosts: marcas, copia de seguridad, escritura atómica, flushdns.
- `aguacate/admin.py` – comprobar permisos y relanzar con UAC.
- `aguacate/config.py` – valores por defecto (en Fase 3, lectura/escritura de config.json).
- `tests/` – tests con `python -m unittest`.

## Estado
- [x] Fase 1: ventana + temporizador + pitido + vibración (probada por el usuario).
- [x] Fase 2: bloqueo con hosts + recuperación (pendiente de prueba del usuario en Windows).
- [ ] Fase 3: ajustes, config.json, .exe.

## Limitaciones conocidas
- DNS seguro (DoH) del navegador, VPN o proxy pueden saltarse hosts.
- Pestañas/conexiones ya abiertas pueden seguir funcionando hasta cerrarlas (caché DNS del navegador).
- hosts no admite comodines: cada subdominio hay que listarlo.
- Defender puede avisar al modificar hosts o al ejecutar un `.exe` sin firmar.
- Si la app se cuelga, las webs siguen bloqueadas hasta reabrirla (o desbloqueo manual, ver README).

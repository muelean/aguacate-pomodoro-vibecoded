# Aguacate Pomodoro 🥑

Temporizador pomodoro para Windows con forma de aguacate. Mientras trabajas, bloquea las
webs que te distraen.

## Requisitos
- Windows 10/11
- Python 3.14 y Git

## Instalación (solo la primera vez)
Abre **PowerShell** y ejecuta, uno a uno:

```powershell
mkdir C:\proyectos-claude
cd C:\proyectos-claude
git clone https://github.com/muelean/aguacate-pomodoro-vibecoded.git
cd aguacate-pomodoro-vibecoded
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Si `Activate.ps1` da un error de «ejecución de scripts deshabilitada», ejecuta una vez
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` y vuelve a intentarlo.

## Ejecutar
Desde `C:\proyectos-claude\aguacate-pomodoro-vibecoded`, con el venv activado
(verás `(.venv)` al principio de la línea):

```powershell
python main.py          # 25 min trabajo / 5 min descanso
python main.py --demo   # pruebas: 10 s trabajo / 5 s descanso
python main.py --sin-admin    # sin pedir permisos (solo temporizador, sin bloqueo)
python main.py --desbloquear  # emergencia: quita el bloqueo del hosts y sale
```

Al arrancar, Windows te preguntará si permites que la app haga cambios: es para poder
bloquear webs (ver «Bloqueo de webs»). La ventana de PowerShell queda libre en cuanto
aparece el aguacate.

## Uso
| Acción | Resultado |
|---|---|
| Clic en el aguacate | Iniciar / pausar. Durante la alarma: la para y empieza el descanso. |
| Arrastrar el aguacate | Moverlo por la pantalla. |
| Clic derecho | Menú: minutos de trabajo y descanso, estado del bloqueo, reiniciar, siempre encima, Ajustes…, abrir config.json, salir. Con `--demo` los «minutos» son segundos y no se guardan. |

- El hueso desaparece con un barrido en sentido horario a medida que pasa el tiempo.
- El contador está dentro del aguacate: verde = trabajo, azul = descanso.
  ▶ = listo para empezar, ❚❚ = en pausa.
- Por defecto otras ventanas pueden tapar el aguacate. Cuando acaba un tiempo se pone
  encima de todo hasta que hagas clic. Si lo quieres siempre visible, activa
  «Siempre encima» en el menú.
- Al acabar el trabajo: «ding-dong» suave repetido y vibración hasta que hagas clic.
- Al acabar el descanso: un sonido suave; el siguiente trabajo empieza con un clic.

## Ajustes y config.json
Clic derecho → **Ajustes…** para cambiar tiempos, volumen, tono, vibración, «siempre
encima» y la lista de webs bloqueadas. El botón «▶ Probar sonido» toca la alarma con los
valores que estés eligiendo.

Todo se guarda en `%APPDATA%\Aguacate\config.json` (clic derecho → **Abrir config.json**
lo abre en el Bloc de notas). Si lo editas a mano con la app abierta, los cambios se
aplican al guardar el archivo. Si escribes algo mal, la app te avisa y sigue con lo que
tenía; cada valor incorrecto se sustituye por el de por defecto sin perder el resto.

| Clave | Por defecto | Valores |
|---|---|---|
| `work_minutes` | 25 | 1–180 |
| `break_minutes` | 5 | 1–60 |
| `always_on_top` | false | true / false |
| `volume` | 0.45 | 0.0–1.0 |
| `beep_ms` | 300 | 100–1000 (ms de cada nota) |
| `beep_frequency` | 523 | 200–2000 (Hz; más bajo = más grave) |
| `vibration` | true | true / false |
| `position` | null | [x, y] de la ventana; se guarda al arrastrarla |
| `blocked_domains` | youtube.com, … | lista de dominios: `["youtube.com", "www.youtube.com"]` |

Los dominios que no sean válidos (con espacios, `http://`, barras…) se ignoran y se avisa.

## Crear el .exe
Desde la carpeta del proyecto, en PowerShell:

```powershell
cd C:\proyectos-claude\aguacate-pomodoro-vibecoded
.\build.ps1
```

El script instala PyInstaller, pasa los tests, genera el icono y crea
`dist\AguacatePomodoro.exe` (un solo archivo, ~50–70 MB, no necesita Python instalado).
Puedes copiarlo donde quieras y crear un acceso directo (clic derecho → Mostrar más
opciones → Enviar a → Escritorio).

- Cada arranque tarda 2–4 s: el .exe se descomprime en una carpeta temporal y, al pedir
  permisos, se lanza dos veces (la primera solo para pedir el UAC).
- Las mismas opciones funcionan con el .exe: `AguacatePomodoro.exe --demo`,
  `--sin-admin`, `--desbloquear`.

## Actualizar a la última versión

```powershell
cd C:\proyectos-claude\aguacate-pomodoro-vibecoded
git pull
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Tests

```powershell
python -m unittest -v
```

## Bloqueo de webs
Mientras el **trabajo está en marcha** (verás un candado cerrado bajo el contador; si no diste permisos, el candado sale abierto y en naranja), la app añade
al archivo `C:\Windows\System32\drivers\etc\hosts` un bloque como este:

```
# AGUACATE-START
127.0.0.1 youtube.com
::1 youtube.com
...
# AGUACATE-END
```

Eso hace que esas webs apunten a tu propio PC y no carguen. El bloque se quita al pausar,
al empezar el descanso, al reiniciar y al salir. Después de cada cambio se ejecuta
`ipconfig /flushdns`. Nada fuera de las marcas se modifica nunca.

- **Permisos:** al abrir la app, Windows pregunta (UAC) si permites que haga cambios.
  Si dices «No», funciona como temporizador normal y te avisa de que el bloqueo está
  desactivado. Para no preguntar: `python main.py --sin-admin`.
- **Copia de seguridad:** antes del primer cambio se copia el hosts original a
  `%APPDATA%\Aguacate\hosts.backup` (solo una vez; nunca se sobrescribe).
- **Cierres bruscos:** si la app se cierra mal (cuelgue, Administrador de tareas, apagón),
  al volver a abrirla limpia el bloque y te avisa.
- **Errores:** se guardan en `%TEMP%\aguacate\errores.log`.
- **Estado:** el menú del clic derecho muestra «Bloqueo de webs: ACTIVO / en espera /
  desactivado».

### Limitaciones
- **Pestañas ya abiertas** pueden seguir funcionando un rato: el navegador guarda su propia
  caché de DNS y mantiene las conexiones abiertas. Cierra la pestaña o el navegador.
- **DNS seguro, VPN o proxy** pueden saltarse el hosts. Si una web no se bloquea, prueba a
  desactivar «Usar DNS seguro» (Chrome/Edge: Configuración → Privacidad y seguridad →
  Seguridad; Firefox: Configuración → Privacidad → DNS sobre HTTPS).
- **Sin comodines:** bloquear `youtube.com` no bloquea `music.youtube.com`. Cada subdominio
  hay que añadirlo a la lista.
- **Antivirus:** Microsoft Defender puede avisar al modificar el hosts o al ejecutar el
  .exe (no está firmado digitalmente).

## Desbloquear webs a mano
Si algo falla y alguna web se queda bloqueada, usa cualquiera de estas tres opciones
(de la más fácil a la más manual):

**1. Con la propia app** (pedirá permiso de administrador y mostrará un aviso con el
resultado):

```powershell
cd C:\proyectos-claude\aguacate-pomodoro-vibecoded
.\.venv\Scripts\Activate.ps1
python main.py --desbloquear
```

o, con el .exe: `.\dist\AguacatePomodoro.exe --desbloquear`

**2. Con el Bloc de notas:**
1. Menú Inicio → escribe «Bloc de notas» → clic derecho → **Ejecutar como administrador**.
2. Archivo → Abrir → pega `C:\Windows\System32\drivers\etc\hosts` en el nombre y pulsa
   Abrir.
3. Borra desde la línea `# AGUACATE-START` hasta `# AGUACATE-END`, ambas incluidas.
4. Guarda (Ctrl+S).
5. Abre PowerShell y ejecuta `ipconfig /flushdns`.

**3. Restaurar la copia de seguridad** (PowerShell como administrador). Ojo: deshace
también cualquier otro cambio que hayas hecho al hosts después de la copia.

```powershell
Copy-Item "$env:APPDATA\Aguacate\hosts.backup" "C:\Windows\System32\drivers\etc\hosts"
ipconfig /flushdns
```

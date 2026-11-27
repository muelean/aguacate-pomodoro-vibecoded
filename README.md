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
| Clic derecho | Menú: minutos de trabajo y descanso, reiniciar, siempre encima, salir. Con `--demo` los «minutos» son segundos. |

- El hueso desaparece con un barrido en sentido horario a medida que pasa el tiempo.
- El contador está dentro del aguacate: verde = trabajo, azul = descanso.
  ▶ = listo para empezar, ❚❚ = en pausa.
- Por defecto otras ventanas pueden tapar el aguacate. Cuando acaba un tiempo se pone
  encima de todo hasta que hagas clic. Si lo quieres siempre visible, activa
  «Siempre encima» en el menú.
- Al acabar el trabajo: «ding-dong» suave repetido y vibración hasta que hagas clic.
- Al acabar el descanso: un sonido suave; el siguiente trabajo empieza con un clic.

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
- **Antivirus:** Microsoft Defender puede avisar al modificar el hosts.

## Desbloquear webs a mano
Si algo falla y alguna web se queda bloqueada, usa cualquiera de estas tres opciones
(de la más fácil a la más manual):

**1. Con la propia app** (pedirá permiso de administrador):

```powershell
cd C:\proyectos-claude\aguacate-pomodoro-vibecoded
.\.venv\Scripts\Activate.ps1
python main.py --desbloquear
```

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

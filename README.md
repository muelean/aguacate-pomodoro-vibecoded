# Aguacate Pomodoro 🥑

Temporizador pomodoro para Windows con forma de aguacate. Mientras trabajas, bloquea las
webs que te distraen (Fase 2, en desarrollo).

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
```

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

## Desbloquear webs a mano
Se completará en la Fase 2.

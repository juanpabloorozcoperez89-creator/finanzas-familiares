[Uploading README.md…]()
# Finanzas Familiares · Maite & Pablo

App de Streamlit para registrar ingresos y egresos familiares, analizar la tarjeta de crédito con los **estados de cuenta reales del banco**, proyectar cuándo se liquida y detectar gastos hormiga.

## Stack

- Streamlit (frontend), Google Sheets (backend vía gspread), Streamlit Cloud (hosting)
- pdfplumber y xlrd para leer los estados de cuenta de Banco Industrial (PDF y XLS)

## Qué hay de nuevo en v4

| Antes | Ahora |
|---|---|
| El "saldo" de la tarjeta salía del plan teórico (`saldo_inicial_plan`), no del banco | El saldo, la tasa y la proyección salen de los **estados de cuenta importados** |
| Sin forma de ver a dónde se iba cada pago | Página **Estados de Cuenta**: desglose de cada corte en intereses, IVA, mora, gestión de cobro, anualidad, seguros, cuotas FIN/CT y lo que realmente bajó la deuda |
| Plan fijo a 10 meses | **Simulador**: pago mensual, abonos extra (Bono 14, aguinaldo), cargos nuevos y cuotas FIN restantes. Calcula la fecha del último pago, los intereses y el pago necesario para salir en N meses |
| — | **Diagnóstico automático**: mora, gestión de cobro, meses en que la deuda subió, cargos nuevos y tasa efectiva |
| — | Botón para **regenerar el plan** con el saldo real (conserva las cuotas pagadas) |
| Página de diagnóstico invisible (le faltaba `.py`) | `9_Diagnostico.py` visible, con checks nuevos |
| Fechas en hora UTC del servidor (después de las 6 p. m. ya era "mañana") | Zona horaria `America/Guatemala` |
| Descripciones con `<` o `&` rompían el HTML | Todo el texto del usuario se escapa |
| "Crear nueva categoría" no aparecía hasta enviar el formulario | Selector de categoría fuera del form; aparece al instante |
| Wrappers `<div>` vacíos alrededor de las gráficas | `st.container(border=True)` con estilo del tema |
| Parámetros solo editables en el Sheet | Formulario de parámetros en Configuración |
| `secrets.toml.example` con llave real | Plantilla con valores de ejemplo |

## Hojas del Google Sheet

`Transacciones`, `Categorias`, `Plan_Tarjeta` y `Config` (igual que antes) más **`Movimientos_Tarjeta`**, que la app crea sola al importar el primer estado de cuenta:

```
periodo_corte | fecha | tipo | doc | comercio | categoria | valor | saldo | archivo | importado
```

`valor` lleva signo: positivo aumenta la deuda y negativo la reduce (pagos).

### Claves nuevas en `Config` (se crean solas)

| clave | qué es |
|---|---|
| `pago_mensual_tarjeta` | Pago mensual comprometido (default 5500) |
| `tc_fin_total_cuotas` | Total de cuotas del extrafinanciamiento FIN/CT (vacío = no sé) |
| `tasa_mensual_override` | Forzar una tasa mensual (vacío = usar la tasa real calculada) |
| `tc_limite`, `tc_disponible`, `tc_saldo_mora`, `tc_pago_minimo`, `tc_fecha_pago`, `tc_fecha_corte`, `tc_tarjeta` | Se llenan al importar el último estado de cuenta |

`saldo_inicial_tarjeta`, `tasa_mensual` e `iva` quedan como respaldo cuando no hay estados importados.

## Cómo se usa

1. **Cada vez que pagan algo:** Registrar → 4 campos en 10 segundos.
2. **Cada mes, después del corte (día 11):** descargá el "Detalle de movimientos" de Banca en Línea BI (PDF o Excel) → **Estados de Cuenta → Importar**. Podés subir varios a la vez; los repetidos se ignoran.
3. **Plan Tarjeta:** muestra el saldo real, a dónde se va la próxima cuota y el simulador. Marcá el pago del mes en "Plan de cuotas".
4. **Gastos Hormiga** e **Histórico:** para detectar fugas.

## Cómo calcula la proyección

Por cada corte: `saldo_siguiente = saldo + saldo × tasa + cuota FIN/CT + cargos recurrentes − pago`.

- **tasa** = mediana de `(interés + IVA) ÷ saldo inicial` de los últimos 4 cortes (≈ 3.96 % mensual con los datos actuales).
- **cuota FIN/CT** = la del último corte. Se asume que sigue mientras haya deuda, salvo que configures `tc_fin_total_cuotas`.
- **cargos recurrentes** = seguros o comisiones que ya se repitieron. Los cargos nuevos se pueden incluir con un toggle.

La tasa es una aproximación (el banco calcula sobre saldo diario). El error típico es de ±Q100 de interés por mes.

## Setup

1. Google Sheet con las 4 pestañas (ver encabezados arriba) compartido como **Editor** con el `client_email` del service account.
2. `.streamlit/secrets.toml` siguiendo `.streamlit/secrets.toml.example`. **Nunca lo subas a git.**
3. Streamlit Cloud: conectá el repo y pegá los secrets en Settings → Secrets.

## Estructura

```
finanzas-familiares/
├── streamlit_app.py              # Dashboard
├── pages/
│   ├── 1_Registrar.py
│   ├── 2_Plan_Tarjeta.py         # Saldo real + simulador + plan de cuotas
│   ├── 3_Gastos_Hormiga.py
│   ├── 4_Historico.py
│   ├── 5_Configuracion.py        # Categorías + parámetros editables
│   ├── 6_Estados_de_Cuenta.py    # Importar PDF/XLS + análisis mes a mes
│   └── 9_Diagnostico.py
├── helpers/
│   ├── sheets.py                 # CRUD Google Sheets
│   ├── calc.py                   # Cálculos, zona horaria, situación de la tarjeta
│   ├── estado_cuenta.py          # Parser BI + resumen por corte + proyección (sin Streamlit)
│   └── theme.py                  # Diseño visual y componentes
└── .streamlit/
```

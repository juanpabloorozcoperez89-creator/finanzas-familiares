[README.md](https://github.com/user-attachments/files/29524288/README.md)
# Finanzas Familiares · Maite & Pablo

App de Streamlit para registrar ingresos/egresos familiares, controlar el plan de pago de la tarjeta de crédito y detectar gastos hormiga.

## Stack

- Streamlit (frontend)
- Google Sheets (backend, via gspread)
- Streamlit Cloud (hosting)

## Setup inicial

### 1. Crear el Google Sheet

Crea un Google Sheet nuevo llamado **"Finanzas Familiares"** y agrega estas 4 hojas (pestañas) con sus encabezados exactos:

**Hoja: `Transacciones`**
```
fecha | tipo | persona | categoria | descripcion | monto | es_hormiga | timestamp
```

**Hoja: `Categorias`**
```
nombre | tipo | umbral_hormiga | activa
```

Llena la hoja `Categorias` con estos valores iniciales:

| nombre | tipo | umbral_hormiga | activa |
|---|---|---|---|
| Salario | INGRESO | | TRUE |
| Bono | INGRESO | | TRUE |
| Otros Ingresos | INGRESO | | TRUE |
| Renta casa | EGRESO_FIJO | | TRUE |
| Pago Tarjeta | EGRESO_FIJO | | TRUE |
| Supermercado | EGRESO_FIJO | | TRUE |
| Gasolina | EGRESO_FIJO | | TRUE |
| Sarita | EGRESO_FIJO | | TRUE |
| Netflix | EGRESO_FIJO | | TRUE |
| Claude.ai | EGRESO_FIJO | | TRUE |
| Disney | EGRESO_FIJO | | TRUE |
| Internet | EGRESO_FIJO | | TRUE |
| Cell Sofi | EGRESO_FIJO | | TRUE |
| Cell Pablo | EGRESO_FIJO | | TRUE |
| Luz | EGRESO_FIJO | | TRUE |
| Tia Tachy | EGRESO_FIJO | | TRUE |
| Visacuotas Carro | EGRESO_FIJO | | TRUE |
| IGSS | EGRESO_FIJO | | TRUE |
| IRS | EGRESO_FIJO | | TRUE |
| Retencion Vintage | EGRESO_FIJO | | TRUE |
| Comida fuera | EGRESO_VARIABLE | 200 | TRUE |
| Corte de pelo | EGRESO_VARIABLE | 200 | TRUE |
| Carwash | EGRESO_VARIABLE | 200 | TRUE |
| Farmacia | EGRESO_VARIABLE | 200 | TRUE |
| Hija (gastos) | EGRESO_VARIABLE | 200 | TRUE |
| Salud | EGRESO_VARIABLE | 200 | TRUE |
| Transporte (Uber/taxi) | EGRESO_VARIABLE | 200 | TRUE |
| Entretenimiento | EGRESO_VARIABLE | 200 | TRUE |
| Ropa | EGRESO_VARIABLE | 200 | TRUE |
| Antojo / Snack | EGRESO_VARIABLE | 200 | TRUE |
| Regalos | EGRESO_VARIABLE | 200 | TRUE |
| Otros | EGRESO_VARIABLE | 200 | TRUE |

**Hoja: `Plan_Tarjeta`**
```
mes_num | mes_label | saldo_inicial_plan | pago_planeado | pago_real | fecha_pago_real | notas
```

Plan recalculado al 30/jun/2026 con base en datos reales verificados contra los PDFs de Banco Industrial. Pago fijo Q5,500/mes (sin bonos):

| mes_num | mes_label | saldo_inicial_plan | pago_planeado | pago_real | fecha_pago_real | notas |
|---|---|---|---|---|---|---|
| 1 | Jun 2026 | 37661.81 | 5500.00 | 5500.00 | 2026-06-01 | Cuota base (ya pagada) |
| 2 | Jul 2026 | 34394.94 | 5500.00 | | | Cuota base |
| 3 | Ago 2026 | 30990.85 | 5500.00 | | | Cuota base |
| 4 | Sep 2026 | 27443.81 | 5500.00 | | | Cuota base |
| 5 | Oct 2026 | 23747.78 | 5500.00 | | | Cuota base |
| 6 | Nov 2026 | 19896.52 | 5500.00 | | | Cuota base |
| 7 | Dic 2026 | 15883.50 | 5500.00 | | | Cuota base |
| 8 | Ene 2027 | 11701.94 | 5500.00 | | | Cuota base |
| 9 | Feb 2027 | 7344.75 | 5500.00 | | | Cuota base |
| 10 | Mar 2027 | 2804.56 | 3573.68 | | | Cierre final |

**Total a pagar:** Q53,073.68 · **Capital reducido:** Q37,661.81 · **Cargos del banco proyectados:** Q15,411.87 · **Liquidación:** marzo 2027

> ⚠️ Este plan asume que NO se logra finiquito negociado. Si Banco Industrial acepta
> negociación de intereses con pago de contado, el plan colapsa a un solo pago y las
> cuotas mensuales pasan a ser pagos a la persona prestamista (no al banco).

**Hoja: `Config`**
```
clave | valor
```

| clave | valor |
|---|---|
| saldo_inicial_tarjeta | 37661.81 |
| tasa_mensual | 0.0375 |
| iva | 0.12 |
| umbral_hormiga_default | 200 |
| meta_ingresos_mes | 26007.95 |

### 2. Service Account de Google

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un proyecto nuevo: `finanzas-familiares`
3. Habilita Google Sheets API y Google Drive API
4. Crea un Service Account, descarga el JSON de credenciales
5. Copia el `client_email` del JSON
6. En tu Google Sheet, comparte con ese email (permiso Editor)

### 3. Configurar `secrets.toml`

Crea `.streamlit/secrets.toml`:

```toml
[gcp_service_account]
type = "service_account"
project_id = "tu-project-id"
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "..."
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."

[sheets]
sheet_id = "TU_GOOGLE_SHEET_ID_AQUI"
```

### 4. Deploy a Streamlit Cloud

1. Sube el repo a GitHub: `pabloorozco-cmd/finanzas-familiares`
2. En [share.streamlit.io](https://share.streamlit.io), conecta el repo
3. Pega el contenido de `secrets.toml` en Settings → Secrets
4. Deploy

## Actualizar el sheet automáticamente

Si el sheet quedó con datos viejos o desincronizado con la realidad, podés correr:

```bash
python scripts/actualizar_sheets.py
```

Eso sincroniza las hojas `Config` y `Plan_Tarjeta` con los valores correctos. No toca `Transacciones` ni `Categorias`.

## Estructura

```
finanzas-familiares/
├── streamlit_app.py            # Dashboard principal
├── pages/
│   ├── 0_Diagnostico           # Diagnóstico de conectividad
│   ├── 1_Registrar.py          # Formulario rápido
│   ├── 2_Plan_Tarjeta.py       # Progreso del plan
│   ├── 3_Gastos_Hormiga.py     # Análisis hormiga
│   ├── 4_Historico.py          # Comparativo mes a mes
│   └── 5_Configuracion.py      # Categorías y parámetros
├── helpers/
│   ├── __init__.py
│   ├── sheets.py               # CRUD Google Sheets
│   ├── calc.py                 # Cálculos: saldos, hormigas
│   └── theme.py                # Diseño visual
├── scripts/
│   └── actualizar_sheets.py    # Sincroniza Config + Plan_Tarjeta
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml            # NO subir a git
├── requirements.txt
├── .gitignore
└── README.md
```

## Cómo se usa

1. **Cada vez que pagas algo:** abres la app en el celular → página "➕ Registrar" → llenas 4 campos en 10 segundos
2. **Una vez al mes:** vas a "💳 Plan Tarjeta" y marcas el pago real del mes
3. **Cuando quieras revisar:** dashboard te dice el estado del mes en curso
4. **Para detectar fugas:** "🐜 Gastos Hormiga" te muestra todo lo chiquito acumulado

## Nota sobre el cálculo de saldo

El módulo `helpers/calc.py` usa un cálculo simplificado:

```
saldo_actual = saldo_inicial - total_pagado
```

Este cálculo **no resta intereses dinámicamente**: asume que el `saldo_inicial_tarjeta` ya es el saldo real al momento del plan, y que los `pago_planeado` reflejan los montos reales que vas a transferir al banco. La diferencia entre `Σ(pago_planeado)` y `saldo_inicial_tarjeta` representa los cargos proyectados del banco (intereses + IVA + visacuota + gestión).

Por eso al final del plan el "avance" puede mostrar más de 100% — esa diferencia son los cargos del banco que efectivamente pagaste de más.

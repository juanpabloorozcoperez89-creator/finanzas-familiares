[README.md](https://github.com/user-attachments/files/28313691/README.md)
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

Llena con el plan optimizado (7 meses):

| mes_num | mes_label | saldo_inicial_plan | pago_planeado | pago_real | fecha_pago_real | notas |
|---|---|---|---|---|---|---|
| 1 | Jun 2026 | 39671.28 | 5500.00 | | | Cuota base |
| 2 | Jul 2026 | 35837.47 | 13000.00 | | | Bono 14 completo (Q7,500) |
| 3 | Ago 2026 | 24342.65 | 5500.00 | | | Cuota base |
| 4 | Sep 2026 | 19865.04 | 5500.00 | | | Cuota base |
| 5 | Oct 2026 | 15199.37 | 5500.00 | | | Cuota base |
| 6 | Nov 2026 | 10337.74 | 5500.00 | | | Cuota base |
| 7 | Dic 2026 | 5271.93 | 5493.35 | | | Cierre con aguinaldo (sobra Q9,506) |

**Hoja: `Config`**
```
clave | valor
```

| clave | valor |
|---|---|
| saldo_inicial_tarjeta | 39671.28 |
| tasa_mensual | 0.0375 |
| iva | 0.12 |
| umbral_hormiga_default | 200 |
| meta_ingresos_mes | 25541.40 |

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

## Estructura

```
finanzas-familiares/
├── streamlit_app.py            # Dashboard principal
├── pages/
│   ├── 1_➕_Registrar.py        # Formulario rápido
│   ├── 2_💳_Plan_Tarjeta.py    # Progreso del plan
│   ├── 3_🐜_Gastos_Hormiga.py  # Análisis hormiga
│   ├── 4_📈_Histórico.py       # Comparativo mes a mes
│   └── 5_⚙️_Configuración.py   # Categorías y parámetros
├── helpers/
│   ├── __init__.py
│   ├── sheets.py               # CRUD Google Sheets
│   └── calc.py                 # Cálculos: saldos, hormigas
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

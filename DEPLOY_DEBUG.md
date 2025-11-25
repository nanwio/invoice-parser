# Desplegar con Debug OCR Habilitado

## Cambios Realizados

1. ✅ Añadido `DIRECT_DEBIT` y `CHECK` al enum `BankPaymentMethod`
2. ✅ Añadida variable `DEBUG_OCR_OUTPUT` en settings
3. ✅ Logging completo de OCR en `invoice_processor.py`

## Deploy a Cloud Run con Debug

```bash
# 1. Build y push de la imagen
gcloud builds submit --tag gcr.io/[PROJECT_ID]/invoice-parser

# 2. Deploy con variable DEBUG_OCR_OUTPUT=true
gcloud run deploy invoice-parser-api \
  --image gcr.io/[PROJECT_ID]/invoice-parser \
  --platform managed \
  --region europe-west4 \
  --allow-unauthenticated \
  --set-env-vars="DEBUG_OCR_OUTPUT=true" \
  --memory 4Gi \
  --cpu 2 \
  --timeout 300 \
  --gpu 1 \
  --gpu-type nvidia-l4
```

## Probar Factura #3 (Marly)

```bash
export TOKEN="tu-token-jwt"
export RUTA="/Users/nanwio/Development/Personal/invoice-parser/facturas/varios_igic/3.pdf"

curl -X POST "https://[TU-URL]/api/v1/invoice/parse?mode=ocr" \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@$RUTA"
```

## Ver Logs con OCR Completo

```bash
# Tail de logs en tiempo real
gcloud logging tail "resource.type=cloud_run_revision" \
  --project=[PROJECT_ID] \
  --format=json

# O buscar logs específicos
gcloud logging read "resource.type=cloud_run_revision AND textPayload=~'FULL OCR OUTPUT'" \
  --limit 50 \
  --format json \
  --project=[PROJECT_ID]
```

## Análisis del Output OCR

Una vez en los logs, busca:

1. **"OCR summary:"** → Número de páginas y tablas detectadas
2. **"FULL OCR OUTPUT:"** → Texto completo que recibe Gemini
3. **"TABLE X (Page Y)"** → Formato TOON de cada tabla

Con esto veremos:
- ¿Cuántos items detecta PaddleOCR en la tabla?
- ¿Están los headers correctos (DESCRIPCION, CANTIDAD, PRECIO)?
- ¿Faltan filas de la tabla?

## Deshabilitar Debug Después

```bash
gcloud run services update invoice-parser-api \
  --region europe-west4 \
  --remove-env-vars="DEBUG_OCR_OUTPUT"
```

## Alternativa: Ver Logs desde Console

1. Google Cloud Console → Cloud Run
2. Selecciona `invoice-parser-api`
3. Tab "Logs"
4. Filtra por: `textPayload:"FULL OCR OUTPUT"`

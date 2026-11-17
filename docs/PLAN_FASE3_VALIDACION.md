# Fase 3 — Validación contra ejemplos publicados (plan y bitácora de fuentes)

Solicitud del usuario (13/11/2026): validar y ajustar todas las calculadoras «al 100 % usables», tomando ejemplos de libros
de cálculo o normas resueltos de modo profesional. Decisiones del usuario:

- Viga: revisión con **AISC 360-22 y NTC-DCEA 2023 (CDMX)**, ambas.
- Silo: **solo predimensionamiento** (marcar «no apto para diseño estructural»; sin pandeo).

Criterio de entrega: cada calculadora queda VALIDADA BAJO CONDICIONES DOCUMENTADAS solo si reproduce un ejemplo resuelto
publicado (o una tabla oficial) dentro de una tolerancia declarada. Lo que no tenga fuente pública se declara.

## Fuentes encontradas

### Helicoidal — KWS Screw Conveyor Engineering Guide (público, kwsmfg.com) y catálogo Martin (CEMA 350)
- FHP = L·S·DF·HBF / 1 000 000 ; MHP = CP·L·MF·SF·PF / 1 000 000 (CP en lb/h = CFH·W) ; TSHP = (FHP + MHP corregida)/e
- DF: 4"→12, 6"→18, 9"→31, 12"→55, 14"→78, 16"→106, 18"→135, 20"→165, 24"→235, 30"→377, 36"→549
- HBF: bolas/rodillos/sin colgante 1.0; bronce o madera 1.7; plástico/nylon/UHMW/teflón 2.0; hierro duro/stellite 4.4
- Factor de hélice especial (15/30/45 %): cortada 1.10/1.15/1.20; cortada y doblada NR/1.50/1.70; cinta 1.05/1.14/1.20
- Paletas por paso 1/2/3/4: 1.29/1.58/1.87/2.16
- e típica 0.88 (85–95 %); KWS no recomienda e > 0.93
- Sobrecarga: KWS corrige MHP < 5 HP con gráfica (sin valores numéricos públicos). CEMA/Martin Tabla 1-16: Fo de 3.0 a 1.0
  en escala logarítmica; Fo = 1.0 para HPf + HPm > 5.2.
- Ejemplo KWS: harina de maíz 25 600 lb/h, 32–40 lb/ft³, carga 30A, MF 0.5, 12", 12.9 ft³/h por rpm, L = 16 ft,
  62 rpm, DF 55, HBF 1.7 (madera), MHP = 0.21 HP, MHP corregida 0.5, e = 0.88, motor 1 HP a 60 rpm.

### Viga — AISC
- AISC «First Semester Design Examples v16.0» (aisc.org, público): ejemplos F.1-1A/B, F.1-2A/B, F.1-3A/B, F.3A/B, F.6, F.7…
- AISC 360-22 (público en aisc.org).

### Colector — EPA Air Pollution Control Cost Manual, Sección 6, Cap. 1 «Baghouses and Filters» (público, epa.gov):
  relación gas/tela por tipo de polvo y método de limpieza.

## Avance
- [x] Viga: nucleo/acero.py (AISC 360-22 F2, F3, F8, F11, G2, G5; NTC 6.2, 6.3, 7.2). tests/test_acero.py reproduce
  F.1-1B (φMn 379), F.1-2B (Lp 5.83 ft, Lr 203 in, Cb 1.01, Mn 338 ±1 %), F.1-3B (Cb 1.30, Fcr 43.2 ksi, Mn 320),
  F.3B (Mn 442), G.1B (φVn 306). NTC: Me = momento crítico clásico (coincide con AISC F2-4); edición 2023 no
  disponible → nota en la calculadora.

### Helicoidal — datos KWS adicionales (kwsmfg.com, «Screw Conveyor Capacity» y «Bulk Material Table»)
- Capacidad (máx rpm / ft³/h a máx rpm / ft³/h a 1 rpm) por carga 15 %, 30A, 30B, 45 % y diámetro 4"–36" (tabla completa
  transcrita en calculadoras/calculos/helicoidal.py).
- CF1 paso: estándar 1.00, corto 1.50, medio 2.00, largo 0.67. CF2 cortada 1.92/1.57/1.43 (15/30/45 %), cortada y doblada
  X/3.75/2.54. CF3 paletas 1–4 por paso: 1.08/1.16/1.24/1.32. SC = CFH·CF1·CF2·CF3; N = SC / capacidad a 1 rpm.
- Materiales (densidad lb/ft³, carga, MF): ver MATERIALES en helicoidal.py.
- Fo: gráfica CEMA (Martin Tabla 1-16) de 3.0 a 1.0; Fo = 1 para HPf + HPm > 5.2 → aproximación log-lineal (nivel E).
- [x] Helicoidal reescrito con el método KWS/CEMA; validado contra el ejemplo KWS (62 rpm, MHP 0.21 HP, motor 1 HP).

## Avance al 13/11/2026 (versión 2.1.0)
- [x] Viga AISC/NTC — [x] Helicoidal KWS/CEMA — [x] Bomba Crane/NPSHa — [x] Ductos ASHRAE/ACGIH — [x] Soplador
- [x] Vacío — [x] Colector EPA — [x] Banda ISO 5048 — [x] Elevador KWS — [x] Torre Merkel — [x] Silo (predimensionamiento)
- [x] Plataforma: datos del proyecto e historial
- [ ] Pendientes sin ejemplo público de extremo a extremo: aerodeslizador, neumático, tolva, secador.

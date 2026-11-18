# Registro de pruebas de validación matemática

Fecha: 2026-11-18T13:43:59  
Comprobaciones numéricas: 185 — aprobadas: 185 — fallidas: 0

| Prueba | Comprobación | Esperado | Obtenido | Error abs. | Error rel. | Tolerancia | Referencia | Estado |
|---|---|---|---|---|---|---|---|---|
| test_ach | Q por ACH | 1.6666667 | 1.6666667 | 0 | 0 | rel 1e-12 | Q = V·ACH/3600 | APROBADA |
| test_ach_volume_override | Q por ACH con volumen | 1 | 1 | 0 | 0 | rel 1e-12 | Q = V·ACH/3600 | APROBADA |
| test_dilution | Q dilución | 6 | 6 | 0 | 0 | rel 1e-12 | Q = K·G/(C − Cb) | APROBADA |
| test_dilution | Q dilución con captura y fondo | 2.5 | 2.5 | 0 | 0 | rel 1e-12 | Q = K·G(1−ηc)/(C − Cb) | APROBADA |
| test_dilution_transient | C(t) mezcla perfecta | 18.55374 | 18.55374 | 0 | 0 | rel 1e-12 | Solución analítica EDO lineal | APROBADA |
| test_dilution_transient | t para C = 10 | 549.30614 | 549.30614 | 0 | 0 | rel 1e-12 | Solución analítica | APROBADA |
| test_thermal | ṁ aire seco | 1.9880716 | 1.9880716 | 0 | 0 | rel 1e-09 | ṁ = q/(cp·Δt), cp = 1006 J/(kg·K) | APROBADA |
| test_thermal | Q entrada | 1.6791739 | 1.6791739 | 0 | 0 | rel 1e-09 | Q = ṁ·v | APROBADA |
| test_thermal | Q forma simplificada | 1.6791739 | 1.6791739 | 0 | 0 | rel 1e-09 | Q = q/(ρ cp Δt) | APROBADA |
| test_occupancy | Voz 62.1 | 0.1 | 0.1 | 0 | 0 | rel 1e-12 | Vbz = Rp·Pz + Ra·Az; Voz = Vbz/Ez | APROBADA |
| test_hood_openings[exterior_plain-0.49999999999999994] | Q exterior_plain | 0.5 | 0.5 | 0 | 0 | rel 1e-12 | DallaValle / ACGIH | APROBADA |
| test_hood_openings[exterior_flanged-0.37499999999999994] | Q exterior_flanged | 0.375 | 0.375 | 0 | 0 | rel 1e-12 | DallaValle / ACGIH | APROBADA |
| test_hood_openings[bench_plain-0.27499999999999997] | Q bench_plain | 0.275 | 0.275 | 0 | 0 | rel 1e-12 | DallaValle / ACGIH | APROBADA |
| test_hood_openings[bench_flanged-0.20625] | Q bench_flanged | 0.20625 | 0.20625 | 0 | 0 | rel 1e-12 | DallaValle / ACGIH | APROBADA |
| test_hood_slots_booth_canopy | Q ranura | 0.555 | 0.555 | 0 | 0 | rel 1e-12 | Q = 3.7·L·V·X | APROBADA |
| test_hood_slots_booth_canopy | Q ranura con brida | 0.39 | 0.39 | 0 | 0 | rel 1e-12 | Q = 2.6·L·V·X | APROBADA |
| test_hood_slots_booth_canopy | Q cabina | 1.2 | 1.2 | 0 | 0 | rel 1e-12 | Q = V·W·H | APROBADA |
| test_hood_slots_booth_canopy | Q dosel | 2.24 | 2.24 | 0 | 0 | rel 1e-12 | Q = 1.4·P·D·V | APROBADA |
| test_hood_imperial_example | Q campana IP | 1100 | 1100 | 2.27e-13 | 2.07e-16 | rel 1e-12 | Ecuación de DallaValle en unidades IP | APROBADA |
| test_ce_fh | Fh(Ce=0.72) | 0.92901235 | 0.92901235 | 0 | 0 | rel 1e-12 | Fh = (1 − Ce²)/Ce² | APROBADA |
| test_ce_fh | Ce(Fh=0.49) | 0.81923192 | 0.81923192 | 0 | 0 | rel 1e-12 | Ce = √(1/(1+Fh)) | APROBADA |
| test_hood_static_pressure | SPh = (1 + Fh)·VPd | 226.45285 | 226.45285 | 0 | 0 | rel 1e-12 | ACGIH | APROBADA |
| test_hood_static_pressure | Ce efectivo | 0.81923192 | 0.81923192 | 0 | 0 | rel 1e-12 | Ce = √(VP/SPh) | APROBADA |
| test_hood_static_pressure | pérdida compuesta ranura | 705.49544 | 705.49544 | 0 | 0 | rel 1e-12 | he = Fs·VPs + Fd·VPd | APROBADA |
| test_geometry | A circular D=0.3 | 0.070685835 | 0.070685835 | 0 | 0 | rel 1e-15 | πD²/4 | APROBADA |
| test_geometry | A rectangular 0.4×0.2 | 0.08 | 0.08 | 1.39e-17 | 1.73e-16 | rel 1e-15 | a·b | APROBADA |
| test_geometry | Dh rectangular 0.4×0.2 | 0.26666667 | 0.26666667 | 0 | 0 | rel 1e-15 | 4A/P | APROBADA |
| test_geometry | Dh circular = D | 0.3 | 0.3 | 0 | 0 | rel 1e-15 | 4(πD²/4)/(πD) | APROBADA |
| test_geometry | De Huebscher cuadrado = 1.0932·a | 0.54658267 | 0.54658267 | 0 | 0 | rel 1e-12 | De = 1.30(ab)^0.625/(a+b)^0.25 | APROBADA |
| test_geometry | De Huebscher 0.4×0.2 | 0.30467497 | 0.30467497 | 0 | 0 | rel 1e-12 | Huebscher (1948) | APROBADA |
| test_rounding_rules | redondeo inferior | 0.16 | 0.16 | 0 | 0 | rel 1e-12 | Serie | APROBADA |
| test_rounding_rules | redondeo superior | 0.18 | 0.18 | 0 | 0 | rel 1e-12 | Serie | APROBADA |
| test_rounding_rules | redondeo cercano | 0.15 | 0.15 | 0 | 0 | rel 1e-12 | Serie | APROBADA |
| test_size_by_velocity | D velocidad constante | 0.25231325 | 0.25231325 | 0 | 0 | rel 1e-12 | D = √(4Q/(πV)) | APROBADA |
| test_size_by_velocity | V resultante | 20 | 20 | 0 | 0 | rel 1e-12 | Continuidad | APROBADA |
| test_size_by_friction_reproduces_target | ΔP/L recalculada = objetivo | 4 | 4 | 5.33e-11 | 1.33e-11 | rel 1e-06 | Darcy-Weisbach + Colebrook recalculados | APROBADA |
| test_static_regain_balance | recuperación estática R·ΔVP = pérdidas | 19.735091 | 19.735091 | 9.09e-13 | 4.61e-14 | rel 1e-05 | Balance del método | APROBADA |
| test_reynolds | Re | 200000 | 200000 | 2.91e-11 | 1.46e-16 | rel 1e-12 | Re = ρVD/μ | APROBADA |
| test_laminar | f laminar Re=1000 | 0.064 | 0.064 | 0 | 0 | rel 1e-12 | 64/Re | APROBADA |
| test_colebrook_vs_bisection[5000.0-0.0] | Colebrook Re=5000 εr=0 | 0.037392728 | 0.037392728 | 6.39e-15 | 1.71e-13 | rel 1e-10 | Colebrook resuelto por bisección (Brent) | APROBADA |
| test_colebrook_vs_bisection[10000.0-0.0001] | Colebrook Re=10000 εr=0.0001 | 0.031037212 | 0.031037212 | 2.21e-15 | 7.11e-14 | rel 1e-10 | Colebrook resuelto por bisección (Brent) | APROBADA |
| test_colebrook_vs_bisection[100000.0-0.0001] | Colebrook Re=100000 εr=0.0001 | 0.018513866 | 0.018513866 | 8.57e-16 | 4.63e-14 | rel 1e-10 | Colebrook resuelto por bisección (Brent) | APROBADA |
| test_colebrook_vs_bisection[1000000.0-0.001] | Colebrook Re=1e+06 εr=0.001 | 0.019943466 | 0.019943466 | 1.73e-17 | 8.7e-16 | rel 1e-10 | Colebrook resuelto por bisección (Brent) | APROBADA |
| test_colebrook_vs_bisection[10000000.0-1e-05] | Colebrook Re=1e+07 εr=1e-05 | 0.0089957117 | 0.0089957117 | 4.75e-16 | 5.28e-14 | rel 1e-10 | Colebrook resuelto por bisección (Brent) | APROBADA |
| test_colebrook_vs_bisection[300000.0-0.005] | Colebrook Re=300000 εr=0.005 | 0.030689305 | 0.030689305 | 3.47e-18 | 1.13e-16 | rel 1e-10 | Colebrook resuelto por bisección (Brent) | APROBADA |
| test_explicit_correlations[10000.0-0.0001] | Haaland vs Colebrook | 0.030990343 | 0.031037212 | 4.69e-05 | 0.00151 | rel 0.02 | Haaland (1983), ±2 % | APROBADA |
| test_explicit_correlations[10000.0-0.0001] | Swamee-Jain vs Colebrook | 0.031037212 | 0.0311487 | 0.000111 | 0.00359 | rel 0.015 | Swamee-Jain declara ≈±1 % | APROBADA |
| test_explicit_correlations[10000.0-0.0001] | Churchill vs Colebrook | 0.031037212 | 0.031178157 | 0.000141 | 0.00454 | rel 0.03 | Churchill (1977) | APROBADA |
| test_explicit_correlations[100000.0-0.001] | Haaland vs Colebrook | 0.021966214 | 0.022174536 | 0.000208 | 0.00948 | rel 0.02 | Haaland (1983), ±2 % | APROBADA |
| test_explicit_correlations[100000.0-0.001] | Swamee-Jain vs Colebrook | 0.022174536 | 0.022342412 | 0.000168 | 0.00757 | rel 0.015 | Swamee-Jain declara ≈±1 % | APROBADA |
| test_explicit_correlations[100000.0-0.001] | Churchill vs Colebrook | 0.022174536 | 0.022343236 | 0.000169 | 0.00761 | rel 0.03 | Churchill (1977) | APROBADA |
| test_explicit_correlations[1000000.0-0.0001] | Haaland vs Colebrook | 0.01332616 | 0.013441438 | 0.000115 | 0.00865 | rel 0.02 | Haaland (1983), ±2 % | APROBADA |
| test_explicit_correlations[1000000.0-0.0001] | Swamee-Jain vs Colebrook | 0.013441438 | 0.013507703 | 6.63e-05 | 0.00493 | rel 0.015 | Swamee-Jain declara ≈±1 % | APROBADA |
| test_explicit_correlations[1000000.0-0.0001] | Churchill vs Colebrook | 0.013441438 | 0.013508203 | 6.68e-05 | 0.00497 | rel 0.03 | Churchill (1977) | APROBADA |
| test_explicit_correlations[10000000.0-0.001] | Haaland vs Colebrook | 0.019701935 | 0.019667052 | 3.49e-05 | 0.00177 | rel 0.02 | Haaland (1983), ±2 % | APROBADA |
| test_explicit_correlations[10000000.0-0.001] | Swamee-Jain vs Colebrook | 0.019667052 | 0.019686172 | 1.91e-05 | 0.000972 | rel 0.015 | Swamee-Jain declara ≈±1 % | APROBADA |
| test_explicit_correlations[10000000.0-0.001] | Churchill vs Colebrook | 0.019667052 | 0.019677462 | 1.04e-05 | 0.000529 | rel 0.03 | Churchill (1977) | APROBADA |
| test_smooth_pipe_prandtl | tubo liso Re=1e5 (Prandtl–Kármán) | 0.017992594 | 0.017989773 | 2.82e-06 | 0.000157 | rel 0.01 | 1/√f = 2 log(Re√f) − 0.8 | APROBADA |
| test_fanning_darcy | Fanning = Darcy/4 | 0.005 | 0.005 | 0 | 0 | rel 1e-15 | Definición | APROBADA |
| test_darcy_weisbach | ΔP Darcy-Weisbach | 40 | 40 | 0 | 0 | rel 1e-12 | ΔP = f(L/D)ρV²/2 | APROBADA |
| test_pressures | VP | 60 | 60 | 0 | 0 | rel 1e-15 | ρV²/2 | APROBADA |
| test_pressures | TP = SP + VP | -140 | -140 | 0 | 0 | rel 1e-15 | Definición | APROBADA |
| test_pressures | FSP = FTP − VPsal | 1410 | 1410 | 0 | 0 | rel 1e-15 | AMCA 210 | APROBADA |
| test_pressures | VP 4005 fpm estándar | 1 | 1 | 0 | 0 | rel 1e-12 | (V/4005)² | APROBADA |
| test_pressures | VP 4005 fpm desde SI (0.075 lb/ft³) | 1 | 0.99922753 | 0.000772 | 0.000772 | rel 0.0015 | Forma (V/4005)² — diferencia por la definición de in.wg | APROBADA |
| test_fittings | ΔP local | 30 | 30 | 0 | 0 | rel 1e-15 | KρV²/2 | APROBADA |
| test_fittings | Borda-Carnot A1/A2=0.5 | 0.25 | 0.25 | 0 | 0 | rel 1e-15 | (1 − A1/A2)² | APROBADA |
| test_fittings | contracción brusca β²=0.5 | 0.25 | 0.25 | 0 | 0 | rel 1e-15 | Crane 0.5(1−β²) | APROBADA |
| test_fittings | difusor 20° | 0.11287132 | 0.11287132 | 0 | 0 | rel 1e-15 | Crane fórmula 3 | APROBADA |
| test_fittings | codo 90° R/D=1.5 (local) | 0.17146428 | 0.17146428 | 0 | 0 | rel 1e-12 | Idelchik A1·B1·C1 | APROBADA |
| test_fittings | codo 45° R/D=2 | 0.0945 | 0.0945 | 1.39e-17 | 1.47e-16 | rel 1e-12 | Idelchik A1 = 0.9 sen δ | APROBADA |
| test_fan_laws | Q ∝ N | 2.4 | 2.4 | 0 | 0 | rel 1e-12 | AMCA 99 | APROBADA |
| test_fan_laws | P ∝ N² | 1440 | 1440 | 0 | 0 | rel 1e-12 | AMCA 99 | APROBADA |
| test_fan_laws | W ∝ N³ | 5184 | 5184 | 9.09e-13 | 1.75e-16 | rel 1e-12 | AMCA 99 | APROBADA |
| test_fan_laws | Q ∝ D³ | 3.456 | 3.456 | 0 | 0 | rel 1e-12 | AMCA 99 | APROBADA |
| test_fan_laws | P ∝ D²ρ | 1080 | 1080 | 0 | 0 | rel 1e-12 | AMCA 99 | APROBADA |
| test_fan_laws | W ∝ D⁵ρ | 5598.72 | 5598.72 | 0 | 0 | rel 1e-12 | AMCA 99 | APROBADA |
| test_fan_laws | velocidad periférica | 47.12389 | 47.12389 | 0 | 0 | rel 1e-12 | U = πDN/60 | APROBADA |
| test_operating_point_analytic | Q operación analítica | 5 | 4.9999993 | 7.07e-07 | 1.41e-07 | rel 0.002 | Solución cerrada Q = √(2000/80) | APROBADA |
| test_operating_point_analytic | P operación | 750 | 750.00035 | 0.000353 | 4.71e-07 | rel 0.005 | 30·Q² | APROBADA |
| test_density_correction | P corregida por densidad | 1350 | 1350 | 0 | 0 | rel 0.001 | P ∝ ρ a Q constante | APROBADA |
| test_bep | Q_BEP | 4 | 3.9983306 | 0.00167 | 0.000417 | rel 0.01 | Máximo de η(Q) = 0.8 − 0.02(Q−4)² | APROBADA |
| test_bep | η_max | 0.8 | 0.79999992 | 8.34e-08 | 1.04e-07 | rel 0.001 | Parábola de eficiencia | APROBADA |
| test_speed_for_design_point | N requerida | 1183.216 | 1183.216 | 6.76e-05 | 5.71e-08 | rel 0.002 | P_k(Q) = 2000k² − 50Q² pasa por (Qd, Pd) | APROBADA |
| test_power_si | P_aire | 7500 | 7500 | 0 | 0 | rel 1e-15 | Q·FTP | APROBADA |
| test_power_si | W ventilador | 10000 | 10000 | 0 | 0 | rel 1e-12 | Q·FTP/η | APROBADA |
| test_power_si | W motor | 10526.316 | 10526.316 | 0 | 0 | rel 1e-12 | W/η_tr | APROBADA |
| test_power_si | P eléctrica | 11441.648 | 11441.648 | 0 | 0 | rel 1e-12 | W_motor/η_m | APROBADA |
| test_power_si | motor normalizado | 15000 | 15000 | 0 | 0 | rel 1e-12 | Serie IEC ≥ 11.58 kW | APROBADA |
| test_power_si | energía anual | 45766.59 | 45766.59 | 0 | 0 | rel 1e-12 | E = P·t | APROBADA |
| test_power_ip_bhp | BHP IP (6356) | 8.9903803 | 8.9993618 | 0.00898 | 0.000999 | rel 0.0015 | BHP = cfm·in.wg/(6356·η); 0.1 % por la definición de in.wg | APROBADA |
| test_power_static_basis | W con base estática | 3142.8571 | 3142.8571 | 0 | 0 | rel 1e-12 | Q·FSP/η_s | APROBADA |
| test_power_static_basis | η total resultante | 0.76363636 | 0.76363636 | 0 | 0 | rel 1e-12 | Q·FTP/W | APROBADA |
| test_air_density_cdmx | ρ a 2240 m, 25 °C, 50 % | 0.89477002 | 0.89453349 | 0.000237 | 0.000264 | rel 0.001 | CoolProp | APROBADA |
| test_critical_path_independent | ΔP tramo R4 | 534.99853 | 534.99853 | 0 | 0 | rel 1e-09 | Recalculo con ecuaciones elementales | APROBADA |
| test_critical_path_independent | ΔP tramo M3 | 1657.7734 | 1657.7734 | 0 | 0 | rel 1e-09 | Recalculo con ecuaciones elementales | APROBADA |
| test_critical_path_independent | ΔP tramo M4 | 17.488461 | 17.488461 | 0 | 0 | rel 1e-09 | Recalculo con ecuaciones elementales | APROBADA |
| test_critical_path_independent | ΔP tramo D1 | 118.12096 | 118.12096 | 0 | 0 | rel 1e-09 | Recalculo con ecuaciones elementales | APROBADA |
| test_critical_path_independent | FTP = Σ pérdidas del camino crítico | 2328.3813 | 2328.3813 | 0 | 0 | rel 1e-09 | Balance de presión total en el camino crítico | APROBADA |
| test_operating_point_on_both_curves | FTP ventilador = FTP sistema en operación | 2369.0257 | 2369.0257 | 1.24e-07 | 5.22e-11 | rel 0.0001 | Intersección de curvas | APROBADA |
| test_operating_point_on_both_curves | continuidad en operación | 2.0107689 | 2.0107689 | 0 | 0 | rel 1e-12 | Σṁ campanas = ṁ ventilador | APROBADA |
| test_power_chain | P_elec = W_vent/(η_tr·η_m) | 7690.0196 | 7690.0196 | 9.09e-13 | 1.18e-16 | rel 1e-12 | Cadena de potencias | APROBADA |
| test_power_chain | P_aire = Q·FTP | 5325.1926 | 5325.1926 | 0 | 0 | rel 1e-12 | Definición | APROBADA |
| test_k_only_split_analytic | Q1 reparto analítico | 0.60355744 | 0.60355744 | 4.4e-12 | 7.29e-12 | rel 1e-06 | Igualdad de ΔP: Q ∝ A/√K | APROBADA |
| test_k_only_split_analytic | Q2 reparto analítico | 0.59644256 | 0.59644256 | 4.4e-12 | 7.37e-12 | rel 1e-06 | Igualdad de ΔP | APROBADA |
| test_k_only_split_analytic | FTP analítica | 617.9655 | 617.9655 | 6.55e-09 | 1.06e-11 | rel 1e-06 | ΔP_ramal + K3·VP3 | APROBADA |
| test_continuity_and_temperature_mixing | continuidad de masa | 1 | 1 | 0 | 0 | rel 1e-15 | Σṁ_entrada = ṁ_salida | APROBADA |
| test_continuity_and_temperature_mixing | temperatura de mezcla | 44 | 44 | 0 | 0 | rel 1e-12 | Mezcla adiabática | APROBADA |
| test_continuity_and_temperature_mixing | ρ aguas abajo | 1.1130289 | 1.1130289 | 0 | 0 | rel 1e-12 | Gas ideal a T_mezcla | APROBADA |
| test_operating_vs_independent_node_solver | ṁ ventilador (2 formulaciones) | 2.0107689 | 2.0107689 | 7.37e-11 | 3.67e-11 | rel 1e-06 | Formulación de nudos independiente (fsolve + bisección por tramo) | APROBADA |
| test_operating_vs_independent_node_solver | ṁ campana H1 | 0.61151657 | 0.61151657 | 2.39e-10 | 3.91e-10 | rel 1e-05 | Formulación de nudos independiente | APROBADA |
| test_operating_vs_independent_node_solver | ṁ campana H2 | 0.35341161 | 0.35341161 | 8.85e-10 | 2.5e-09 | rel 1e-05 | Formulación de nudos independiente | APROBADA |
| test_operating_vs_independent_node_solver | ṁ campana H3 | 0.70263459 | 0.70263459 | 3.38e-11 | 4.82e-11 | rel 1e-05 | Formulación de nudos independiente | APROBADA |
| test_operating_vs_independent_node_solver | ṁ campana H4 | 0.34320608 | 0.34320608 | 5.38e-10 | 1.57e-09 | rel 1e-05 | Formulación de nudos independiente | APROBADA |
| test_design_flow_increase_exact_vs_sqrt | escala exacta = √r (sin fricción) | 1.7320508 | 1.7320508 | 2.22e-15 | 1.28e-15 | rel 1e-08 | ΔP ∝ Q² ⇒ Q_corr = Q·√r | APROBADA |
| test_design_flow_increase_exact_vs_sqrt | presiones igualadas en la unión | -915.0457 | -915.0457 | 2.27e-12 | 2.48e-15 | rel 1e-09 | Balance de presión total | APROBADA |
| test_design_dampers_then_operating_reproduces_design | Q H1 operación = diseño con compuertas | 0.67125 | 0.67125 | 0 | 0 | rel 1e-05 | Consistencia diseño ↔ operación | APROBADA |
| test_design_dampers_then_operating_reproduces_design | Q H2 operación = diseño con compuertas | 0.39 | 0.39 | 0 | 0 | rel 1e-05 | Consistencia diseño ↔ operación | APROBADA |
| test_design_dampers_then_operating_reproduces_design | Q H3 operación = diseño con compuertas | 0.75 | 0.75 | 0 | 0 | rel 1e-05 | Consistencia diseño ↔ operación | APROBADA |
| test_design_dampers_then_operating_reproduces_design | Q H4 operación = diseño con compuertas | 0.38 | 0.38 | 0 | 0 | rel 1e-05 | Consistencia diseño ↔ operación | APROBADA |
| test_project_roundtrip | ida y vuelta JSON: n.º de alternativas | 4 | 4 | 0 | 0 | rel 0 | Persistencia | APROBADA |
| test_flow_cfm | 1 cfm → m³/s | 0.00047194744 | 0.00047194744 | 0 | 0 | rel 1e-15 | Definición ft = 0.3048 m | APROBADA |
| test_flow_cfm | 3600 m³/h → m³/s | 1 | 1 | 0 | 0 | rel 1e-15 | Definición | APROBADA |
| test_velocity_pressure_temperature | 1 fpm → m/s | 0.00508 | 0.00508 | 0 | 0 | rel 1e-15 | Definición | APROBADA |
| test_velocity_pressure_temperature | 1 in.wg (60 °F) → Pa | 248.84 | 248.84 | 0 | 0 | rel 1e-12 | ASHRAE/NIST SP 811 | APROBADA |
| test_velocity_pressure_temperature | 68 °F → °C | 20 | 20 | 0 | 0 | rel 1e-12 | Definición | APROBADA |
| test_velocity_pressure_temperature | 293.15 K → °C | 20 | 20 | 0 | 0 | rel 1e-12 | Definición | APROBADA |
| test_velocity_pressure_temperature | ΔT 9 °F → K | 5 | 5 | 0 | 0 | rel 1e-12 | Definición | APROBADA |
| test_velocity_pressure_temperature | 1 hp → W | 745.69987 | 745.69987 | 0 | 0 | rel 1e-12 | NIST SP 811 | APROBADA |
| test_velocity_pressure_temperature | 0.075 lb/ft³ → kg/m³ | 1.2013848 | 1.2013848 | 4.7e-08 | 3.91e-08 | rel 1e-07 | lb = 0.45359237 kg (exacto) | APROBADA |
| test_roundtrip[flow-cfm] | ida y vuelta cfm | 123.456 | 123.456 | 0 | 0 | rel 1e-12 | Identidad | APROBADA |
| test_roundtrip[pressure-mmH2O] | ida y vuelta mmH2O | 123.456 | 123.456 | 0 | 0 | rel 1e-12 | Identidad | APROBADA |
| test_roundtrip[temperature-\xb0F] | ida y vuelta °F | 123.456 | 123.456 | 0 | 0 | rel 1e-12 | Identidad | APROBADA |
| test_roundtrip[velocity-fpm] | ida y vuelta fpm | 123.456 | 123.456 | 1.42e-14 | 1.15e-16 | rel 1e-12 | Identidad | APROBADA |
| test_roundtrip[friction_rate-in.wg/100ft] | ida y vuelta in.wg/100ft | 123.456 | 123.456 | 0 | 0 | rel 1e-12 | Identidad | APROBADA |
| test_roundtrip[enthalpy-Btu/lb] | ida y vuelta Btu/lb | 123.456 | 123.456 | 0 | 0 | rel 1e-12 | Identidad | APROBADA |
| test_saturation_pressure_independent[-40.0] | pws(-40.0 °C) | 12.841172 | 12.845249 | 0.00408 | 0.000318 | rel 0.0015 | IAPWS 2011 (sublimación del hielo Ih) | APROBADA |
| test_saturation_pressure_independent[-20.0] | pws(-20.0 °C) | 103.23903 | 103.26038 | 0.0213 | 0.000207 | rel 0.0015 | IAPWS 2011 (sublimación del hielo Ih) | APROBADA |
| test_saturation_pressure_independent[-5.0] | pws(-5.0 °C) | 401.74102 | 401.76412 | 0.0231 | 5.75e-05 | rel 0.0015 | IAPWS 2011 (sublimación del hielo Ih) | APROBADA |
| test_saturation_pressure_independent[0.5] | pws(0.5 °C) | 633.78029 | 633.77465 | 0.00564 | 8.9e-06 | rel 0.0015 | CoolProp IAPWS-95 (saturación líquido-vapor) | APROBADA |
| test_saturation_pressure_independent[20.0] | pws(20.0 °C) | 2339.3182 | 2338.8037 | 0.514 | 0.00022 | rel 0.0015 | CoolProp IAPWS-95 (saturación líquido-vapor) | APROBADA |
| test_saturation_pressure_independent[50.0] | pws(50.0 °C) | 12351.946 | 12349.856 | 2.09 | 0.000169 | rel 0.0015 | CoolProp IAPWS-95 (saturación líquido-vapor) | APROBADA |
| test_saturation_pressure_independent[100.0] | pws(100.0 °C) | 101418 | 101418.72 | 0.72 | 7.1e-06 | rel 0.0015 | CoolProp IAPWS-95 (saturación líquido-vapor) | APROBADA |
| test_saturation_pressure_independent[150.0] | pws(150.0 °C) | 476164.54 | 476197.88 | 33.3 | 7e-05 | rel 0.0015 | CoolProp IAPWS-95 (saturación líquido-vapor) | APROBADA |
| test_altitude_first_principles[0.0] | p(Z=0.0) | 101325 | 101325 | 0 | 0 | rel 2e-05 | Hidrostática + gas ideal (US Std. Atmosphere 1976) | APROBADA |
| test_altitude_first_principles[500.0] | p(Z=500.0) | 95460.935 | 95460.812 | 0.123 | 1.28e-06 | rel 2e-05 | Hidrostática + gas ideal (US Std. Atmosphere 1976) | APROBADA |
| test_altitude_first_principles[1000.0] | p(Z=1000.0) | 89874.752 | 89874.519 | 0.232 | 2.58e-06 | rel 2e-05 | Hidrostática + gas ideal (US Std. Atmosphere 1976) | APROBADA |
| test_altitude_first_principles[2240.0] | p(Z=2240.0) | 77155.103 | 77154.65 | 0.453 | 5.87e-06 | rel 2e-05 | Hidrostática + gas ideal (US Std. Atmosphere 1976) | APROBADA |
| test_altitude_first_principles[3000.0] | p(Z=3000.0) | 70108.979 | 70108.422 | 0.557 | 7.94e-06 | rel 2e-05 | Hidrostática + gas ideal (US Std. Atmosphere 1976) | APROBADA |
| test_altitude_ashrae_table | p(2000 m) tabla ASHRAE | 79495 | 79495.124 | 0.124 | 1.56e-06 | rel 5e-05 | ASHRAE Fundamentals cap. 1, tabla 1 | APROBADA |
| test_moist_air_vs_coolprop[20-0-0.5] | W humedad absoluta | 0.0072936977 | 0.0072617372 | 3.2e-05 | 0.00438 | rel 0.006 | CoolProp HAPropsSI (con factor de realce) | APROBADA |
| test_moist_air_vs_coolprop[20-0-0.5] | densidad aire húmedo | 1.1993593 | 1.198898 | 0.000461 | 0.000385 | rel 0.001 | CoolProp HAPropsSI | APROBADA |
| test_moist_air_vs_coolprop[20-0-0.5] | entalpía | 38.622839 | 38.551741 | 0.0711 | 0.00184 | rel 0.006 | CoolProp HAPropsSI | APROBADA |
| test_moist_air_vs_coolprop[20-0-0.5] | punto de rocío [K] | 282.42443 | 282.42239 | 0.00203 | 7.2e-06 | rel 0.0005 | CoolProp HAPropsSI | APROBADA |
| test_moist_air_vs_coolprop[20-0-0.5] | bulbo húmedo [K] | 286.92647 | 286.93355 | 0.00709 | 2.47e-05 | rel 0.0005 | CoolProp HAPropsSI | APROBADA |
| test_moist_air_vs_coolprop[25-2240-0.5] | W humedad absoluta | 0.013091288 | 0.0130414 | 4.99e-05 | 0.00381 | rel 0.006 | CoolProp HAPropsSI (con factor de realce) | APROBADA |
| test_moist_air_vs_coolprop[25-2240-0.5] | densidad aire húmedo | 0.89477002 | 0.89453349 | 0.000237 | 0.000264 | rel 0.001 | CoolProp HAPropsSI | APROBADA |
| test_moist_air_vs_coolprop[25-2240-0.5] | entalpía | 58.54262 | 58.372967 | 0.17 | 0.0029 | rel 0.006 | CoolProp HAPropsSI | APROBADA |
| test_moist_air_vs_coolprop[25-2240-0.5] | punto de rocío [K] | 287.01777 | 287.01397 | 0.0038 | 1.32e-05 | rel 0.0005 | CoolProp HAPropsSI | APROBADA |
| test_moist_air_vs_coolprop[25-2240-0.5] | bulbo húmedo [K] | 290.39535 | 290.39944 | 0.00409 | 1.41e-05 | rel 0.0005 | CoolProp HAPropsSI | APROBADA |
| test_moist_air_vs_coolprop[35-0-0.9] | W humedad absoluta | 0.032889707 | 0.032725701 | 0.000164 | 0.00499 | rel 0.006 | CoolProp HAPropsSI (con factor de realce) | APROBADA |
| test_moist_air_vs_coolprop[35-0-0.9] | densidad aire húmedo | 1.1242661 | 1.1238881 | 0.000378 | 0.000336 | rel 0.001 | CoolProp HAPropsSI | APROBADA |
| test_moist_air_vs_coolprop[35-0-0.9] | entalpía | 119.54374 | 119.18742 | 0.356 | 0.00298 | rel 0.006 | CoolProp HAPropsSI | APROBADA |
| test_moist_air_vs_coolprop[35-0-0.9] | punto de rocío [K] | 306.25956 | 306.25833 | 0.00123 | 4e-06 | rel 0.0005 | CoolProp HAPropsSI | APROBADA |
| test_moist_air_vs_coolprop[35-0-0.9] | bulbo húmedo [K] | 306.60719 | 306.60668 | 0.000505 | 1.65e-06 | rel 0.0005 | CoolProp HAPropsSI | APROBADA |
| test_moist_air_vs_coolprop[5-1500-0.3] | W humedad absoluta | 0.0019382003 | 0.0019312318 | 6.97e-06 | 0.0036 | rel 0.006 | CoolProp HAPropsSI (con factor de realce) | APROBADA |
| test_moist_air_vs_coolprop[5-1500-0.3] | densidad aire húmedo | 1.0582951 | 1.0578182 | 0.000477 | 0.000451 | rel 0.001 | CoolProp HAPropsSI | APROBADA |
| test_moist_air_vs_coolprop[5-1500-0.3] | entalpía | 9.9371921 | 9.8779712 | 0.0592 | 0.00596 | rel 0.006 | CoolProp HAPropsSI | APROBADA |
| test_moist_air_vs_coolprop[5-1500-0.3] | punto de rocío [K] | 263.23008 | 263.22962 | 0.000458 | 1.74e-06 | rel 0.0005 | CoolProp HAPropsSI | APROBADA |
| test_moist_air_vs_coolprop[5-1500-0.3] | bulbo húmedo [K] | 271.99833 | 272.01497 | 0.0166 | 6.12e-05 | rel 0.0005 | CoolProp HAPropsSI | APROBADA |
| test_moist_air_vs_coolprop[60-500-0.2] | W humedad absoluta | 0.027283192 | 0.02712068 | 0.000163 | 0.00596 | rel 0.006 | CoolProp HAPropsSI (con factor de realce) | APROBADA |
| test_moist_air_vs_coolprop[60-500-0.2] | densidad aire húmedo | 0.98255559 | 0.98248218 | 7.34e-05 | 7.47e-05 | rel 0.001 | CoolProp HAPropsSI | APROBADA |
| test_moist_air_vs_coolprop[60-500-0.2] | entalpía | 131.6663 | 131.21549 | 0.451 | 0.00342 | rel 0.006 | CoolProp HAPropsSI | APROBADA |
| test_moist_air_vs_coolprop[60-500-0.2] | punto de rocío [K] | 302.08879 | 302.06556 | 0.0232 | 7.69e-05 | rel 0.0005 | CoolProp HAPropsSI | APROBADA |
| test_moist_air_vs_coolprop[60-500-0.2] | bulbo húmedo [K] | 307.81333 | 307.80592 | 0.00741 | 2.41e-05 | rel 0.0005 | CoolProp HAPropsSI | APROBADA |
| test_viscosity_vs_coolprop[0.0-0.005] | μ(0.0 °C) | 1.7218406e-05 | 1.716e-05 | 5.84e-08 | 0.00339 | rel 0.005 | CoolProp (Lemmon y Jacobsen 2004) | APROBADA |
| test_viscosity_vs_coolprop[20.0-0.005] | μ(20.0 °C) | 1.8205675e-05 | 1.8133221e-05 | 7.25e-08 | 0.00398 | rel 0.005 | CoolProp (Lemmon y Jacobsen 2004) | APROBADA |
| test_viscosity_vs_coolprop[100.0-0.008] | μ(100.0 °C) | 2.1896473e-05 | 2.1733078e-05 | 1.63e-07 | 0.00746 | rel 0.008 | CoolProp (Lemmon y Jacobsen 2004) | APROBADA |
| test_viscosity_vs_coolprop[200.0-0.015] | μ(200.0 °C) | 2.6046119e-05 | 2.5713291e-05 | 3.33e-07 | 0.0128 | rel 0.015 | CoolProp (Lemmon y Jacobsen 2004) | APROBADA |
| test_viscosity_vs_coolprop[400.0-0.025] | μ(400.0 °C) | 3.32839e-05 | 3.2496645e-05 | 7.87e-07 | 0.0237 | rel 0.025 | CoolProp (Lemmon y Jacobsen 2004) | APROBADA |
| test_viscosity_error_impact_on_friction[200.0] | f con μ Sutherland a 200.0 °C | 0.018572345 | 0.018539711 | 3.26e-05 | 0.00176 | rel 0.005 | f con μ de CoolProp | APROBADA |
| test_viscosity_error_impact_on_friction[400.0] | f con μ Sutherland a 400.0 °C | 0.019238119 | 0.019169402 | 6.87e-05 | 0.00357 | rel 0.005 | f con μ de CoolProp | APROBADA |
| test_standard_air | ρ aire estándar ASHRAE seco 20 °C | 1.2041 | 1.2041519 | 5.19e-05 | 4.31e-05 | rel 0.0002 | ASHRAE: aire seco 20 °C, 101.325 kPa = 1.204 kg/m³ | APROBADA |
| test_standard_air | ρ aire estándar AMCA | 1.2 | 1.198898 | 0.0011 | 0.000918 | rel 0.002 | AMCA 210 (≈1.2 kg/m³) | APROBADA |
| test_ppm_conversion | ppm→mg/m³ CO | 1.1449009 | 1.144882 | 1.89e-05 | 1.65e-05 | rel 0.001 | Gas ideal, volumen molar 24.465 L/mol a 25 °C | APROBADA |

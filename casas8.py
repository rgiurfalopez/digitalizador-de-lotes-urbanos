import cv2
import pandas as pd
import numpy as np
import os

# Cargar imagen
ruta_imagen = "girasoles-2.jpg"
imagen_base = cv2.imread(ruta_imagen)
if imagen_base is None:
    raise ValueError("No se pudo cargar la imagen. Verifica el nombre o la ruta.")

alto_orig, ancho_orig = imagen_base.shape[:2]

# Dimensiones de la ventana
ANCHO_VENTANA = 1280
ALTO_VENTANA = 800

# Zoom inicial centrado
zoom = min(ANCHO_VENTANA / ancho_orig, ALTO_VENTANA / alto_orig)
offset = [
    int((ancho_orig * zoom - ANCHO_VENTANA) / 2),
    int((alto_orig * zoom - ALTO_VENTANA) / 2)
]

# Variables de estado
puntos = []
lotes_manzana_actual = []  # Lotes acumulados de la manzana en curso
todas_las_casas = []       # Historial global (se cargará del Excel si existe)

manzana_actual = "S/M"
lote_actual = 1

# Estados para la ventana flotante interactiva en pantalla
modo_ingreso_manzana = False
buffer_texto_mz = ""
modo_ingreso_lote = False
buffer_texto_lt = ""

# Control de mouse y dibujo
arrastrando = False
se_movio = False
inicio_arrastre = (0, 0)
cursor_pantalla = (0, 0)
punto_iman_actual = None
necesita_redibujar = True
vista_cache = None

RADIO_IMAN_PANTALLA = 12  # Distancia en píxeles de pantalla para activar el imán

def cargar_excel_existente():
    """Carga automáticamente el historial previo desde el Excel al iniciar el programa."""
    global todas_las_casas
    nombre_archivo = "coordenadas_casas.xlsx"
    if os.path.exists(nombre_archivo):
        try:
            df = pd.read_excel(nombre_archivo)
            for _, row in df.iterrows():
                mz = str(row['Manzana'])
                lt = int(row['Lote'])
                puntos_casa = [
                    (int(row['XSI1']), int(row['YSI2'])),
                    (int(row['XSD1']), int(row['YSD2'])),
                    (int(row['XID1']), int(row['YID2'])),
                    (int(row['XII1']), int(row['YII2']))
                ]
                todas_las_casas.append({
                    'manzana': mz,
                    'lote': lt,
                    'puntos': puntos_casa
                })
            print(f"📂 Historial cargado con éxito: {len(todas_las_casas)} lotes recuperados de '{nombre_archivo}'.")
        except Exception as e:
            print(f"⚠️ No se pudo leer el Excel existente: {e}")

def buscar_punto_cercano(screen_x, screen_y):
    """Busca si hay un vértice ya registrado cerca del cursor para pegarse (Snapping)."""
    mejor_punto = None
    menor_dist = RADIO_IMAN_PANTALLA

    todos_vertices = [p for c in lotes_manzana_actual + todas_las_casas for p in c['puntos']] + puntos

    for vx, vy in todos_vertices:
        sx = vx * zoom - offset[0]
        sy = vy * zoom - offset[1]
        dist = np.hypot(screen_x - sx, screen_y - sy)
        if dist <= menor_dist:
            menor_dist = dist
            mejor_punto = (vx, vy)

    return mejor_punto

def mostrar_imagen():
    """Recorta, escala con máxima nitidez (Lanczos4) y dibuja polígonos e interfaz."""
    global necesita_redibujar, vista_cache
    if not necesita_redibujar and vista_cache is not None:
        return vista_cache

    lienzo = np.zeros((ALTO_VENTANA, ANCHO_VENTANA, 3), dtype=np.uint8)

    x1_orig = max(0, int(offset[0] / zoom))
    y1_orig = max(0, int(offset[1] / zoom))
    x2_orig = min(ancho_orig, int((offset[0] + ANCHO_VENTANA) / zoom) + 1)
    y2_orig = min(alto_orig, int((offset[1] + ALTO_VENTANA) / zoom) + 1)

    if x2_orig > x1_orig and y2_orig > y1_orig:
        recorte = imagen_base[y1_orig:y2_orig, x1_orig:x2_orig]
        ancho_dest = int((x2_orig - x1_orig) * zoom)
        alto_dest = int((y2_orig - y1_orig) * zoom)

        if ancho_dest > 0 and alto_dest > 0:
            # CORRECCIÓN DE PIXELACIÓN: Usar INTER_LANCZOS4 para evitar dientes de serrucho al hacer zoom
            interpolacion = cv2.INTER_AREA if zoom < 1.0 else cv2.INTER_LANCZOS4
            recorte_escalado = cv2.resize(recorte, (ancho_dest, alto_dest), interpolation=interpolacion)

            pos_x = max(0, int(x1_orig * zoom - offset[0]))
            pos_y = max(0, int(y1_orig * zoom - offset[1]))

            h_pegar = min(alto_dest, ALTO_VENTANA - pos_y)
            w_pegar = min(ancho_dest, ANCHO_VENTANA - pos_x)

            lienzo[pos_y:pos_y+h_pegar, pos_x:pos_x+w_pegar] = recorte_escalado[:h_pegar, :w_pegar]

    # 1. Dibujar historial global ya guardado
    for item in todas_las_casas:
        pts = item['puntos']
        pts_pantalla = [[int(px * zoom - offset[0]), int(py * zoom - offset[1])] for px, py in pts]
        pts_np = np.array(pts_pantalla, np.int32).reshape((-1, 1, 2))

        cv2.polylines(lienzo, [pts_np], isClosed=True, color=(0, 200, 0), thickness=2, lineType=cv2.LINE_AA)

        for sx, sy in pts_pantalla:
            if 0 <= sx < ANCHO_VENTANA and 0 <= sy < ALTO_VENTANA:
                cv2.circle(lienzo, (sx, sy), 2, (0, 150, 0), -1, lineType=cv2.LINE_AA)

        cx = int(sum(p[0] for p in pts_pantalla) / 4)
        cy = int(sum(p[1] for p in pts_pantalla) / 4)
        if 0 <= cx < ANCHO_VENTANA and 0 <= cy < ALTO_VENTANA:
            etiqueta = f"{item['manzana']}-{item['lote']:02d}"
            cv2.putText(lienzo, etiqueta, (cx - 22, cy + 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1, lineType=cv2.LINE_AA)

    # 2. Dibujar polígonos de la manzana actual en curso
    for item in lotes_manzana_actual:
        pts = item['puntos']
        pts_pantalla = [[int(px * zoom - offset[0]), int(py * zoom - offset[1])] for px, py in pts]
        pts_np = np.array(pts_pantalla, np.int32).reshape((-1, 1, 2))

        cv2.polylines(lienzo, [pts_np], isClosed=True, color=(0, 255, 100), thickness=2, lineType=cv2.LINE_AA)

        for sx, sy in pts_pantalla:
            if 0 <= sx < ANCHO_VENTANA and 0 <= sy < ALTO_VENTANA:
                cv2.circle(lienzo, (sx, sy), 2, (0, 220, 0), -1, lineType=cv2.LINE_AA)

        cx = int(sum(p[0] for p in pts_pantalla) / 4)
        cy = int(sum(p[1] for p in pts_pantalla) / 4)
        if 0 <= cx < ANCHO_VENTANA and 0 <= cy < ALTO_VENTANA:
            etiqueta = f"{item['manzana']}-{item['lote']:02d}"
            cv2.putText(lienzo, etiqueta, (cx - 22, cy + 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 40, 40), 1, lineType=cv2.LINE_AA)

    # 3. Dibujar puntos en progreso del lote actual
    if puntos:
        pts_actuales = [[int(px * zoom - offset[0]), int(py * zoom - offset[1])] for px, py in puntos]
        if len(pts_actuales) > 1:
            pts_act_np = np.array(pts_actuales, np.int32).reshape((-1, 1, 2))
            cv2.polylines(lienzo, [pts_act_np], isClosed=False, color=(0, 0, 255), thickness=1, lineType=cv2.LINE_AA)

        for sx, sy in pts_actuales:
            if 0 <= sx < ANCHO_VENTANA and 0 <= sy < ALTO_VENTANA:
                cv2.circle(lienzo, (sx, sy), 3, (0, 0, 255), -1, lineType=cv2.LINE_AA)

    # 4. Indicador visual de Imán (Snapping)
    if punto_iman_actual is not None and not modo_ingreso_manzana and not modo_ingreso_lote:
        ix = int(punto_iman_actual[0] * zoom - offset[0])
        iy = int(punto_iman_actual[1] * zoom - offset[1])
        cv2.circle(lienzo, (ix, iy), 6, (0, 255, 255), 1, lineType=cv2.LINE_AA)

    # 5. Barra superior de estado habitual
    cv2.rectangle(lienzo, (0, 0), (680, 30), (20, 20, 20), -1)
    total_general = len(todas_las_casas) + len(lotes_manzana_actual)
    texto_estado = f"Mz: {manzana_actual} | Lote: {lote_actual:02d} | Acum. Mz: {len(lotes_manzana_actual)} | Total: {total_general}"
    cv2.putText(lienzo, texto_estado, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 0), 1, lineType=cv2.LINE_AA)

    # 6. Ventana flotante interactiva en pantalla si se está ingresando Manzana o Lote
    if modo_ingreso_manzana:
        cv2.rectangle(lienzo, (300, 200), (980, 320), (40, 40, 40), -1)
        cv2.rectangle(lienzo, (300, 200), (980, 320), (0, 255, 255), 2)
        cv2.putText(lienzo, "INGRESE NOMBRE DE MANZANA (Ej: N-NB):", (330, 235), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(lienzo, buffer_texto_mz + "_", (330, 285), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2, cv2.LINE_AA)

    elif modo_ingreso_lote:
        cv2.rectangle(lienzo, (300, 200), (980, 320), (40, 40, 40), -1)
        cv2.rectangle(lienzo, (300, 200), (980, 320), (0, 255, 0), 2)
        cv2.putText(lienzo, "INGRESE NUMERO DE LOTE INICIAL (Ej: 1):", (330, 235), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(lienzo, buffer_texto_lt + "_", (330, 285), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2, cv2.LINE_AA)

    vista_cache = lienzo
    necesita_redibujar = False
    return vista_cache

def click_event(event, x, y, flags, param):
    global puntos, offset, zoom, arrastrando, se_movio, inicio_arrastre
    global necesita_redibujar, lote_actual, punto_iman_actual, cursor_pantalla

    cursor_pantalla = (x, y)

    if modo_ingreso_manzana or modo_ingreso_lote:
        return

    if event == cv2.EVENT_LBUTTONDOWN:
        arrastrando = True
        se_movio = False
        inicio_arrastre = (x, y)

    elif event == cv2.EVENT_MOUSEMOVE:
        if arrastrando:
            dx = x - inicio_arrastre[0]
            dy = y - inicio_arrastre[1]
            if abs(dx) > 4 or abs(dy) > 4 or se_movio:
                se_movio = True
                offset[0] -= dx
                offset[1] -= dy
                inicio_arrastre = (x, y)
                necesita_redibujar = True
        else:
            nuevo_iman = buscar_punto_cercano(x, y)
            if nuevo_iman != punto_iman_actual:
                punto_iman_actual = nuevo_iman
                necesita_redibujar = True

    elif event == cv2.EVENT_LBUTTONUP:
        if arrastrando and not se_movio:
            if punto_iman_actual is not None:
                real_x, real_y = punto_iman_actual
                origen = "🧲 IMÁN"
            else:
                real_x = int((offset[0] + x) / zoom)
                real_y = int((offset[1] + y) / zoom)
                origen = "🟢 NUEVO"

            if 0 <= real_x < ancho_orig and 0 <= real_y < alto_orig:
                puntos.append((real_x, real_y))
                print(f"{origen} Punto {len(puntos)}/4: ({real_x}, {real_y})")

                if len(puntos) == 4:
                    lotes_manzana_actual.append({
                        'manzana': manzana_actual,
                        'lote': lote_actual,
                        'puntos': puntos.copy()
                    })
                    print(f"🏠 Guardado en Mz temporal: Manzana {manzana_actual} - Lote {lote_actual:02d}")
                    lote_actual += 1
                    puntos.clear()

                punto_iman_actual = None
                necesita_redibujar = True

        arrastrando = False
        se_movio = False

    elif event == cv2.EVENT_MOUSEWHEEL:
        zoom_min = min(ANCHO_VENTANA / ancho_orig, ALTO_VENTANA / alto_orig) * 0.5
        zoom_nuevo = min(6.0, zoom * 1.2) if flags > 0 else max(zoom_min, zoom * 0.8)
        factor = zoom_nuevo / zoom
        offset[0] = int((offset[0] + x) * factor - x)
        offset[1] = int((offset[1] + y) * factor - y)
        zoom = zoom_nuevo
        necesita_redibujar = True

# Cargar automáticamente los datos anteriores si el Excel existe
cargar_excel_existente()

cv2.namedWindow("Plano Interactivo", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Plano Interactivo", ANCHO_VENTANA, ALTO_VENTANA)
cv2.setMouseCallback("Plano Interactivo", click_event)

print("=== PLANO ABIERTO EXITOSAMENTE ===")
print("👉 Presiona la tecla 'm' para abrir la ventana flotante y configurar la Manzana en pantalla.")
print("\n=== CONTROLES ===")
print("🖱 Clic izquierdo (rápido): Marcar esquina (se pega con 🧲 si acercas a otra esquina)")
print("🖱 Clic izquierdo (arrastrar): Mover plano | Rueda: Zoom")
print("🔤 Tecla 'm': Abrir ventana flotante para configurar Manzana y Lote inicial")
print("💾 Tecla 'g': Consolidar/Guardar la manzana actual al historial general")
print("↩️ Tecla 'z': Deshacer último punto o último lote de la manzana en curso")
print("🚪 Tecla 'q': Guardar todo en Excel y salir\n")

while True:
    vista = mostrar_imagen()
    cv2.imshow("Plano Interactivo", vista)
    tecla = cv2.waitKey(15) & 0xFF

    if modo_ingreso_manzana:
        if tecla == 13:  # ENTER
            if buffer_texto_mz.strip():
                manzana_actual = buffer_texto_mz.strip().upper()
            modo_ingreso_manzana = False
            buffer_texto_mz = ""
            modo_ingreso_lote = True
            necesita_redibujar = True
        elif tecla == 8 or tecla == 127:  # BACKSPACE
            buffer_texto_mz = buffer_texto_mz[:-1]
            necesita_redibujar = True
        elif 32 <= tecla <= 126:
            buffer_texto_mz += chr(tecla)
            necesita_redibujar = True
        continue

    if modo_ingreso_lote:
        if tecla == 13:  # ENTER
            if buffer_texto_lt.strip().isdigit():
                lote_actual = int(buffer_texto_lt.strip())
            modo_ingreso_lote = False
            buffer_texto_lt = ""
            puntos.clear()
            necesita_redibujar = True
            print(f"✅ Manzana activa: {manzana_actual}, Lote inicial: {lote_actual:02d}")
        elif tecla == 8 or tecla == 127:  # BACKSPACE
            buffer_texto_lt = buffer_texto_lt[:-1]
            necesita_redibujar = True
        elif 48 <= tecla <= 57:
            buffer_texto_lt += chr(tecla)
            necesita_redibujar = True
        continue

    if tecla == ord('m'):
        modo_ingreso_manzana = True
        buffer_texto_mz = ""
        necesita_redibujar = True

    elif tecla == ord('g'):
        if lotes_manzana_actual:
            todas_las_casas.extend(lotes_manzana_actual)
            print(f"\n📦 Manzana '{manzana_actual}' consolidada ({len(lotes_manzana_actual)} lotes). Total general: {len(todas_las_casas)}.")
            lotes_manzana_actual.clear()
            manzana_actual = "S/M"
            lote_actual = 1
            necesita_redibujar = True
            print("👉 Presiona 'm' para configurar la siguiente manzana.")
        else:
            print("\n⚠️ No hay lotes marcados en la manzana actual para guardar.")

    elif tecla == ord('z'):
        if puntos:
            eliminado = puntos.pop()
            print(f"↩️ Punto eliminado: {eliminado}")
        elif lotes_manzana_actual:
            ultimo = lotes_manzana_actual.pop()
            lote_actual = ultimo['lote']
            print(f"↩️ Lote eliminado: {ultimo['manzana']}-{lote_actual:02d}")
        necesita_redibujar = True

    elif tecla == ord('q'):
        if lotes_manzana_actual:
            resp = input(f"\n⚠️ Tienes {len(lotes_manzana_actual)} lotes sin guardar de la manzana '{manzana_actual}'. ¿Deseas incluirlos? (s/n): ").strip().lower()
            if resp == 's':
                todas_las_casas.extend(lotes_manzana_actual)
        break

cv2.destroyAllWindows()

# Guardar coordenadas finales consolidando todo en Excel
if todas_las_casas:
    datos = []
    for i, item in enumerate(todas_las_casas):
        casa = item['puntos']
        mz_lote_formato = f"{item['manzana']}-{item['lote']:02d}"
        datos.append({
            'ID': i + 1,
            'Manzana-Lote': mz_lote_formato,
            'Manzana': item['manzana'],
            'Lote': item['lote'],
            'XSI1': casa[0][0], 'YSI2': casa[0][1],
            'XSD1': casa[1][0], 'YSD2': casa[1][1],
            'XID1': casa[2][0], 'YID2': casa[2][1],
            'XII1': casa[3][0], 'YII2': casa[3][1],
        })

    df = pd.DataFrame(datos)
    df.to_excel("coordenadas_casas.xlsx", index=False)
    print(f"\n✅ {len(todas_las_casas)} lotes guardados exitosamente en 'coordenadas_casas.xlsx'")
else:
    print("\n⚠️ No se registraron lotes.")
    
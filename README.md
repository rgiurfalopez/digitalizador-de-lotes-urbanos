# Digitalizador Interactivo de Lotes Urbanos (`casas8.py`) 📐🗺️

Herramienta de visión artificial e interfaz gráfica desarrollada en **Python** con **OpenCV** para vectorizar y extraer las coordenadas espaciales `(x, y)` de lotes urbanos sobre planos técnicos en imagen, generando una base de datos estructurada en **Excel** lista para sistemas posteriores de visualización y gestión.

---

### ✨ Características Principales

* **Navegación Fluida y Zoom de Alta Nitidez:** Permite arrastrar el plano (*pan*) y hacer zoom centrado en el cursor utilizando interpolación `INTER_LANCZOS4` para evitar la pixelación en planos de alta resolución.
* **Sistema de "Imán" (*Vertex Snapping*):** Detecta automáticamente vértices previamente registrados dentro de un radio de proximidad para unir lotes colindantes con precisión exacta, evitando superposiciones o espacios vacíos.
* **Interfaz Flotante en Pantalla (HUD):** Permite configurar dinámicamente el identificador de **Manzana** y el número de **Lote inicial** mediante cuadros de diálogo integrados en el lienzo, incrementando automáticamente el correlativo tras marcar los 4 vértices de cada lote.
* **Persistencia y Continuidad de Trabajo:** Al iniciar, lee automáticamente el archivo `coordenadas_casas.xlsx` si existe, dibujando el historial previo sobre el plano para continuar la digitalización por etapas sin perder avances.
* **Control de Errores en Tiempo Real:** Función de deshacer (`z`) por vértice individual o por lote completo antes de consolidar la manzana.

---

### 🎮 Controles y Atajos de Teclado

| Acción / Tecla | Función |
| :--- | :--- |
| **Clic Izquierdo (rápido)** | Marca una de las 4 esquinas del lote (activa el imán 🧲 al acercarse a un vértice existente). |
| **Clic Izquierdo (arrastrar)** | Desplaza la vista sobre el plano. |
| **Rueda del Mouse** | Acerca o aleja el zoom sobre la posición del cursor. |
| **Tecla `m`** | Abre la ventana flotante para ingresar el nombre de la **Manzana** y el **Lote inicial**. |
| **Tecla `g`** | Consolida los lotes de la manzana en curso hacia el historial general. |
| **Tecla `z`** | Deshace el último punto marcado o el último lote registrado en la manzana actual. |
| **Tecla `q`** | Guarda todos los registros en `coordenadas_casas.xlsx` y cierra el programa. |

---

### 📊 Estructura de la Base de Datos Generada (`coordenadas_casas.xlsx`)

El script exporta una tabla limpia con los 4 vértices de cada polígono listo para ser consumido por scripts de mapeo automatizado:

| Columna | Descripción |
| :--- | :--- |
| `ID` | Identificador único correlativo |
| `Manzana-Lote` | Código compuesto formateado (ej. `N-NB-01`) |
| `Manzana` / `Lote` | Identificadores separados de manzana y número de lote |
| `XSI1`, `YSI2` | Coordenadas del vértice 1 (Superior Izquierdo) |
| `XSD1`, `YSD2` | Coordenadas del vértice 2 (Superior Derecho) |
| `XID1`, `YID2` | Coordenadas del vértice 3 (Inferior Derecho) |
| `XII1`, `YII2` | Coordenadas del vértice 4 (Inferior Izquierdo) |

---

### 🛠️ Requisitos e Instalación

1. Clonar el repositorio y asegurarse de contar con Python 3.8+.
2. Instalar las dependencias necesarias:
   ```bash
   pip install opencv-python pandas numpy openpyxl

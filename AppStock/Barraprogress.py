# file: progress_bar_financial.py

import tkinter as tk
from tkinter import ttk
import random


class ProgressBar(tk.Frame):
    """
    Widget de Tkinter que muestra una barra de progreso financiera visual.

    Parámetros:
        master: Widget padre
        partida: Valor inicial
        avance: Valor actual alcanzado
        proyeccion: Valor objetivo
        width: Ancho del canvas en píxeles (default: 400)
        height: Alto de la barra en píxeles (default: 40)
        bg_color: Color de fondo
        progress_color: Color de la barra de progreso
        border_color: Color del borde
    """

    def __init__(
        self,
        master=None,
        label="",
        partida=0,
        avance=0,
        proyeccion=100,
        width=400,
        height=40,
        bg_color="#2C3E50",
        progress_color="#27AE60",
        border_color="#ECF0F1",
        **kwargs,
    ):
        super().__init__(master, **kwargs)

        self.label_text = label
        self.label_cavas = None
        self.partida = partida
        self.avance = avance
        self.proyeccion = proyeccion
        self.width = width
        self.height = height
        self.bg_cavas = "#2C3E50"
        self.bg_color = bg_color
        self.progress_color = progress_color
        self.border_color = border_color

        self._create_widgets()
        self.update_values(partida, avance, proyeccion)

    def _create_widgets(self):
        """Crea los widgets internos del componente"""

        # Frame para labels inferiores
        try:
            parent_bg = self.master.cget("bg")
        except:
            parent_bg = "white"

        info_left = tk.Frame(self, bg=parent_bg)
        info_right = tk.Frame(self, bg=parent_bg)
        info_left.pack(side=tk.LEFT)
        info_right.pack(side=tk.RIGHT)

        # label Canvas
        self.label_cavas = tk.Label(
            info_right,
            text=self.label_text,
            font=("Arial", 12),
            bg=self.bg_color,
            fg="#121414",
            anchor=tk.W,
        )
        self.label_cavas.pack(side=tk.LEFT)

        # Canvas para la barra de progreso con sombra
        canvas_container = tk.Frame(info_right, bg=self.bg_cavas, bd=0)
        canvas_container.pack(padx=5, pady=5)

        self.canvas = tk.Canvas(
            canvas_container,
            width=self.width,
            height=self.height,
            bg=self.bg_cavas,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(padx=2, pady=2)

        info_frame = tk.Frame(info_right, bg=parent_bg)
        info_frame.pack(fill=tk.X, padx=5, pady=(0, 0))

        # Labels para mostrar valores con mejor tipografía
        self.label_partida = tk.Label(
            info_frame,
            text="$0",
            font=("Segoe UI", 8),
            bg=self.bg_color,
            fg="#7F8C8D",
            anchor=tk.W,
        )
        self.label_partida.pack(side=tk.LEFT)

        self.label_proyeccion = tk.Label(
            info_frame,
            text="$0",
            font=("Segoe UI", 8),
            bg=self.bg_color,
            fg="#7F8C8D",
            anchor=tk.E,
        )
        self.label_proyeccion.pack(side=tk.RIGHT)

    def update_values(self, partida, avance, proyeccion):
        """
        Actualiza los valores de la barra de progreso.

        Args:
            partida: Valor inicial (puede ser negativo)
            avance: Valor actual alcanzado (puede ser negativo)
            proyeccion: Valor objetivo
        """
        # Permitir valores negativos
        self.partida = partida
        self.avance = avance
        self.proyeccion = proyeccion if proyeccion != 0 else 1

        self._draw_progress_bar()
        self._update_labels()

    def _draw_progress_bar(self):
        """Dibuja la barra de progreso en el canvas con diseño moderno"""
        # Limpiar canvas
        self.canvas.delete("all")

        # Calcular rango total (para manejar valores negativos)
        min_val = min(self.partida, 0, self.avance)
        max_val = max(self.proyeccion, self.partida, self.avance)
        total_range = max_val - min_val if max_val != min_val else 1

        # Calcular posiciones normalizadas (0 a 1)
        zero_position = (0 - min_val) / total_range if total_range > 0 else 0
        avance_position = (self.avance - min_val) / total_range if total_range > 0 else 0

        # Convertir a píxeles
        zero_pixel = int(self.width * zero_position)
        avance_pixel = int(self.width * avance_position)

        # Radio para bordes redondeados
        radius = min(8, self.height // 4)

        # Dibujar fondo de la barra con bordes redondeados
        self._draw_rounded_rect(
            0, 0, self.width, self.height, radius, fill=self.bg_cavas
        )

        # Calcular ancho de la barra (desde 0 hasta avance)
        if self.avance >= 0:
            # Valor positivo: dibuja desde zero_pixel hacia la derecha
            progress_start = zero_pixel
            progress_end = avance_pixel
        else:
            # Valor negativo: dibuja desde avance_pixel hasta zero_pixel
            progress_start = avance_pixel
            progress_end = zero_pixel

        progress_width = abs(progress_end - progress_start)

        # Dibujar línea de cero si hay valores negativos
        if min_val < 0:
            self.canvas.create_line(
                zero_pixel, 0, zero_pixel, self.height,
                fill="#95A5A6", width=2, dash=(3, 3)
            )

        # Dibujar progreso con bordes redondeados
        if progress_width > 5:
            # Color dinámico según si es positivo o negativo
            if self.avance >= 0:
                # Valores positivos en verde
                if self.proyeccion > 0:
                    percent = self.avance / self.proyeccion
                    if percent >= 1.0:
                        color = "#27AE60"  # Verde completo
                    elif percent >= 0.75:
                        color = "#2ECC71"  # Verde claro
                    elif percent >= 0.5:
                        color = "#F39C12"  # Naranja
                    else:
                        color = "#E67E22"  # Naranja oscuro
                else:
                    color = "#27AE60"
            else:
                # Valores negativos en rojo
                color = "#E74C3C"  # Rojo

            # Barra de progreso principal
            self._draw_rounded_rect(
                progress_start, 0, progress_end, self.height, radius, fill=color
            )

            # Efecto de brillo en la parte superior
            self._draw_rounded_rect(
                progress_start,
                0,
                progress_end,
                self.height // 3,
                radius,
                fill=self._lighten_color(color, 60),
            )

            # Sombra interna en la parte inferior
            self.canvas.create_rectangle(
                progress_start,
                self.height * 0.7,
                progress_end,
                self.height,
                fill=self._darken_color(color),
                outline="",
            )

        # Dibujar marcador de inicio (partida) si es diferente de cero
        if self.partida != 0:
            partida_position = (self.partida - min_val) / total_range if total_range > 0 else 0
            partida_pos = int(partida_position * self.width)
            # Línea del marcador
            self.canvas.create_line(
                partida_pos, 3, partida_pos, self.height - 3, fill="#E74C3C", width=3
            )
            # Círculo superior
            self.canvas.create_oval(
                partida_pos - 4,
                -2,
                partida_pos + 4,
                6,
                fill="#E74C3C",
                outline="#C0392B",
                width=1,
            )

        # Dibujar marcador de objetivo (proyección)
        proyeccion_position = (self.proyeccion - min_val) / total_range if total_range > 0 else 1
        proyeccion_pos = int(proyeccion_position * self.width)
        arrow_size = min(12, self.height // 3)
        self.canvas.create_polygon(
            proyeccion_pos - arrow_size,
            self.height // 2 - arrow_size,
            proyeccion_pos - arrow_size,
            self.height // 2 + arrow_size,
            proyeccion_pos - 2,
            self.height // 2,
            fill="#3498DB",
            outline="#2980B9",
            width=2,
        )

        # Texto del valor actual en el centro con sombra
        avance_text = self._format_amount(self.avance)
        percent_text = f"{avance_text}"

        # Determinar posición del texto (en el centro de la barra de progreso)
        text_x = (progress_start + progress_end) // 2 if progress_width > 20 else self.width // 2

        # Sombra del texto
        self.canvas.create_text(
            text_x + 1,
            self.height // 2 + 1,
            text=percent_text,
            font=("Segoe UI", 9, "bold"),
            fill="#000000",
            anchor=tk.CENTER,
        )

        # Texto principal
        text_color = "white" if progress_width > 20 else "#ECF0F1"
        self.canvas.create_text(
            text_x,
            self.height // 2,
            text=percent_text,
            font=("Segoe UI", 9, "bold"),
            fill=text_color,
            anchor=tk.CENTER,
        )

    def _draw_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        """Dibuja un rectángulo con bordes redondeados"""
        points = [
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1,
        ]
        return self.canvas.create_polygon(points, smooth=True, **kwargs)

    def _darken_color(self, color):
        """Oscurece un color hexadecimal"""
        color = color.lstrip("#")
        r, g, b = tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))

        r = max(0, r - 30)
        g = max(0, g - 30)
        b = max(0, b - 30)

        return f"#{r:02x}{g:02x}{b:02x}"

    def _update_labels(self):
        """Actualiza los textos de los labels"""
        percent = (self.avance / self.proyeccion * 100) if self.proyeccion > 0 else 0

        # Determinar color según progreso
        if percent >= 100:
            color = "#27AE60"  # Verde
        elif percent >= 75:
            color = "#F39C12"  # Naranja
        elif percent >= 50:
            color = "#E67E22"  # Naranja oscuro
        else:
            color = "#E74C3C"  # Rojo

        self.label_partida.config(text=f"${self._format_amount(self.partida)}")

        # self.label_avance.config(
        #    text=f"Avance: ${self._format_amount(self.avance)} ({percent:.1f}%)", fg=color
        # )

        self.label_proyeccion.config(text=f"${self._format_amount(self.proyeccion)}")

    def _lighten_color(self, color, amount=40):
        """Aclara un color hexadecimal para efecto de brillo"""
        # Convertir hex a RGB
        color = color.lstrip("#")
        r, g, b = tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))

        # Aclarar (aumentar hacia 255)
        r = min(255, r + amount)
        g = min(255, g + amount)
        b = min(255, b + amount)

        return f"#{r:02x}{g:02x}{b:02x}"

    @staticmethod
    def _clamp(value, min_value, max_value):
        """Limita un valor entre un mínimo y un máximo"""
        return max(min_value, min(value, max_value))

    @staticmethod
    def _format_amount(amount):
        """Formatea un número como cantidad con separadores de miles (maneja negativos)"""
        abs_amount = abs(amount)
        sign = "-" if amount < 0 else ""

        if abs_amount >= 1_000_000:
            return f"{sign}{abs_amount / 1_000_000:.1f}M"
        elif abs_amount >= 1_000:
            return f"{sign}{abs_amount / 1_000:.1f}K"
        else:
            return f"{sign}{abs_amount:,.0f}"


if __name__ == "__main__":
    partida = 0
    avance = -50_000  # Valor negativo de prueba
    proyeccion = 1_000_000

    # Crear ventana de ejemplo
    root = tk.Tk()
    root.title("Barra de Progreso Financiera - Con Valores Negativos")
    root.geometry("600x300")
    root.configure(bg="white")

    # Título
    tk.Label(
        root,
        text="Prueba con valores positivos y negativos",
        font=("Segoe UI", 12, "bold"),
        bg="white"
    ).pack(pady=10)

    # Crear widget de barra de progreso
    progress = ProgressBar(
        root,
        label="Ganancias diaria:",
        partida=0,
        avance=-50_000,
        proyeccion=1_000_000,
        width=300,
        height=15,
        bg_color="white",
    )
    progress.pack(pady=20)

    # Botones para probar actualizaciones
    def update_random():
        # Generar valores aleatorios incluyendo negativos
        new_avance = random.randint(-200_000, 1_000_000)
        progress.update_values(0, new_avance, 1_000_000)

    btn = tk.Button(
        root,
        text="🔄 Actualizar Aleatoriamente",
        command=update_random,
        bg="#3498DB",
        fg="white",
        font=("Segoe UI", 9),
        relief=tk.FLAT,
        padx=20,
        pady=8,
        cursor="hand2",
    )
    btn.pack(pady=10)

    root.mainloop()

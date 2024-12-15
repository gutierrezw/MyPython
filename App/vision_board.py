import tkinter as tk

import numpy as np

from api_io_file import *

global vsn, all_xlis, dis
vrows, vcols = 3, 6
vsn = [[None] * 3 for _ in range(7)]
imagen0, all_xlis = select_objeto(usamodo='visionboard')


def mapa_board() -> list:
    dis = [[0] * 6 for _ in range(3)]
    nro = str(numero_randon(18))
    dig = np.array([d for d in nro if d in '012345'])
    i = 0 if len(dig) == 0 or int(dig[0]) > 2 else int(dig[0])
    j = 0 if len(dig) <= 1 else int(dig[1])
    if i < 2 and j <= 4:
        dis[i][j] = 1
        dis[i][j + 1] = 1
        dis[i + 1][j] = 1
        dis[i + 1][j + 1] = 1
    return dis, i, j


class visionBoard(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.widgets_vision()
        self.update_vision()
        self.config(bg="black")

    def widgets_vision(self):
        global vsn, all_xlis, dis

        imagen, xlis = get_imagen(ix=30)
        (dis, i, j) = mapa_board()
        itrue = True

        for widget in self.winfo_children():
            widget.destroy()

        for i in range(vrows):
            for j in range(vcols):

                if dis[i][j] == 1 and itrue:
                    vsn[j][i] = tk.Label(self, image=None)
                    vsn[j][i].image = None
                    vsn[j][i].grid(row=i, column=j, rowspan=2, columnspan=2, padx=4, pady=10)
                    itrue = False

                if dis[i][j] == 0:
                    vsn[j][i] = tk.Label(self, image=None)
                    vsn[j][i].image = None
                    vsn[j][i].grid(row=i, column=j, padx=4, pady=10)

        self.after(1, self.update_vision)
        return vsn, dis

    def update_vision(self):
        global vsn, all_xlis, dis
        #
        # rescata lista de imagen y toma muestra aleatoria
        #
        slis = list()
        for key in all_xlis:
            slis.append(key['id'])
        random.shuffle(slis)

        i0, itrue = 0, True
        for i in range(vrows):
            for j in range(vcols):
                imagen, tmp = get_imagen(ix=slis[i0])

                if dis[i][j] == 1 and itrue:
                    imagen = imagen.resize((425, 425), Image.ADAPTIVE)
                    imagen_tk = ImageTk.PhotoImage(imagen)
                    vsn[j][i].config(image=imagen_tk, width=425, height=425)
                    vsn[j][i].imagen = imagen_tk
                    vsn[j][i].grid(row=i, column=j, rowspan=2, columnspan=2, padx=4, pady=10)
                    itrue = False

                if dis[i][j] == 0:
                    imagen = imagen.resize((200, 200), Image.ADAPTIVE)
                    imagen_tk = ImageTk.PhotoImage(imagen)
                    vsn[j][i].config(image=imagen_tk, width=200, height=200)
                    vsn[j][i].imagen = imagen_tk

                i0 = 0 if i0 == len(slis)-1 else i0 + 1

        self.after(apilocal['elapse vision'], self.widgets_vision)
        # self.after(3000, self.widgets_vision)
        return vsn

        self.mainloop()


if __name__ == '__main__':
    win = tk.Tk()
    dimension = "%dx%d+0+0" % (dw, dh)
    win.geometry(dimension)
    win.config(bg="black")
    dpn = ttk.Frame(win, style="TFrame", width=df, height=700)
    dpn.grid(pady=40)

    frame_vision = visionBoard(master=dpn)
    frame_vision.pack()
    frame_vision.mainloop()
    win.mainloop()

import tkinter as tk
import tkinter as ttk

root = tk.Tk()
root.geometry("1000x600")

fwin0 = tk.Frame(root, bg="blue")
fwin0.pack(fill='both', expand=True)


fwin1 = tk.Frame(fwin0, bg="green")
#fwin1.pack(side='left', fill='both', expand=True, padx=10, pady=20)
fwin1.grid(row=0, column=0, padx=10, pady=10)
for i in range(10):
     for j in range(8):
         tk.Button(fwin1, text=str(i)+str(j), width=11).grid(row=i, column=j)

fwin2 = tk.Frame(fwin0, bg="white")
#fwin2.pack(side='right', fill='both', expand=True, padx=10, pady=20)
fwin2.grid(row=0, column=1, padx=10, pady=10)
fwin20 = tk.Frame(fwin2, bg="yellow")
fwin20.grid(row=0, column=0, padx=10, pady=10)
for i in range(5):
     for j in range(3):
         tk.Button(fwin20, text=str(i)+str(j), width=11).grid(row=i, column=j)

fwin21 = tk.Frame(fwin2, bg="orange")
fwin21.grid(row=1, column=0, padx=10, pady=10)
for i in range(5):
     for j in range(3):
         tk.Button(fwin21, text=str(i)+str(j), width=11).grid(row=i, column=j)

fwin3 = tk.Frame(fwin0, bg="red")
#fwin3.pack(side='bottom', fill='both', expand=True, padx=10, pady=10)
fwin3.grid(row=1, column=0, columnspan=2, padx=10, pady=10)
for i in range(6):
     for j in range(11):
         tk.Button(fwin3, text=str(i)+str(j), width=11).grid(row=i, column=j)

root.mainloop()

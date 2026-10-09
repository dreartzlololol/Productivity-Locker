import tkinter as tk
from tkinter import messagebox
root = tk.Tk()
root.geometry('200x200')
def click():
    dialog = tk.Toplevel(root)
    dialog.geometry('100x100')
    def do_it():
        dialog.destroy()
        messagebox.showinfo('Title', 'Message', parent=root)
    btn = tk.Button(dialog, text='Do it', command=do_it)
    btn.pack()
tk.Button(root, text='Open', command=click).pack()
root.after(500, click)
root.after(1500, lambda: [d for d in root.winfo_children() if isinstance(d, tk.Toplevel)][0].winfo_children()[0].invoke())
root.after(3000, root.destroy)
root.mainloop()

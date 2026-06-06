import tkinter as tk
from tkinter import messagebox


class EcoLensUI:
    def __init__(self):
        self.root = tk.Tk()

        self.root.title("EcoLens")
        self.root.geometry("800x480")  # Common Pi touchscreen size
        self.root.configure(bg="white")

        self.user_code = tk.StringVar()

        self.build_ui()

    def build_ui(self):
        title = tk.Label(
            self.root,
            text="EcoLens",
            font=("Arial", 24, "bold"),
            bg="white"
        )
        title.pack(pady=20)

        instruction = tk.Label(
            self.root,
            text="Enter User Code",
            font=("Arial", 16),
            bg="white"
        )
        instruction.pack()

        self.code_entry = tk.Entry(
            self.root,
            textvariable=self.user_code,
            font=("Arial", 18),
            width=20,
            justify="center"
        )
        self.code_entry.pack(pady=10)

        self.start_button = tk.Button(
            self.root,
            text="Start Session",
            font=("Arial", 16),
            width=20,
            height=2
        )
        self.start_button.pack(pady=20)

        self.status_label = tk.Label(
            self.root,
            text="Ready",
            font=("Arial", 14),
            bg="white"
        )
        self.status_label.pack(pady=10)

    def get_user_code(self):
        return self.user_code.get().strip()

    def set_status(self, message):
        self.status_label.config(text=message)
        self.root.update()

    def show_success(self, message):
        messagebox.showinfo("EcoLens", message)

    def show_error(self, message):
        messagebox.showerror("EcoLens", message)

    def set_start_callback(self, callback):
        self.start_button.config(command=callback)

    def run(self):
        self.root.mainloop()
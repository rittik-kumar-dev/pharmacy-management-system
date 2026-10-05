# Medicine Shop Management System - app.py
# This is now the ONLY entry point. Run this file.
#
# Architecture: ONE tk.Tk() root window stays alive for the whole
# program. Each "screen" (Login, Dashboard, Medicines) is a Frame
# stacked on top of the others inside self.container. Switching
# screens just raises a different frame to the top (tkraise()) —
# no window is ever destroyed or recreated, so there's no flicker
# or jump, unlike the old approach of spawning a new tk.Tk() per screen.

import tkinter as tk

BG = "#0F1117"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Medicine Shop Management System")
        self.geometry("1100x680+120+60")
        self.minsize(900, 580)
        self.configure(bg=BG)

        # Shared state all frames can read via self.controller.<attr>
        self.admin_username = None

        self.container = tk.Frame(self, bg=BG)
        self.container.pack(fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        self._init_frames()
        self.show_frame("LoginFrame")

    def _init_frames(self):
        # Imported here (not at top of file) to avoid circular imports,
        # since login.py / dashboard.py / main.py don't need to import app.py.
        from login import LoginFrame
        from dashboard import DashboardFrame
        from main import MedicineFrame

        for F in (LoginFrame, DashboardFrame, MedicineFrame):
            frame = F(parent=self.container, controller=self)
            self.frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

    def show_frame(self, name):
        """Switch to a different screen by class name, e.g. 'DashboardFrame'."""
        frame = self.frames[name]
        if hasattr(frame, "on_show"):
            frame.on_show()  # let the frame refresh itself (e.g. reload table/stats)
        frame.tkraise()

    def logout(self):
        """Clears the logged-in admin and returns to the login screen."""
        self.admin_username = None
        self.show_frame("LoginFrame")


if __name__ == "__main__":
    App().mainloop()
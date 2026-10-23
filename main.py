import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime


def initialize_db():
    conn = sqlite3.connect('smart_campus.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password TEXT,
                    role TEXT,
                    campus_id INTEGER)''')

    c.execute('''CREATE TABLE IF NOT EXISTS campuses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    open_hour INTEGER,
                    close_hour INTEGER,
                    max_duration INTEGER)''')

    c.execute('''CREATE TABLE IF NOT EXISTS resources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    campus_id INTEGER,
                    UNIQUE(name, campus_id))''')

    c.execute('''CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    resource_id INTEGER,
                    user_id INTEGER,
                    date TEXT,
                    start_time INTEGER,
                    duration INTEGER)''')

    c.execute("SELECT COUNT(*) FROM campuses")
    if c.fetchone()[0] == 0:
        campuses = [
            ('Johannesburg', 8, 17, 2),
            ('Cape Town', 9, 18, 3),
            ('Durban', 8, 16, 1)
        ]
        c.executemany("INSERT INTO campuses (name, open_hour, close_hour, max_duration) VALUES (?, ?, ?, ?)", campuses)

    c.execute("SELECT COUNT(*) FROM users WHERE role='SystemOperator'")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users (username, password, role) VALUES ('admin', 'admin123', 'SystemOperator')")

    conn.commit()
    conn.close()


class User:
    def __init__(self, user_id, username, role):
        self._user_id = user_id
        self._username = username
        self._role = role

    def get_id(self): return self._user_id

    def get_role(self): return self._role

    def get_username(self): return self._username


class Lecturer(User):
    def __init__(self, user_id, username):
        super().__init__(user_id, username, 'Lecturer')


class CampusAdmin(User):
    def __init__(self, user_id, username, campus_id):
        super().__init__(user_id, username, 'CampusAdmin')
        self._campus_id = campus_id

    def get_campus_id(self): return self._campus_id


class SystemOperator(User):
    def __init__(self, user_id, username):
        super().__init__(user_id, username, 'SystemOperator')


class SmartCampusApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Smart Campus Resource Booking System")
        self.geometry("700x500")
        self.current_user = None

        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True)

        self.frames = {}
        self.show_login_frame()

    def db_query(self, query, params=(), fetch=False, fetchall=False):
        conn = sqlite3.connect('smart_campus.db')
        c = conn.cursor()
        c.execute(query, params)
        result = None
        if fetch:
            result = c.fetchone()
        elif fetchall:
            result = c.fetchall()
        else:
            conn.commit()
        conn.close()
        return result

    def show_frame(self, FrameClass):
        for widget in self.container.winfo_children():
            widget.destroy()
        frame = FrameClass(self.container, self)
        frame.pack(fill="both", expand=True)

    def show_login_frame(self):
        self.current_user = None
        self.show_frame(LoginFrame)


class LoginFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        ttk.Label(self, text="Login", font=("Times New Roman", 18, "bold")).pack(pady=20)

        ttk.Label(self, text="Username:").pack()
        self.entry_user = ttk.Entry(self)
        self.entry_user.pack(pady=5)

        ttk.Label(self, text="Password:").pack()
        self.entry_pass = ttk.Entry(self, show="*")
        self.entry_pass.pack(pady=5)

        ttk.Button(self, text="Login", command=self.login).pack(pady=10)
        ttk.Button(self, text="Register New Lecturer/Admin",
                   command=lambda: controller.show_frame(RegisterFrame)).pack()

    def login(self):
        username = self.entry_user.get()
        password = self.entry_pass.get()

        user_data = self.controller.db_query("SELECT id, role, campus_id FROM users WHERE username=? AND password=?",
                                             (username, password), fetch=True)

        if user_data:
            u_id, role, campus_id = user_data
            if role == 'Lecturer':
                self.controller.current_user = Lecturer(u_id, username)
                self.controller.show_frame(LecturerDashboard)
            elif role == 'CampusAdmin':
                self.controller.current_user = CampusAdmin(u_id, username, campus_id)
                self.controller.show_frame(AdminDashboard)
            elif role == 'SystemOperator':
                self.controller.current_user = SystemOperator(u_id, username)
                self.controller.show_frame(OperatorDashboard)
        else:
            messagebox.showerror("Error", "Invalid credentials")


class RegisterFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        ttk.Label(self, text="Register", font=("Times New Roman", 18, "bold")).pack(pady=10)

        ttk.Label(self, text="Username:").pack()
        self.entry_user = ttk.Entry(self)
        self.entry_user.pack()

        ttk.Label(self, text="Password:").pack()
        self.entry_pass = ttk.Entry(self, show="*")
        self.entry_pass.pack()

        ttk.Label(self, text="Role:").pack()
        self.role_var = tk.StringVar(value="Lecturer")
        ttk.Radiobutton(self, text="Lecturer", variable=self.role_var, value="Lecturer").pack()
        ttk.Radiobutton(self, text="Campus Admin", variable=self.role_var, value="CampusAdmin").pack()

        ttk.Label(self, text="Campus (For Admin only):").pack()
        campuses = self.controller.db_query("SELECT id, name FROM campuses", fetchall=True)
        self.campus_dict = {name: c_id for c_id, name in campuses}
        self.campus_combo = ttk.Combobox(self, values=list(self.campus_dict.keys()), state="readonly")
        self.campus_combo.pack()

        ttk.Button(self, text="Register", command=self.register).pack(pady=10)
        ttk.Button(self, text="Back to Login", command=lambda: controller.show_frame(LoginFrame)).pack()

    def register(self):
        username = self.entry_user.get()
        password = self.entry_pass.get()
        role = self.role_var.get()
        campus_name = self.campus_combo.get()

        campus_id = self.campus_dict.get(campus_name) if role == 'CampusAdmin' else None

        if not username or not password:
            messagebox.showerror("Error", "All fields are required")
            return

        try:
            self.controller.db_query("INSERT INTO users (username, password, role, campus_id) VALUES (?, ?, ?, ?)",
                                     (username, password, role, campus_id))
            messagebox.showinfo("Success", "Registration successful")
            self.controller.show_frame(LoginFrame)
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Username already exists")


class LecturerDashboard(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        ttk.Label(self, text=f"Welcome Lecturer: {self.controller.current_user.get_username()}",
                  font=("Times New Roman", 14)).pack(pady=5)
        ttk.Button(self, text="Logout", command=self.controller.show_login_frame).pack(anchor="ne", padx=10)

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_book = ttk.Frame(notebook)
        self.tab_history = ttk.Frame(notebook)
        notebook.add(self.tab_book, text="Book Resource")
        notebook.add(self.tab_history, text="My History")

        self.setup_booking_tab()
        self.setup_history_tab()

    def setup_booking_tab(self):
        top_frame = ttk.Frame(self.tab_book)
        top_frame.pack(fill="x", pady=5)

        ttk.Label(top_frame, text="Select Campus:").pack(side="left")
        campuses = self.controller.db_query("SELECT id, name FROM campuses", fetchall=True)
        self.campus_dict = {name: c_id for c_id, name in campuses}
        self.campus_combo = ttk.Combobox(top_frame, values=list(self.campus_dict.keys()), state="readonly")
        self.campus_combo.pack(side="left", padx=5)
        self.campus_combo.bind("<<ComboboxSelected>>", self.load_resources)

        self.policy_lbl = ttk.Label(self.tab_book, text="Booking Policy: Select a campus", foreground="blue")
        self.policy_lbl.pack()

        ttk.Label(self.tab_book, text="Select Resource:").pack()
        self.resource_combo = ttk.Combobox(self.tab_book, state="readonly")
        self.resource_combo.pack(pady=5)

        form_frame = ttk.Frame(self.tab_book)
        form_frame.pack(pady=10)

        ttk.Label(form_frame, text="Date (YYYY-MM-DD):").grid(row=0, column=0, padx=5, pady=5)
        self.date_entry = ttk.Entry(form_frame)
        self.date_entry.insert(0, datetime.today().strftime('%Y-%m-%d'))
        self.date_entry.grid(row=0, column=1)

        ttk.Label(form_frame, text="Start Hour (0-23):").grid(row=1, column=0, padx=5, pady=5)
        self.start_entry = ttk.Entry(form_frame)
        self.start_entry.grid(row=1, column=1)

        ttk.Label(form_frame, text="Duration (hours):").grid(row=2, column=0, padx=5, pady=5)
        self.dur_entry = ttk.Entry(form_frame)
        self.dur_entry.grid(row=2, column=1)

        ttk.Button(self.tab_book, text="Make Booking", command=self.make_booking).pack(pady=10)

    def load_resources(self, event=None):
        campus_id = self.campus_dict[self.campus_combo.get()]
        rules = self.controller.db_query("SELECT open_hour, close_hour, max_duration FROM campuses WHERE id=?",
                                         (campus_id,), fetch=True)
        self.policy_lbl.config(text=f"Policy: Open {rules[0]}:00 to {rules[1]}:00 | Max {rules[2]} hrs per booking")

        resources = self.controller.db_query("SELECT id, name FROM resources WHERE campus_id=?", (campus_id,),
                                             fetchall=True)
        self.resource_dict = {name: r_id for r_id, name in resources}
        self.resource_combo['values'] = list(self.resource_dict.keys())
        if self.resource_combo['values']: self.resource_combo.current(0)

    def make_booking(self):
        if not self.resource_combo.get(): return messagebox.showerror("Error", "Select a resource")

        resource_id = self.resource_dict[self.resource_combo.get()]
        date = self.date_entry.get()

        try:
            start = int(self.start_entry.get())
            duration = int(self.dur_entry.get())
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            return messagebox.showerror("Error", "Invalid date, start time, or duration.")

        campus_id = self.campus_dict[self.campus_combo.get()]
        rules = self.controller.db_query("SELECT open_hour, close_hour, max_duration FROM campuses WHERE id=?",
                                         (campus_id,), fetch=True)

        if duration > rules[2]:
            return messagebox.showerror("Error", f"Exceeds max duration of {rules[2]} hours for this campus.")
        if start < rules[0] or (start + duration) > rules[1]:
            return messagebox.showerror("Error", f"Booking must be within campus hours: {rules[0]}:00 - {rules[1]}:00.")

        existing = self.controller.db_query("SELECT start_time, duration FROM bookings WHERE resource_id=? AND date=?",
                                            (resource_id, date), fetchall=True)
        new_end = start + duration

        for e_start, e_dur in existing:
            e_end = e_start + e_dur
            if not (new_end <= e_start or start >= e_end):
                return messagebox.showerror("Error", "Resource is double-booked during this time.")

        self.controller.db_query(
            "INSERT INTO bookings (resource_id, user_id, date, start_time, duration) VALUES (?, ?, ?, ?, ?)",
            (resource_id, self.controller.current_user.get_id(), date, start, duration))
        messagebox.showinfo("Success", "Booking confirmed!")
        self.load_history()

    def setup_history_tab(self):
        columns = ("ID", "Resource", "Date", "Start", "Duration")
        self.tree = ttk.Treeview(self.tab_history, columns=columns, show='headings')
        for col in columns: self.tree.heading(col, text=col)
        self.tree.pack(fill="both", expand=True, pady=5)

        ttk.Button(self.tab_history, text="Cancel Selected Booking", command=self.cancel_booking).pack(pady=5)
        self.load_history()

    def load_history(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        data = self.controller.db_query('''SELECT b.id, r.name, b.date, b.start_time, b.duration 
                                           FROM bookings b JOIN resources r ON b.resource_id = r.id 
                                           WHERE b.user_id=?''', (self.controller.current_user.get_id(),),
                                        fetchall=True)
        for row in data:
            self.tree.insert("", "end", values=row)

    def cancel_booking(self):
        selected = self.tree.selection()
        if not selected: return
        booking_id = self.tree.item(selected[0])['values'][0]
        self.controller.db_query("DELETE FROM bookings WHERE id=?", (booking_id,))
        messagebox.showinfo("Success", "Booking cancelled.")
        self.load_history()


class AdminDashboard(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.campus_id = self.controller.current_user.get_campus_id()

        c_name = self.controller.db_query("SELECT name FROM campuses WHERE id=?", (self.campus_id,), fetch=True)[0]
        ttk.Label(self, text=f"{c_name} Campus Admin: {self.controller.current_user.get_username()}",
                  font=("Times New Roman", 14)).pack(pady=5)
        ttk.Button(self, text="Logout", command=self.controller.show_login_frame).pack(anchor="ne", padx=10)

        frame = ttk.Frame(self)
        frame.pack(pady=10)
        ttk.Label(frame, text="New Resource Name:").pack(side="left")
        self.res_entry = ttk.Entry(frame)
        self.res_entry.pack(side="left", padx=5)
        ttk.Button(frame, text="Add Resource", command=self.add_resource).pack(side="left")

        cols = ("Booking ID", "Resource", "Lecturer ID", "Date", "Time")
        self.tree = ttk.Treeview(self, columns=cols, show='headings')
        for col in cols: self.tree.heading(col, text=col)
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)

        ttk.Button(self, text="Remove Selected Booking", command=self.remove_booking).pack(pady=5)
        self.load_data()

    def add_resource(self):
        name = self.res_entry.get()
        if not name: return
        try:
            self.controller.db_query("INSERT INTO resources (name, campus_id) VALUES (?, ?)", (name, self.campus_id))
            messagebox.showinfo("Success", "Resource added.")
            self.res_entry.delete(0, 'end')
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Resource name already exists at this campus.")

    def load_data(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        data = self.controller.db_query('''SELECT b.id, r.name, b.user_id, b.date, b.start_time 
                                           FROM bookings b JOIN resources r ON b.resource_id = r.id 
                                           WHERE r.campus_id=?''', (self.campus_id,), fetchall=True)
        for row in data: self.tree.insert("", "end", values=row)

    def remove_booking(self):
        selected = self.tree.selection()
        if not selected: return
        b_id = self.tree.item(selected[0])['values'][0]
        self.controller.db_query("DELETE FROM bookings WHERE id=?", (b_id,))
        self.load_data()


class OperatorDashboard(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        ttk.Label(self, text="System Operator Dashboard", font=("Times New Roman", 14)).pack(pady=5)
        ttk.Button(self, text="Logout", command=self.controller.show_login_frame).pack(anchor="ne", padx=10)

        self.text_area = tk.Text(self, height=15)
        self.text_area.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Button(self, text="Generate Usage Reports", command=self.generate_reports).pack(pady=10)

    def generate_reports(self):
        self.text_area.delete(1.0, tk.END)
        report = "--- CAMPUS UTILIZATION REPORT ---\n\n"

        campuses = self.controller.db_query("SELECT id, name FROM campuses", fetchall=True)

        for c_id, c_name in campuses:
            total_bookings = self.controller.db_query('''SELECT COUNT(b.id), AVG(b.duration) FROM bookings b 
                                                         JOIN resources r ON b.resource_id = r.id 
                                                         WHERE r.campus_id=?''', (c_id,), fetch=True)

            dates_data = self.controller.db_query('''SELECT b.date FROM bookings b 
                                                     JOIN resources r ON b.resource_id = r.id 
                                                     WHERE r.campus_id=?''', (c_id,), fetchall=True)
            unique_dates = set([d[0] for d in dates_data])

            count = total_bookings[0] or 0
            avg_dur = total_bookings[1] or 0.0

            report += f"Campus: {c_name}\n"
            report += f"Total Bookings: {count}\n"
            report += f"Average Booking Duration: {avg_dur:.1f} hours\n"
            report += f"Active Days (Unique Dates Used): {len(unique_dates)}\n"
            report += "-" * 30 + "\n"

        self.text_area.insert(tk.END, report)


if __name__ == "__main__":
    initialize_db()
    app = SmartCampusApp()
    app.mainloop()

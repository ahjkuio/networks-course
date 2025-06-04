import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from ftplib import FTP, error_perm
from pathlib import Path


class FTPGui(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('FTP клиент')
        self.geometry('500x400')
        self.ftp: FTP | None = None
        self._build_ui()

    def _build_ui(self):
        frm_conn = ttk.LabelFrame(self, text='Подключение')
        frm_conn.pack(fill='x', padx=10, pady=5)

        ttk.Label(frm_conn, text='Host').grid(row=0, column=0, sticky='e')
        self.ent_host = ttk.Entry(frm_conn)
        self.ent_host.insert(0, '127.0.0.1')
        self.ent_host.grid(row=0, column=1)

        ttk.Label(frm_conn, text='Port').grid(row=0, column=2, sticky='e')
        self.ent_port = ttk.Entry(frm_conn, width=5)
        self.ent_port.insert(0, '21')
        self.ent_port.grid(row=0, column=3)

        ttk.Label(frm_conn, text='User').grid(row=1, column=0, sticky='e')
        self.ent_user = ttk.Entry(frm_conn)
        self.ent_user.insert(0, 'anonymous')
        self.ent_user.grid(row=1, column=1)

        ttk.Label(frm_conn, text='Password').grid(row=1, column=2, sticky='e')
        self.ent_pass = ttk.Entry(frm_conn, show='*')
        self.ent_pass.insert(0, 'anonymous@')
        self.ent_pass.grid(row=1, column=3)

        btn_connect = ttk.Button(frm_conn, text='Connect', command=self.connect)
        btn_connect.grid(row=0, column=4, rowspan=2, padx=5)

        frm_files = ttk.LabelFrame(self, text='Файлы')
        frm_files.pack(fill='both', expand=True, padx=10, pady=5)

        self.lst_files = tk.Listbox(frm_files)
        self.lst_files.pack(fill='both', expand=True, side='left')

        scrollbar = ttk.Scrollbar(frm_files, orient='vertical', command=self.lst_files.yview)
        scrollbar.pack(side='left', fill='y')
        self.lst_files.config(yscrollcommand=scrollbar.set)

        frm_buttons = ttk.Frame(frm_files)
        frm_buttons.pack(side='left', fill='y', padx=5)
        ttk.Button(frm_buttons, text='Refresh', command=self.refresh).pack(fill='x')
        ttk.Button(frm_buttons, text='Retrieve', command=self.retrieve).pack(fill='x', pady=5)
        ttk.Button(frm_buttons, text='New', command=self.new_file).pack(fill='x')
        ttk.Button(frm_buttons, text='Edit', command=self.edit_file).pack(fill='x', pady=5)
        ttk.Button(frm_buttons, text='Delete', command=self.delete_file).pack(fill='x', pady=5)
        ttk.Button(frm_buttons, text='Upload', command=self.upload).pack(fill='x')

        # content viewer
        frm_content = ttk.LabelFrame(self, text='Содержимое файла')
        frm_content.pack(fill='both', expand=True, padx=10, pady=5)
        self.txt_content = tk.Text(frm_content, wrap='word')
        self.txt_content.pack(fill='both', expand=True)
        self.txt_content.configure(state='disabled')

    # FTP methods
    def connect(self):
        host = self.ent_host.get()
        port = int(self.ent_port.get())
        user = self.ent_user.get()
        passwd = self.ent_pass.get()
        try:
            self.ftp = FTP()
            self.ftp.connect(host, port, timeout=5)
            self.ftp.login(user, passwd)
            self.ftp.set_pasv(False)
            messagebox.showinfo('FTP', 'Соединение установлено')
            self.refresh()
        except Exception as e:
            messagebox.showerror('FTP', f'Ошибка подключения: {e}')
            self.ftp = None

    def refresh(self):
        if not self.ftp:
            return
        self.lst_files.delete(0, tk.END)
        files = []
        self.ftp.retrlines('NLST', files.append)
        for f in files:
            self.lst_files.insert(tk.END, f)

    def download(self):
        if not self.ftp:
            return
        sel = self.lst_files.curselection()
        if not sel:
            return
        remote = self.lst_files.get(sel[0])
        dest = filedialog.asksaveasfilename(initialfile=remote)
        if not dest:
            return
        try:
            with open(dest, 'wb') as f:
                self.ftp.retrbinary(f'RETR {remote}', f.write)
            messagebox.showinfo('FTP', 'Файл скачан')
        except error_perm as e:
            messagebox.showerror('FTP', f'Ошибка: {e}')

    def upload(self):
        if not self.ftp:
            return
        local = filedialog.askopenfilename()
        if not local:
            return
        path = Path(local)
        try:
            with path.open('rb') as f:
                self.ftp.storbinary(f'STOR {path.name}', f)
            messagebox.showinfo('FTP', 'Файл загружен')
            self.refresh()
        except error_perm as e:
            messagebox.showerror('FTP', f'Ошибка: {e}')

    # --- CRUD helpers ---
    def _editor(self, filename: str, content: str = ''):
        win = tk.Toplevel(self)
        win.title(filename)
        txt = tk.Text(win, wrap='word')
        txt.pack(fill='both', expand=True)
        txt.insert('1.0', content)

        def save():
            data = txt.get('1.0', 'end').encode()
            try:
                from io import BytesIO
                bio = BytesIO(data)
                self.ftp.storbinary(f'STOR {filename}', bio)
                messagebox.showinfo('FTP', 'Сохранено')
                self.refresh()
            except error_perm as e:
                messagebox.showerror('FTP', f'Ошибка: {e}')

        ttk.Button(win, text='Save', command=save).pack()

    def view(self):
        if not self.ftp:
            return
        sel = self.lst_files.curselection()
        if not sel:
            return
        remote = self.lst_files.get(sel[0])
        from io import BytesIO
        buf = BytesIO()
        try:
            self.ftp.retrbinary(f'RETR {remote}', buf.write)
            self._editor(remote, buf.getvalue().decode())
        except error_perm as e:
            messagebox.showerror('FTP', f'Ошибка: {e}')

    def retrieve(self):
        if not self.ftp:
            return
        sel = self.lst_files.curselection()
        if not sel:
            return
        remote = self.lst_files.get(sel[0])
        from io import BytesIO
        buf = BytesIO()
        try:
            self.ftp.retrbinary(f'RETR {remote}', buf.write)
            self.txt_content.configure(state='normal')
            self.txt_content.delete('1.0', 'end')
            try:
                text = buf.getvalue().decode()
            except UnicodeDecodeError:
                text = '[binary data]'
            self.txt_content.insert('1.0', text)
            self.txt_content.configure(state='disabled')
        except error_perm as e:
            messagebox.showerror('FTP', f'Ошибка: {e}')

    def new_file(self):
        if not self.ftp:
            return
        name = simpledialog.askstring('New file', 'Имя файла:')
        if name:
            self._editor(name, '')

    def edit_file(self):
        if not self.ftp:
            return
        sel = self.lst_files.curselection()
        if not sel:
            return
        remote = self.lst_files.get(sel[0])
        from io import BytesIO
        buf = BytesIO()
        try:
            self.ftp.retrbinary(f'RETR {remote}', buf.write)
            self._editor(remote, buf.getvalue().decode())
        except error_perm as e:
            messagebox.showerror('FTP', f'Ошибка: {e}')

    def delete_file(self):
        if not self.ftp:
            return
        sel = self.lst_files.curselection()
        if not sel:
            return
        remote = self.lst_files.get(sel[0])
        if messagebox.askyesno('Удалить', f'Удалить файл {remote}?'):
            try:
                self.ftp.delete(remote)
                self.refresh()
            except error_perm as e:
                messagebox.showerror('FTP', f'Ошибка: {e}')


def main():
    app = FTPGui()
    app.mainloop()


if __name__ == '__main__':
    main() 
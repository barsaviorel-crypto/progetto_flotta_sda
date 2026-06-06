import subprocess
import base64
import sys
import os
from tkinter import messagebox, filedialog, ttk
import datetime
import winsound
import tkinter as tk
from tkcalendar import Calendar  # Inclusione della libreria del calendario (ma meglio scrivere dentro al setup per velocizzare il programma al avvio)


def get_hwid():
    """Recupera l'UUID Hardware. Prova prima il registro (veloce),
    poi PowerShell (affidabile), infine il MachineGuid software."""
    try:
        cmd = 'reg query "HKLM\\HARDWARE\\DESCRIPTION\\System\\BIOS" /v SystemUUID'
        output = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL).decode().strip()
        uuid = output.split()[-1]
        if len(uuid) > 10:
            return uuid
    except Exception:
        pass

    try:
        cmd = 'powershell -command "(Get-CimInstance Win32_ComputerSystemProduct).UUID"'
        uuid = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL).decode().strip()
        if len(uuid) > 10 and "Errore" not in uuid:
            return uuid
    except Exception:
        pass

    try:
        cmd = 'reg query "HKLM\\SOFTWARE\\Microsoft\\Cryptography" /v MachineGuid'
        output = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL).decode().strip()
        return output.split()[-1]
    except Exception:
        return "ID_NON_RILEVATO"


def verifica_licenza():
    id_attuale = get_hwid()

    with open("ID_PER_ATTIVAZIONE.txt", "w") as f:
        f.write(id_attuale)

    if os.path.exists("license.key"):
        with open("license.key", "r") as f:
            chiave_letta = f.read().strip()
        try:
            id_autorizzato = base64.b64decode(chiave_letta).decode()
            if id_autorizzato == id_attuale:
                print("Licenza Permanente rilevata. Accesso completo.")
                return
            else:
                messagebox.showerror("Errore",
                                     f"Licenza non valida per questo PC.\nIl tuo ID è stato salvato in 'ID_PER_ATTIVAZIONE.txt'.")
                sys.exit()
        except:
            messagebox.showerror("Errore",
                                 f"File licenza corrotto. \nInvia questo ID allo sviluppatore(Viorel):\n\n{id_attuale}")
            sys.exit()

    path_programma = os.path.dirname(os.path.abspath(__file__))
    ctime = os.path.getctime(path_programma)
    data_creazione = datetime.datetime.fromtimestamp(ctime)
    giorni_passati = (datetime.datetime.now() - data_creazione).days

    if giorni_passati <= 30:
        messagebox.showerror("Licenza",
                             f"Licenza mancante.\nInvia questo ID allo sviluppatore(Viorel):\n\n{id_attuale}")
        messagebox.showinfo("Modaliata Trial", f"Modalità TRIAL: {30 - giorni_passati} giorni rimanenti.")
        print(f"Modalità TRIAL: {30 - giorni_passati} giorni rimanenti.")
    else:
        messagebox.showerror("Trial Scaduto",
                             f"Il periodo di prova è terminato.\n\n"
                             f"Contatta lo sviluppatore per la licenza(Viorel).\n"
                             f"L'ID è disponibile nel file 'ID_PER_ATTIVAZIONE.txt'.")
        sys.exit()


if __name__ == "__main__":
    verifica_licenza()
    print("Esecuzione del software in corso...")

import json
import pandas as pd
import customtkinter as ctk
import sqlite3
import re
import hashlib
import shutil
import csv
from datetime import datetime

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class DatabaseSQL:
    def __init__(self, db_path="database_flotta_pro.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.cursor = self.conn.cursor()
        self.setup()

    def setup(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS veicoli
                               (targa TEXT PRIMARY KEY, marca TEXT, modello TEXT, anno TEXT, assicurazione TEXT, note TEXT)''')
        try:
            self.cursor.execute("ALTER TABLE veicoli ADD COLUMN note TEXT DEFAULT ''")
            self.conn.commit()
        except sqlite3.OperationalError:
            pass

        self.cursor.execute('''CREATE TABLE IF NOT EXISTS driver
                               (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, cognome TEXT, nascita TEXT, giro TEXT, email TEXT, telefono TEXT, targa TEXT, note TEXT)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS utenti
                               (username TEXT PRIMARY KEY, password TEXT, ruolo TEXT)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS presenze
                               (id_driver INTEGER, data TEXT, stato TEXT, PRIMARY KEY (id_driver, data))''')

        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_driver_nome_cognome ON driver(nome, cognome);")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_driver_giro ON driver(giro);")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_driver_targa ON driver(targa);")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_presenze_data ON presenze(data);")
        self.conn.commit()


class SistemaGestionaleFlotta:
    def __init__(self, root):
        self.root = root
        self.modificato = False
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        db_predefinito = "database_flotta_pro.db"
        self.colonne_salvate = {}

        if os.path.exists("config.json"):
            try:
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
                    if os.path.exists(config.get("ultimo_db", "")):
                        db_predefinito = config["ultimo_db"]
                    self.colonne_salvate = config.get("larghezze_colonne", {})
            except:
                pass

        self.db = DatabaseSQL(db_predefinito)
        self.root.geometry("1400x850+0+0")
        self.aggiorna_titolo_finestra()

        self.campi_d = ["Nome", "Cognome", "Nascita", "Giro", "Email", "Telefono", "Targa", "Note"]
        self.campi_v = ["Targa", "Marca", "Modello", "Anno", "Assicurazione", "Note", "Stato"]
        self.utente_attuale = None
        self.filtro_liberi = False

        self.mesi_nomi = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
                          "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]

        self.root.withdraw()
        self.mostra_login()

    def valida_data_stringa(self, data_str):
        """Verifica se il formato inserito è esattamente GG/MM/AAAA e se corrisponde a un giorno reale."""
        if not re.match(r"^\d{2}/\d{2}/\d{4}$", data_str):
            return False
        try:
            datetime.strptime(data_str, "%d/%m/%Y")
            return True
        except ValueError:
            return False

    def aggiorna_titolo_finestra(self):
        nome_db = os.path.basename(self.db.db_path)
        self.root.title(f"Gestione Flotta Pro - by Viorel  |  📂 Database Attivo: {nome_db}")

    def salva_configurazione_completa(self):
        try:
            larghezze = {
                "driver": {col: self.tree_d.column(col, "width") for col in self.tree_d["columns"]},
                "veicoli": {col: self.tree_v.column(col, "width") for col in self.tree_v["columns"]},
                "presenze": {col: self.tree_p.column(col, "width") for col in self.tree_p["columns"]} if hasattr(self,
                                                                                                                 'tree_p') else {}
            }
            config_data = {
                "ultimo_db": self.db.db_path,
                "larghezze_colonne": larghezze
            }
            with open("config.json", "w", encoding="utf-8") as f:
                json.dump(config_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Errore nel salvataggio della configurazione: {e}")

    def ripristina_dimensioni_colonne(self):
        if not self.colonne_salvate:
            return
        driver_widths = self.colonne_salvate.get("driver", {})
        for col, width in driver_widths.items():
            if col in self.tree_d["columns"]:
                self.tree_d.column(col, width=width)
        veicoli_widths = self.colonne_salvate.get("veicoli", {})
        for col, width in veicoli_widths.items():
            if col in self.tree_v["columns"]:
                self.tree_v.column(col, width=width)
        presenze_widths = self.colonne_salvate.get("presenze", {})
        if hasattr(self, 'tree_p'):
            for col, width in presenze_widths.items():
                if col in self.tree_p["columns"]:
                    self.tree_p.column(col, width=width)

    def esporta_driver_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="esporta_driver.csv",
                                            filetypes=[("CSV File", "*.csv")])
        if path:
            self.db.cursor.execute("SELECT * FROM driver")
            righe = self.db.cursor.fetchall()
            with open(path, 'w', newline='', encoding='utf-8-sig') as f:
                w = csv.writer(f, delimiter=';')
                w.writerow(["ID"] + self.campi_d)
                w.writerows(righe)
            messagebox.showinfo("Export", "Anagrafica Driver esportata con successo!")

    def esporta_veicoli_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="esporta_veicoli.csv",
                                            filetypes=[("CSV File", "*.csv")])
        if path:
            self.db.cursor.execute("SELECT * FROM veicoli")
            veicoli = self.db.cursor.fetchall()
            dati_finali = []
            oggi_str = datetime.now().strftime("%d/%m/%Y")
            self.db.cursor.execute("SELECT id_driver, stato FROM presenze WHERE data=?", (oggi_str,))
            assenti_oggi = {r[0] for r in self.db.cursor.fetchall() if r[1] != "Presente"}

            for v in veicoli:
                self.db.cursor.execute("SELECT id, nome, cognome FROM driver WHERE targa=?", (v[0],))
                res = self.db.cursor.fetchone()
                if res:
                    id_d, nome, cognome = res[0], res[1], res[2]
                    if id_d in assenti_oggi:
                        stato = "Disponibile (Driver Assente)"
                    else:
                        stato = f"{nome} {cognome}"
                else:
                    stato = "Disponibile"
                v_lista = list(v)
                while len(v_lista) < 6:
                    v_lista.append("")
                dati_finali.append((*v_lista, stato))

            with open(path, 'w', newline='', encoding='utf-8-sig') as f:
                w = csv.writer(f, delimiter=';')
                w.writerow(self.campi_v)
                w.writerows(dati_finali)
            messagebox.showinfo("Export", "Elenco Veicoli esportato con successo!")

    def file_nuovo(self):
        path = filedialog.asksaveasfilename(defaultextension=".db", filetypes=[("Database SQL", "*.db")])
        if path:
            self.db.cursor.execute("SELECT password, ruolo FROM utenti WHERE username=?",
                                   (self.utente_attuale["nome"],))
            user_data = self.db.cursor.fetchone()
            self.salva_configurazione_completa()
            self.db.conn.close()
            self.db = DatabaseSQL(path)
            if user_data:
                self.db.cursor.execute("INSERT OR IGNORE INTO utenti VALUES (?,?,?)",
                                       (self.utente_attuale["nome"], user_data[0], user_data[1]))
                self.db.conn.commit()
            self.modificato = False
            self.aggiorna_dati()
            self.aggiorna_titolo_finestra()
            self.salva_configurazione_completa()
            messagebox.showinfo("Nuovo Database", f"Nuovo database creato e attivo: {os.path.basename(path)}")

    def file_apri(self):
        path = filedialog.askopenfilename(filetypes=[("Database SQL", "*.db")])
        if path:
            self.salva_configurazione_completa()
            self.db.conn.close()
            self.db = DatabaseSQL(path)
            self.aggiorna_dati()
            self.aggiorna_titolo_finestra()
            self.salva_configurazione_completa()
            messagebox.showinfo("Apri", f"Database caricato: {os.path.basename(path)}")

    def file_salva(self):
        self.db.conn.commit()
        self.modificato = False
        self.salva_configurazione_completa()
        messagebox.showinfo("Salva", "Modifiche e layout tabelle salvati correttamente.")

    def file_salva_con_nome(self):
        path = filedialog.asksaveasfilename(defaultextension=".db", filetypes=[("Database SQL", "*.db")])
        if path:
            self.db.conn.commit()
            shutil.copy2(self.db.db_path, path)
            self.salva_configurazione_completa()
            self.db.conn.close()
            self.db = DatabaseSQL(path)
            self.modificato = False
            self.aggiorna_dati()
            self.aggiorna_titolo_finestra()
            self.salva_configurazione_completa()
            messagebox.showinfo("Salva con nome", f"Nuova copia creata e attiva: {os.path.basename(path)}")

    def popup_ricerca_moderno(self, titolo, label_testo, callback):
        pop = ctk.CTkToplevel(self.root)
        pop.title(titolo)
        pop.geometry("400x220")
        pop.attributes("-topmost", True)
        pop.grab_set()
        ctk.CTkLabel(pop, text=label_testo, font=("Helvetica", 14, "bold")).pack(pady=15)
        entry = ctk.CTkEntry(pop, width=300)
        entry.pack(pady=10)
        entry.focus_set()

        def invia(event=None):
            v = entry.get()
            pop.destroy()
            if v: callback(v)

        btn = ctk.CTkButton(pop, text="CERCA", fg_color="#f1c40f", text_color="black", command=invia)
        btn.pack(pady=15)
        pop.bind("<Return>", invia)

    def esegui_ricerca_driver(self, tree, val):
        val_lower = val.lower()
        for item in tree.get_children():
            valori = tree.item(item)['values']
            if val_lower in str(valori[1]).lower() or val_lower in str(valori[2]).lower():
                tree.selection_set(item)
                tree.see(item)
                return
        messagebox.showwarning("Ricerca", "Nessun driver trovato con questo nome/cognome.")

    def mostra_login(self):
        win = ctk.CTkToplevel(self.root)
        win.geometry("400x450")
        win.attributes("-topmost", True)
        win.grab_set()

        def on_login_close():
            winsound.MessageBeep(winsound.MB_OK)
            if messagebox.askyesno("Esci", "Vuoi davvero uscire dal programma?", parent=win):
                win.destroy()
                self.root.destroy()

        win.protocol("WM_DELETE_WINDOW", on_login_close)

        ctk.CTkLabel(win, text="LOG IN", font=("Helvetica", 24, "bold")).pack(pady=40)
        u_ent = ctk.CTkEntry(win, width=250, placeholder_text="Username")
        u_ent.pack(pady=10)
        p_ent = ctk.CTkEntry(win, width=250, placeholder_text="Password", show="*")
        p_ent.pack(pady=10)

        def login():
            u, p_raw = u_ent.get(), p_ent.get()
            if not u or not p_raw:
                winsound.MessageBeep(winsound.MB_ICONHAND)
                messagebox.showerror("Errore", "Inserisci credenziali", parent=win)
                return

            p = hashlib.sha256(p_raw.encode()).hexdigest()
            self.db.cursor.execute("SELECT COUNT(*) FROM utenti")
            count = self.db.cursor.fetchone()[0]

            if count == 0:
                self.db.cursor.execute("INSERT INTO utenti VALUES (?,?,?)", (u, p, "admin"))
                self.db.conn.commit()
                winsound.MessageBeep(winsound.MB_OK)
                messagebox.showinfo("Benvenuto", f"Primo utente '{u}' creato come Amministratore.", parent=win)

            self.db.cursor.execute("SELECT ruolo FROM utenti WHERE username=? AND password=?", (u, p))
            res = self.db.cursor.fetchone()
            if res:
                self.utente_attuale = {"nome": u, "ruolo": res[0]}
                win.destroy()
                self.crea_interfaccia()
            else:
                winsound.MessageBeep(winsound.MB_ICONHAND)
                messagebox.showerror("Errore", "Dati errati", parent=win)

        ctk.CTkButton(win, text="ACCEDI", command=login).pack(pady=30)

    def crea_interfaccia(self):
        # FORZA IL PROGRAMMA IN FULL SCREEN (Massimizzato su Windows)
        self.root.state('zoomed')
#        self.root.geometry("1280x720")
#        self.root.minsize(1024, 600)
        self.root.deiconify()
        perm = "normal" if self.utente_attuale["ruolo"] == "admin" else "disabled"

        menu = ctk.CTkFrame(self.root, height=70, fg_color="#1e1e1e", corner_radius=0)
        menu.pack(side="top", fill="x")

        ctk.CTkButton(menu, state=perm, text="📄 NUOVO", fg_color="#2980b9", width=70, command=self.file_nuovo).pack(
            side="left", padx=5, pady=15)
        ctk.CTkButton(menu, state=perm, text="📂 APRI", fg_color="#34495e", width=70, command=self.file_apri).pack(
            side="left", padx=5)
        ctk.CTkButton(menu, state=perm, text="💾 SALVA", fg_color="#27ae60", width=70, command=self.file_salva).pack(
            side="left", padx=5)
        ctk.CTkButton(menu, state=perm, text="💾 SALVA CON...", fg_color="#16a085", width=100,
                      command=self.file_salva_con_nome).pack(side="left", padx=5)
        ctk.CTkButton(menu, text="📤 EXPORT DRIVER", fg_color="#d35400", width=130,
                      command=self.esporta_driver_csv).pack(side="left", padx=5)
        ctk.CTkButton(menu, text="📤 EXPORT MEZZI", fg_color="#a04000", width=130,
                      command=self.esporta_veicoli_csv).pack(side="left", padx=5)

        if self.utente_attuale["ruolo"] == "admin":
            ctk.CTkButton(menu, text="⚙️ UTENTI", fg_color="#607D8B", width=90, command=self.gestione_utenti).pack(
                side="left", padx=5)

        ctk.CTkButton(menu, text="ESCI", fg_color="#e74c3c", width=70, command=self.on_closing).pack(side="right",
                                                                                                     padx=15)
        ctk.CTkLabel(menu, text=f"👤 {self.utente_attuale['nome'].upper()}", font=("Helvetica", 12, "bold"),
                     text_color="#3498db").pack(side="right", padx=10)

        self.tabs = ctk.CTkTabview(self.root, segmented_button_selected_color="#1f538d")
        self.tabs.pack(expand=True, fill="both", padx=10, pady=10)

        self.tab_d = self.tabs.add("       👤 ANAGRAFICA       ")
        self.tab_v = self.tabs.add("       🚛 VEICOLI           ")
        self.tab_p = self.tabs.add("       📅 PRESENZE          ")

        self.setup_tab_anagrafica(perm)
        self.setup_tab_veicoli(perm)
        self.setup_tab_presenze(perm)

        self.aggiorna_dati()
        self.ripristina_dimensioni_colonne()

    def setup_tab_anagrafica(self, perm):
        tb = ctk.CTkFrame(self.tab_d, fg_color="transparent")
        tb.pack(fill="x", pady=10)
        ctk.CTkButton(tb, text="➕ AGGIUNGI", fg_color="#2ecc71", command=lambda: self.form_driver(), state=perm).pack(
            side="left", padx=5)
        ctk.CTkButton(tb, text="📝 MODIFICA", fg_color="#3498db", command=self.modifica_driver, state=perm).pack(
            side="left", padx=5)
        ctk.CTkButton(tb, text="🗑️ ELIMINA", fg_color="#e74c3c", command=self.elimina_driver, state=perm).pack(
            side="left", padx=5)
        ctk.CTkButton(tb, text="🔗 ASSEGNA MEZZO", fg_color="#9b59b6", command=self.popup_assegna_da_driver,
                      state=perm).pack(side="left", padx=5)
        ctk.CTkButton(tb, text="🔍 CERCA GIRO", fg_color="#f1c40f", text_color="black",
                      command=lambda: self.popup_ricerca_moderno("Cerca Giro", "Numero Giro:",
                                                                 lambda v: self.esegui_ricerca(self.tree_d, 4,
                                                                                               v))).pack(side="right",
                                                                                                         padx=5)
        ctk.CTkButton(tb, text="🔍 CERCA DRIVER", fg_color="#f1c40f", text_color="black",
                      command=lambda: self.popup_ricerca_moderno("Cerca Driver", "Nome o Cognome:",
                                                                 lambda v: self.esegui_ricerca_driver(self.tree_d,
                                                                                                      v))).pack(
            side="right", padx=5)

        self.tree_d = self.crea_tree(self.tab_d, ["ID"] + self.campi_d)
        self.tree_d.bind("<Double-1>", lambda e: self.mostra_dettagli("Driver",
                                                                      self.tree_d.item(self.tree_d.selection()[0])[
                                                                          'values']))
        self.tree_d.bind("<Return>", lambda e: self.mostra_dettagli("Driver",
                                                                    self.tree_d.item(self.tree_d.selection()[0])[
                                                                        'values']))

    def setup_tab_veicoli(self, perm):
        tb = ctk.CTkFrame(self.tab_v, fg_color="transparent")
        tb.pack(fill="x", pady=10)
        ctk.CTkButton(tb, text="➕ AGGIUNGI MEZZO", fg_color="#2ecc71", command=self.form_veicolo, state=perm).pack(
            side="left", padx=5)
        ctk.CTkButton(tb, text="📝 MODIFICA MEZZO", fg_color="#3498db", command=self.modifica_veicolo, state=perm).pack(
            side="left", padx=5)
        ctk.CTkButton(tb, text="🗑️ ELIMINA", fg_color="#e74c3c", command=self.elimina_veicolo, state=perm).pack(
            side="left", padx=5)
        ctk.CTkButton(tb, text="🔓 LIBERA MEZZO", fg_color="#e67e22", command=self.libera_mezzo, state=perm).pack(
            side="left", padx=5)
        ctk.CTkButton(tb, text="🔗 COLLEGA DRIVER", fg_color="#9b59b6", command=self.popup_collega_driver,
                      state=perm).pack(side="left", padx=5)
        ctk.CTkButton(tb, text="🔍 CERCA TARGA", fg_color="#f1c40f", text_color="black",
                      command=lambda: self.popup_ricerca_moderno("Cerca Targa", "Inserisci Targa:",
                                                                 lambda v: self.esegui_ricerca(self.tree_v, 0,
                                                                                               v.upper()))).pack(
            side="right", padx=5)

        self.btn_liberi = ctk.CTkButton(tb, text="🔍 SOLO LIBERI", fg_color="#444", command=self.toggle_liberi)
        self.btn_liberi.pack(side="right", padx=5)

        self.tree_v = self.crea_tree(self.tab_v, self.campi_v)
        self.tree_v.bind("<Double-1>", lambda e: self.mostra_dettagli("Veicolo",
                                                                      self.tree_v.item(self.tree_v.selection()[0])[
                                                                          'values']))
        self.tree_v.bind("<Return>", lambda e: self.mostra_dettagli("Veicolo",
                                                                    self.tree_v.item(self.tree_v.selection()[0])[
                                                                        'values']))

    def setup_tab_presenze(self, perm):

        # Frame principale che occupa tutto il tab presenze con griglia equilibrata (70% e 30%)
        main_p_frame = ctk.CTkFrame(self.tab_p, fg_color="transparent")
        main_p_frame.pack(fill="both", expand=True, padx=15, pady=15)

        main_p_frame.grid_columnconfigure(0, weight=7)
        main_p_frame.grid_columnconfigure(1, weight=3)
        main_p_frame.grid_rowconfigure(0, weight=1)

        # ---------------------------------------------
        # COLONNA DI SINISTRA: Tabella dei Conducenti
        # ---------------------------------------------
        left_frame = ctk.CTkFrame(main_p_frame, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 15))

        self.label_data_presenze = ctk.CTkLabel(left_frame, text="Stato Conducenti del: OGGI",
                                                font=("Helvetica", 15, "bold"))
        self.label_data_presenze.pack(anchor="w", pady=(0, 5))

        self.tree_p = self.crea_tree(left_frame,
                                     ["ID DRIVER", "NOME", "COGNOME", "GIRO", "TARGA MEZZO", "STATO PRESENZA"])

        # Configurazione visiva dei tag dei colori per la tabella presenze
        self.tree_p.tag_configure('tag_Presente', background='#2ecc71', foreground='white')
        self.tree_p.tag_configure('tag_Ferie', background='#e67e22', foreground='white')
        self.tree_p.tag_configure('tag_Malattia', background='#9b59b6', foreground='white')
        self.tree_p.tag_configure('tag_Permesso', background='#3498db', foreground='white')
        self.tree_p.tag_configure('tag_Assente Ingiustificato', background='#e74c3c', foreground='white')

        # ---------------------------------------------
        # COLONNA DI DESTRA: Calendario Leggibile e Pulsanti
        # ---------------------------------------------
        right_frame = ctk.CTkFrame(main_p_frame, fg_color="transparent")
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(15, 0))

        ctk.CTkLabel(right_frame, text="1. Scegli il giorno nel calendario:", font=("Helvetica", 14, "bold")).pack(
            anchor="w", pady=(0, 5))

        # Calendario ridimensionato per evitare schiacciamenti
        self.cal = Calendar(right_frame, selectmode="day",
                            locale="it_IT", date_pattern="dd/mm/yyyy",
                            font=("Helvetica", 11, "bold"),
                            headerfont=("Helvetica", 12, "bold"),
                            background="#1f538d", foreground="white",
                            headersbackground="#2b2b2b", headersforeground="white",
                            selectbackground="#2ecc71", selectforeground="white",
                            normalbackground="#2b2b2b", normalforeground="white",
                            weekendbackground="#3a3a3a", weekendforeground="white",
                            othermonthbackground="#1e1e1e", othermonthforeground="#555555")
        self.cal.pack(fill="both", expand=True, pady=(0, 15))

        # Associa il click sulla data del calendario all'aggiornamento grafico immediato della tabella
        self.cal.bind("<<CalendarSelected>>", lambda event: self.aggiorna_presenze_da_calendario())

        # Pulsanti di comando stato
        ctk.CTkLabel(right_frame, text="2. Cambia Stato per il giorno scelto:", font=("Helvetica", 13, "bold")).pack(
            anchor="w", pady=(10, 2))

        ctk.CTkButton(right_frame, text="✅ PRESENTE", fg_color="#2ecc71", text_color="white", height=38,
                      font=("Helvetica", 13, "bold"),
                      command=lambda: self.salva_stato_presenza_da_calendario("Presente"), state=perm).pack(fill="x",
                                                                                                            pady=3)
        ctk.CTkButton(right_frame, text="🌴 FERIE", fg_color="#e67e22", height=38, font=("Helvetica", 13, "bold"),
                      command=lambda: self.salva_stato_presenza_da_calendario("Ferie"), state=perm).pack(fill="x",
                                                                                                         pady=3)
        ctk.CTkButton(right_frame, text="🤒 MALATTIA", fg_color="#9b59b6", height=38,
                      font=("Helvetica", 13, "bold"),
                      command=lambda: self.salva_stato_presenza_da_calendario("Malattia"), state=perm).pack(fill="x",
                                                                                                            pady=3)
        ctk.CTkButton(right_frame, text="📄 PERMESSO", fg_color="#3498db", height=38,
                      font=("Helvetica", 13, "bold"),
                      command=lambda: self.salva_stato_presenza_da_calendario("Permesso"), state=perm).pack(fill="x",
                                                                                                            pady=3)
        ctk.CTkButton(right_frame, text="❌ ASSENTE", fg_color="#e74c3c", height=38,
                      font=("Helvetica", 13, "bold"),
                      command=lambda: self.salva_stato_presenza_da_calendario("Assente Ingiustificato"),
                      state=perm).pack(fill="x", pady=3)

    def aggiorna_presenze_da_calendario(self):
        if not hasattr(self, 'tree_p'): return
        for i in self.tree_p.get_children(): self.tree_p.delete(i)

        # Legge la data attualmente evidenziata nel calendario grafico
        data_selezionata = self.cal.get_date()

        if hasattr(self, 'label_data_presenze'):
            self.label_data_presenze.configure(text=f"Stato Conducenti del: {data_selezionata}")

        # Estrae le informazioni per quel giorno specifico
        self.db.cursor.execute("SELECT id_driver, stato FROM presenze WHERE data=?", (data_selezionata,))
        mappa_stati_data = {r[0]: r[1] for r in self.db.cursor.fetchall()}

        self.db.cursor.execute("SELECT id, nome, cognome, giro, targa FROM driver")
        for d in self.db.cursor.fetchall():
            id_driver = d[0]
            stato_giorno = mappa_stati_data.get(id_driver, "Presente")

            # Associa il tag del colore corretto ('tag_Presente', 'tag_Ferie', ecc.)
            tag = (f'tag_{stato_giorno}',)
            self.tree_p.insert("", "end",
                               values=(d[0], d[1], d[2], d[3], d[4] if d[4] else "Nessuno", stato_giorno),
                               tags=tag)

    def salva_stato_presenza_da_calendario(self, nuovo_stato):
        # 1. Controlla se l'utente ha selezionato almeno un autista
        sel_driver = self.tree_p.selection()
        if not sel_driver:
            winsound.MessageBeep(winsound.MB_ICONHAND)
            messagebox.showwarning("Selezione Driver", "Seleziona uno o più Conducenti dalla tabella di sinistra.")
            return

        # 2. Recupera la data selezionata nel calendario
        data_sel = self.cal.get_date()
        nomi_selezionati = []

        # 3. Salva o esegue l'UPDATE nel database per quella determinata data
        for item in sel_driver:
            valori = self.tree_p.item(item)['values']
            id_driver = valori[0]
            nome_completo = f"{valori[1]} {valori[2]}"
            nomi_selezionati.append(nome_completo)

            self.db.cursor.execute("""
                INSERT INTO presenze (id_driver, data, stato) VALUES (?, ?, ?)
                ON CONFLICT(id_driver, data) DO UPDATE SET stato=excluded.stato
            """, (id_driver, data_sel, nuovo_stato))

        self.db.conn.commit()
        self.modificato = True

        # 4. Rinfresca all'istante la visualizzazione dei colori e della lista
        self.aggiorna_presenze_da_calendario()
        self.aggiorna_dati()

        # ==========================================================
        # NUOVO AUDIO E AVVISO DI CONFERMA
        # ==========================================================
        # Riproduce il Beep standard di Windows per confermare l'azione succeduta
        winsound.MessageBeep(winsound.MB_OK)

        # Crea un piccolo banner di notifica elegante e non invasivo
        popup_conferma = ctk.CTkToplevel(self.root)
        popup_conferma.geometry("420x70")
        # Centra la notifica rispetto allo schermo principale
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 210
        y = self.root.winfo_y() + 80
        popup_conferma.geometry(f"420x70+{x}+{y}")
        popup_conferma.overrideredirect(True)  # Rimuove i bordi della finestra per farla sembrare un banner
        popup_conferma.attributes("-topmost", True)

        # Mappa dei colori di sfondo del banner coerenti con lo stato salvato
        colori_stato = {
            "Presente": "#2ecc71",
            "Ferie": "#e67e22",
            "Malattia": "#9b59b6",
            "Permesso": "#3498db",
            "Assente Ingiustificato": "#e74c3c"
        }
        colore_sfondo = colori_stato.get(nuovo_stato, "#2c3e50")

        # Visualizzazione del testo di conferma all'interno del banner
        testo_notifica = f"Stato aggiornato in: {nuovo_stato.upper()}\nper {', '.join(nomi_selezionati)}"
        if len(nomi_selezionati) > 2:
            testo_notifica = f"Stato aggiornato in: {nuovo_stato.upper()}\nper {len(nomi_selezionati)} conducenti selezionati"

        lbl_notifica = ctk.CTkLabel(popup_conferma, text=testo_notifica,
                                    font=("Helvetica", 12, "bold"),
                                    text_color="white", fg_color=colore_sfondo, corner_radius=8)
        lbl_notifica.pack(expand=True, fill="both")

        # Chiude automaticamente il banner dopo 1500 millisecondi (1.5 secondi) senza bloccare l'app
        popup_conferma.after(1500, popup_conferma.destroy)

    def crea_tree(self, parent, colonne):
        fr = ctk.CTkFrame(parent)
        fr.pack(expand=True, fill="both")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#2b2b2b", foreground="white", fieldbackground="#2b2b2b",
                        font=("Helvetica", 14, "bold"), rowheight=35)
        style.configure("Treeview.Heading", background="#2C5364", foreground="black", font=("Helvetica", 18, "bold"))
        tree = ttk.Treeview(fr, columns=colonne, show="headings")
        for c in colonne:
            tree.heading(c, text=c.upper())
            tree.column(c, width=110, anchor="center")
        tree.tag_configure('scaduto', background='#721c24')
        tree.tag_configure('avviso', background='#f1c40f', foreground="black")
        tree.pack(side="left", expand=True, fill="both")
        sb = ttk.Scrollbar(fr, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        return tree

    def aggiorna_dati(self):
        for i in self.tree_d.get_children(): self.tree_d.delete(i)
        for i in self.tree_v.get_children(): self.tree_v.delete(i)

        self.db.cursor.execute("SELECT * FROM driver")
        for r in self.db.cursor.fetchall(): self.tree_d.insert("", "end", values=r)

        oggi_str = datetime.now().strftime("%d/%m/%Y")
        self.db.cursor.execute("SELECT id_driver, stato FROM presenze WHERE data=?", (oggi_str,))
        mappa_presenze_oggi = {r[0]: r[1] for r in self.db.cursor.fetchall()}

        self.db.cursor.execute("SELECT id, nome, cognome, targa FROM driver WHERE targa != ''")
        driver_targa_map = {}
        for row in self.db.cursor.fetchall():
            id_d, nome, cognome, targa = row[0], row[1], row[2], row[3]
            stato_presenza = mappa_presenze_oggi.get(id_d, "Presente")
            if stato_presenza != "Presente":
                iniziale = stato_presenza[0].upper()
                driver_targa_map[targa] = f"Disponibile ({iniziale}) {nome} {cognome}"
            else:
                driver_targa_map[targa] = f"{nome} {cognome}"

        oggi = datetime.now()
        self.db.cursor.execute("SELECT * FROM veicoli")
        for v in self.db.cursor.fetchall():
            v_lista = list(v)
            while len(v_lista) < 6:
                v_lista.append("")

            stato = driver_targa_map.get(v_lista[0], "Disponibile")
            if self.filtro_liberi and not stato.startswith("Disponibile"):
                continue

            tag = ()
            try:
                sc = datetime.strptime(v_lista[4], "%d/%m/%Y")
                diff = (sc - oggi).days
                if diff < 0:
                    tag = ('scaduto',)
                elif diff <= 30:
                    tag = ('avviso',)
            except:
                pass

            valori_riga = (v_lista[0], v_lista[1], v_lista[2], v_lista[3], v_lista[4], v_lista[5], stato)
            self.tree_v.insert("", "end", values=valori_riga, tags=tag)

        self.aggiorna_presenze_da_calendario()

    def mostra_dettagli(self, tipo, dati):
        win = ctk.CTkToplevel(self.root)
        win.title(f"Dettagli {tipo}")
        win.geometry("450x550")
        win.attributes("-topmost", True)

        ctk.CTkLabel(win, text=f"DETTAGLI {tipo.upper()}", font=("Helvetica", 18, "bold")).pack(pady=20)
        campi = self.campi_d if tipo == "Driver" else self.campi_v

        for i, campo in enumerate(campi):
            fr = ctk.CTkFrame(win, fg_color="transparent")
            fr.pack(fill="x", padx=20, pady=5)
            ctk.CTkLabel(fr, text=f"{campo}:", font=("Helvetica", 12, "bold")).pack(side="left")
            valore = dati[i + 1] if tipo == "Driver" else dati[i]

            entry_selezionabile = tk.Entry(
                fr,
                font=("Helvetica", 12),
                fg="white",
                bg="#2b2b2b",
                bd=0,
                highlightthickness=0,
                justify="right"
            )
            entry_selezionabile.insert(0, str(valore))
            entry_selezionabile.configure(readonlybackground="#2b2b2b", state="readonly")
            entry_selezionabile.pack(side="right", fill="x", expand=True)

        ctk.CTkButton(win, text="CHIUDI", command=win.destroy).pack(pady=30)

    def esegui_ricerca(self, tree, col, val):
        val_lower = val.lower()
        for item in tree.get_children():
            if val_lower in str(tree.item(item)['values'][col]).lower():
                tree.selection_set(item)
                tree.see(item)
                return
        messagebox.showwarning("Ricerca", "Nessun risultato.")

    def form_veicolo(self, dati=None):
        win = ctk.CTkToplevel(self.root)
        win.geometry("400x600+10+10")
        win.attributes("-topmost", True)
        win.grab_set()
        titolo = "MODIFICA VEICOLO" if dati else "AGGIUNGI VEICOLO"
        ctk.CTkLabel(win, text=titolo, font=("Helvetica", 16, "bold")).pack(pady=15)
        vars = {}

        for i, c in enumerate(self.campi_v[:-1]):
            ctk.CTkLabel(win, text=c).pack()
            valore = ""
            if dati:
                try:
                    valore = str(dati[i])
                except IndexError:
                    valore = ""

            v = ctk.StringVar(value=valore)
            e = ctk.CTkEntry(win, textvariable=v, width=250)
            e.pack(pady=5)
            vars[c] = v
            if dati and c == "Targa": e.configure(state="disabled", fg_color="#3d3d3d")

        def salva():
            d = [vars[c].get().strip().upper() if c == "Targa" else vars[c].get().strip() for c in self.campi_v[:-1]]
            targa_nuova = d[0]
            data_assicurazione = d[4]

            if not targa_nuova:
                messagebox.showerror("Errore", "La Targa è obbligatoria!", parent=win)
                return

            if data_assicurazione:
                if not self.valida_data_stringa(data_assicurazione):
                    winsound.MessageBeep(winsound.MB_ICONHAND)
                    messagebox.showerror("Data Errata",
                                         "La data di Assicurazione deve essere nel formato valido GG/MM/AAAA\n(Es. 28/02/2026)",
                                         parent=win)
                    return

            if not dati:
                self.db.cursor.execute("SELECT targa FROM veicoli WHERE UPPER(targa)=?", (targa_nuova,))
                if self.db.cursor.fetchone():
                    messagebox.showerror("Errore Targa", f"La targa {targa_nuova} è già presente!", parent=win)
                    return
            try:
                if dati:
                    self.db.cursor.execute(
                        "UPDATE veicoli SET marca=?, modello=?, anno=?, assicurazione=?, note=? WHERE targa=?",
                        (d[1], d[2], d[3], d[4], d[5], dati[0]))
                else:
                    self.db.cursor.execute("INSERT INTO veicoli VALUES (?,?,?,?,?,?)", d)
                self.db.conn.commit()
                self.modificato = True
                self.aggiorna_dati()
                win.destroy()
            except Exception as e:
                messagebox.showerror("Errore", f"Errore: {e}", parent=win)

        ctk.CTkButton(win, text="SALVA", fg_color="#2ecc71", command=salva).pack(pady=20)

    def modifica_veicolo(self):
        sel = self.tree_v.selection()
        if sel:
            self.form_veicolo(self.tree_v.item(sel[0])['values'])
        else:
            messagebox.showwarning("Alt", "Seleziona un veicolo")

    def elimina_veicolo(self):
        sel = self.tree_v.selection()
        if sel and messagebox.askyesno("Alt", "Eliminare il veicolo selezionato?"):
            self.db.cursor.execute("DELETE FROM veicoli WHERE targa=?", (self.tree_v.item(sel[0])['values'][0],))
            self.db.conn.commit()
            self.modificato = True
            self.aggiorna_dati()

    def libera_mezzo(self):
        sel = self.tree_v.selection()
        if sel:
            self.db.cursor.execute("UPDATE driver SET targa='' WHERE targa=?", (self.tree_v.item(sel[0])['values'][0],))
            self.db.conn.commit()
            self.modificato = True
            self.aggiorna_dati()

    def popup_collega_driver(self):
        sel = self.tree_v.selection()
        if not sel: return
        targa = self.tree_v.item(sel[0])['values'][0]
        self.db.cursor.execute("SELECT id, nome, cognome FROM driver")
        d_res = self.db.cursor.fetchall()
        d_map = {f"{r[1]} {r[2]} (ID:{r[0]})": r[0] for r in d_res}
        win = ctk.CTkToplevel(self.root)
        win.geometry("400x250+10+10")
        win.attributes("-topmost", True)
        win.grab_set()
        ctk.CTkLabel(win, text=f"Assegna Driver a {targa}:").pack(pady=20)
        cb = ctk.CTkComboBox(win, values=["NESSUNO"] + list(d_map.keys()), width=280)
        cb.pack(pady=10)

        def ok():
            self.db.cursor.execute("SELECT nome, cognome FROM driver WHERE targa=?", (targa,))
            vecchio_driver = self.db.cursor.fetchone()
            scelta = cb.get()
            if scelta != "NESSUNO" and vecchio_driver:
                nome_nuovo = scelta.split(" (ID:")[0]
                nome_vecchio = f"{vecchio_driver[0]} {vecchio_driver[1]}"
                if nome_nuovo != nome_vecchio:
                    if not messagebox.askyesno("Sostituzione",
                                               f"Il mezzo {targa} è di {nome_vecchio}. Confermi il passaggio a {nome_nuovo}?",
                                               parent=win): return
            self.db.cursor.execute("UPDATE driver SET targa='' WHERE targa=?", (targa,))
            if cb.get() != "NESSUNO":
                self.db.cursor.execute("UPDATE driver SET targa=? WHERE id=?", (targa, d_map[cb.get()]))
            self.db.conn.commit()
            self.aggiorna_dati()
            win.destroy()

        ctk.CTkButton(win, text="CONFERMA", fg_color="#2ecc71", command=ok).pack(pady=20)

    def form_driver(self, dati=None):
        win = ctk.CTkToplevel(self.root)
        win.geometry("450x650+10+10")
        win.attributes("-topmost", True)
        win.grab_set()
        titolo_testo = "MODIFICA DRIVER" if dati else "AGGIUNGI DRIVER"
        win.title(titolo_testo)

        ctk.CTkLabel(win, text=titolo_testo, font=("Helvetica", 16, "bold")).pack(pady=15)

        self.db.cursor.execute("SELECT targa FROM veicoli ORDER BY targa")
        elenco_targhe = [r[0] for r in self.db.cursor.fetchall()]
        opzioni_targa = [""] + elenco_targhe

        vars = {}
        for i, c in enumerate(self.campi_d):
            ctk.CTkLabel(win, text=c).pack()
            valore_iniziale = str(dati[i + 1]) if dati else ""

            if c == "Targa":
                v = ctk.StringVar(value=valore_iniziale)
                if valore_iniziale and valore_iniziale not in opzioni_targa:
                    opzioni_targa.append(valore_iniziale)
                e = ctk.CTkComboBox(win, variable=v, values=opzioni_targa, width=250)
                e.pack(pady=2)
            else:
                v = ctk.StringVar(value=valore_iniziale)
                e = ctk.CTkEntry(win, textvariable=v, width=250)
                e.pack(pady=2)
            vars[c] = v

        def salva():
            d = [vars[c].get().strip() for c in self.campi_d]
            nome, cognome, nascita, giro = d[0], d[1], d[2], d[3]

            if not nome or not ...:
                messagebox.showerror("Errore", "Nome e Cognome sono obbligatori!", parent=win)
                return

            if nascita:
                if not self.valida_data_stringa(nascita):
                    winsound.MessageBeep(winsound.MB_ICONHAND)
                    messagebox.showerror("Data Errata",
                                         "La data di Nascita deve essere nel formato valido GG/MM/AAAA\n(Es. 14/10/1992)",
                                         parent=win)
                    return

            if dati:
                self.db.cursor.execute(
                    "SELECT id FROM driver WHERE LOWER(nome)=LOWER(?) AND LOWER(cognome)=LOWER(?) AND id != ?",
                    (nome, cognome, dati[0]))
            else:
                self.db.cursor.execute("SELECT id FROM driver WHERE LOWER(nome)=LOWER(?) AND LOWER(cognome)=LOWER(?)",
                                       (nome, cognome))

            if self.db.cursor.fetchone():
                messagebox.showwarning("Duplicato", f"Il driver {nome} {cognome} è già presente nel sistema!",
                                       parent=win)
                return

            if giro:
                if dati:
                    self.db.cursor.execute("SELECT nome, cognome FROM driver WHERE LOWER(giro)=LOWER(?) AND id != ?",
                                           (giro, dati[0]))
                else:
                    self.db.cursor.execute("SELECT nome, cognome FROM driver WHERE LOWER(giro)=LOWER(?)", (giro,))

                res_giro = self.db.cursor.fetchone()
                if res_giro:
                    messagebox.showwarning("Giro Duplicato",
                                           f"Il giro '{giro}' è già assegnato al driver {res_giro[0]} {res_giro[1]}!",
                                           parent=win)
                    return

            if dati:
                self.db.cursor.execute(
                    "UPDATE driver SET nome=?, cognome=?, nascita=?, giro=?, email=?, telefono=?, targa=?, note=? WHERE id=?",
                    (*d, dati[0]))
            else:
                self.db.cursor.execute(
                    "INSERT INTO driver (nome, cognome, nascita, giro, email, telefono, targa, note) VALUES (?,?,?,?,?,?,?,?)",
                    d)
            self.db.conn.commit()
            self.modificato = True
            self.aggiorna_dati()
            win.destroy()

        ctk.CTkButton(win, text="SALVA", fg_color="#2ecc71", command=salva).pack(pady=20)

    def modifica_driver(self):
        sel = self.tree_d.selection()
        if sel: self.form_driver(self.tree_d.item(sel[0])['values'])

    def elimina_driver(self):
        sel = self.tree_d.selection()
        if sel and messagebox.askyesno("Alt", "Eliminare il driver selezionato?"):
            self.db.cursor.execute("DELETE FROM driver WHERE id=?", (self.tree_d.item(sel[0])['values'][0],))
            self.db.conn.commit()
            self.modificato = True
            self.aggiorna_dati()

    def popup_assegna_da_driver(self):
        sel = self.tree_d.selection()
        if not sel: return
        id_d = self.tree_d.item(sel[0])['values'][0]
        self.db.cursor.execute("SELECT targa FROM veicoli")
        targhe = [t[0] for t in self.db.cursor.fetchall()]
        win = ctk.CTkToplevel(self.root)
        win.geometry("300x220")
        win.attributes("-topmost", True)
        win.grab_set()
        ctk.CTkLabel(win, text="Seleziona Targa:").pack(pady=10)
        cb = ctk.CTkComboBox(win, values=["NESSUNA"] + targhe)
        cb.pack(pady=10)

        def ok():
            t = cb.get() if cb.get() != "NESSUNA" else ""
            if t != "":
                self.db.cursor.execute("SELECT nome, cognome FROM driver WHERE targa=? AND id != ?", (t, id_d))
                esistente = self.db.cursor.fetchone()
                if esistente:
                    if not messagebox.askyesno("Targa già assegnata",
                                               f"La targa {t} è di {esistente[0]} {esistente[1]}. Vuoi spostarla?",
                                               parent=win): return
                    self.db.cursor.execute("UPDATE driver SET targa='' WHERE targa=?", (t,))
            self.db.cursor.execute("UPDATE driver SET targa=? WHERE id=?", (t, id_d))
            self.db.conn.commit()
            self.aggiorna_dati()
            win.destroy()

        ctk.CTkButton(win, text="CONFERMA", command=ok).pack(pady=10)

    def toggle_liberi(self):
        self.filtro_liberi = not self.filtro_liberi
        self.btn_liberi.configure(fg_color="#9b59b6" if self.filtro_liberi else "#444")
        self.aggiorna_dati()

    def gestione_utenti(self):
        win = ctk.CTkToplevel(self.root)
        win.geometry("500x700+10+10")
        win.title("Gestione Utenti")
        win.attributes("-topmost", True)
        win.grab_set()

        ctk.CTkLabel(win, text="NUOVO UTENTE", font=("Helvetica", 14, "bold")).pack(pady=10)
        u = ctk.CTkEntry(win, placeholder_text="Nuovo User", width=250)
        u.pack(pady=5)
        p = ctk.CTkEntry(win, placeholder_text="Nuova Pass", show="*", width=250)
        p.pack(pady=5)

        def add():
            if u.get() and p.get():
                try:
                    pw_hash = hashlib.sha256(p.get().encode()).hexdigest()
                    self.db.cursor.execute("INSERT INTO utenti VALUES (?,?,?)", (u.get(), pw_hash, "user"))
                    self.db.conn.commit()
                    messagebox.showinfo("OK", "Utente aggiunto", parent=win)
                    aggiorna_lista_utenti()
                except:
                    messagebox.showerror("Errore", "Username già esistente", parent=win)

        ctk.CTkButton(win, text="AGGIUNGI UTENTE", fg_color="#2ecc71", command=add).pack(pady=10)

        ctk.CTkLabel(win, text="CAMBIA TUA PASSWORD", font=("Helvetica", 12, "bold"), text_color="#3498db").pack(
            pady=10)
        p_new = ctk.CTkEntry(win, placeholder_text="Nuova Password", show="*", width=250)
        p_new.pack(pady=5)

        def cambia_password_admin():
            nuova = p_new.get()
            if not nuova:
                messagebox.showwarning("Alt", "Inserisci la nuova password", parent=win)
                return
            pw_hash = hashlib.sha256(nuova.encode()).hexdigest()
            self.db.cursor.execute("UPDATE utenti SET password=? WHERE username=?",
                                   (pw_hash, self.utente_attuale["nome"]))
            self.db.conn.commit()
            messagebox.showinfo("Successo", "Password aggiornata con successo!", parent=win)
            p_new.delete(0, 'end')

        ctk.CTkButton(win, text="MODIFICA TUA PASSWORD", fg_color="#2980b9", command=cambia_password_admin).pack(pady=5)

        ctk.CTkLabel(win, text="UTENTI REGISTRATI", font=("Helvetica", 14, "bold")).pack(pady=15)
        fr_list = ctk.CTkFrame(win)
        fr_list.pack(expand=True, fill="both", padx=20, pady=5)
        tree_u = ttk.Treeview(fr_list, columns=("User", "Ruolo"), show="headings", height=8)
        tree_u.heading("User", text="USERNAME")
        tree_u.heading("Ruolo", text="RUOLO")
        tree_u.column("User", width=150, anchor="center")
        tree_u.column("Ruolo", width=100, anchor="center")
        tree_u.pack(side="left", expand=True, fill="both")

        def aggiorna_lista_utenti():
            for i in tree_u.get_children(): tree_u.delete(i)
            self.db.cursor.execute("SELECT username, ruolo FROM utenti")
            for row in self.db.cursor.fetchall(): tree_u.insert("", "end", values=row)

        def elimina_utente():
            sel = tree_u.selection()
            if not sel: return
            user_to_del = tree_u.item(sel[0])['values'][0]
            if user_to_del == self.utente_attuale["nome"]:
                messagebox.showerror("Errore", "Non puoi eliminare te stesso!", parent=win)
                return
            if messagebox.askyesno("Conferma", f"Eliminare '{user_to_del}'?", parent=win):
                self.db.cursor.execute("DELETE FROM utenti WHERE username=?", (user_to_del,))
                self.db.conn.commit()
                aggiorna_lista_utenti()

        ctk.CTkButton(win, text="🗑️ ELIMINA SELEZIONATO", fg_color="#e74c3c", command=elimina_utente).pack(pady=15)
        aggiorna_lista_utenti()

    def on_closing(self):
        self.salva_configurazione_completa()
        if self.modificato:
            winsound.MessageBeep(winsound.MB_OK)
            risposta = messagebox.askyesnocancel("Esci", "Ci sono modifiche non salvate. Salvare?")
            if risposta is True:
                self.file_salva()
                self.root.destroy()
            elif risposta is False:
                self.root.destroy()
        else:
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
            if messagebox.askyesno("Esci", "Sei sicuro di voler uscire?"): self.root.destroy()


if __name__ == "__main__":
    app = SistemaGestionaleFlotta(ctk.CTk())
    app.root.mainloop()
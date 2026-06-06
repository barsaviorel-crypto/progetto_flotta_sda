import customtkinter as ctk
from tkinter import messagebox, filedialog, ttk
import pandas as pd
import json
import os
import re
from datetime import datetime

# Impostazioni Tema
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class SistemaGestionaleFlotta:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestione Flotta Pro - by Viorel")
        self.root.geometry("1400x850+0+0")

        # --- 1. DEFINIZIONE VARIABILI STRUTTURALI (FONDAMENTALI) ---
        # Definiamo i campi qui così l'interfaccia sa sempre cosa disegnare
        self.campi_d = ["Nome", "Cognome", "Nascita", "Giro", "Email", "Telefono", "Targa", "Note"]
        self.campi_v = ["Targa", "Marca", "Modello", "Anno", "Assicurazione", "Stato"]

        self.file_database = "database_flotta.json"
        self.file_utenti = "utenti.json"

        # Font e stati
        self.font_titoli = ("Helvetica", 18, "bold")
        self.font_standard = ("Helvetica", 14)
        self.font_bottoni = ("Helvetica", 13, "bold")
        self.utente_attuale = None
        self.modificato = False
        self.filtro_veicoli_liberi = False

        # --- 2. PREPARAZIONE DATI ---
        self.root.withdraw()
        self.carica_dati_iniziali()

        # --- 3. AVVIO LOGICA ACCESSO ---
        self.root.protocol("WM_DELETE_WINDOW", self.chiedi_conferma_uscita)
        self.gestisci_accesso()

    # --- LOGICA DI CARICAMENTO E SALVATAGGIO ---
    def carica_dati_iniziali(self):
        # Inizializza sempre DataFrame vuoti con le colonne corrette
        self.df_driver = pd.DataFrame(columns=self.campi_d)
        self.df_veicoli = pd.DataFrame(columns=self.campi_v[:-1])  # Stato è calcolato

        if os.path.exists(self.file_database):
            try:
                with open(self.file_database, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    df_d_temp = pd.DataFrame(data.get('driver', []))
                    df_v_temp = pd.DataFrame(data.get('veicoli', []))

                    # Se il file ha dati, sovrascrivi i DF vuoti
                    if not df_d_temp.empty:
                        self.df_driver = df_d_temp
                    if not df_v_temp.empty:
                        self.df_veicoli = df_v_temp
            except Exception as e:
                print(f"Errore caricamento dati: {e}")

    def azione_salva(self):
        d = {"driver": self.df_driver.to_dict(orient='records'), "veicoli": self.df_veicoli.to_dict(orient='records')}
        try:
            with open(self.file_database, 'w', encoding='utf-8') as f:
                json.dump(d, f, indent=4)
            self.modificato = False
            messagebox.showinfo("OK", "Dati salvati correttamente!")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel salvataggio: {e}")

    def salva_con_nome(self):
        f = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Database JSON", "*.json")])
        if f:
            self.file_database = f
            self.azione_salva()

    def apri_file(self):
        f = filedialog.askopenfilename(filetypes=[("Database JSON", "*.json")])
        if f:
            self.file_database = f
            self.carica_dati_iniziali()
            self.aggiorna_tutto()

    def chiedi_conferma_uscita(self):
        if self.modificato:
            risposta = messagebox.askyesnocancel("Salvataggio",
                                                 "Ci sono modifiche non salvate.\nVuoi salvare prima di uscire?")
            if risposta is True:
                self.azione_salva()
                self.root.destroy()
            elif risposta is False:
                self.root.destroy()
        else:
            if messagebox.askyesno("Esci", "Vuoi veramente uscire?"):
                self.root.destroy()

    # --- INTERFACCIA E WIDGETS ---
    def crea_treeview(self, parent, colonne):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#2b2b2b", foreground="white", fieldbackground="#2b2b2b", rowheight=35,
                        font=("Helvetica", 14))
        style.configure("Treeview.Heading", background="#1f538d", foreground="white", font=("Helvetica", 16, "bold"),
                        padding=(0, 10))
        tree = ttk.Treeview(parent, columns=colonne, show='headings')
        for c in colonne:
            tree.heading(c, text=c.upper())
            tree.column(c, width=110, anchor="center")
        tree.tag_configure('scaduto', background='#721c24', foreground="white")
        tree.tag_configure('avviso', background='#f1c40f', foreground="black")
        return tree

    def setup_tab_driver(self):
        perm = "normal" if self.utente_attuale["ruolo"] == "admin" else "disabled"
        bf = ctk.CTkFrame(self.tab_driver, fg_color="transparent")
        bf.pack(fill="x", padx=10, pady=10)

        ctk.CTkButton(bf, text="➕ AGGIUNGI", command=self.popup_driver, fg_color="#2ecc71", state=perm).pack(
            side="left", padx=5)
        ctk.CTkButton(bf, text="📝 MODIFICA", command=self.modifica_driver_selezionato, fg_color="#3498db",
                      state=perm).pack(side="left", padx=5)
        ctk.CTkButton(bf, text="🗑️ ELIMINA", command=self.elimina_driver, fg_color="#e74c3c", state=perm).pack(
            side="left", padx=5)
        ctk.CTkButton(bf, text="🔗 ASSEGNA TARGA", command=self.assegna_targa_a_driver, fg_color="#9b59b6",
                      state=perm).pack(side="left", padx=5)
        ctk.CTkButton(bf, text="🔍CERCA GIRO", command=lambda: self.popup_ricerca("Giro"), fg_color="#f1c40f",
                      text_color="black").pack(side="right", padx=5)

        self.tree_d = self.crea_treeview(self.tab_driver, self.campi_d)
        self.tree_d.pack(fill="both", expand=True, padx=10)

    def setup_tab_veicoli(self):
        perm = "normal" if self.utente_attuale["ruolo"] == "admin" else "disabled"
        bf = ctk.CTkFrame(self.tab_veicoli, fg_color="transparent")
        bf.pack(fill="x", padx=10, pady=10)

        ctk.CTkButton(bf, text="➕ AGGIUNGI", command=self.popup_veicolo, fg_color="#2ecc71", state=perm).pack(
            side="left", padx=5)
        ctk.CTkButton(bf, text="📝 MODIFICA", command=self.modifica_veicolo_selezionato, fg_color="#3498db",
                      state=perm).pack(side="left", padx=5)
        ctk.CTkButton(bf, text="🗑️ ELIMINA", command=self.elimina_v, fg_color="#e74c3c", state=perm).pack(side="left",
                                                                                                          padx=5)
        ctk.CTkButton(bf, text="🔓 LIBERA", command=self.libera_veicolo_selezionato, fg_color="#e67e22",
                      state=perm).pack(side="left", padx=5)
        ctk.CTkButton(bf, text="👤 COLLEGA DRIVER", command=self.collega_driver_a_veicolo, fg_color="#1abc9c",
                      state=perm).pack(side="left", padx=5)
        ctk.CTkButton(bf, text="🔍 CERCA TARGA", command=lambda: self.popup_ricerca("Targa"), fg_color="#f1c40f",
                      text_color="black").pack(side="right", padx=5)
        ctk.CTkButton(bf, text="🔍 LIBERI", fg_color="#8e44ad", command=self.toggle_liberi).pack(side="right", padx=5)

        self.tree_v = self.crea_treeview(self.tab_veicoli, self.campi_v)
        self.tree_v.pack(fill="both", expand=True, padx=10)

    # --- LOGICA ACCESSI E UTENTI ---
    def gestisci_accesso(self):
        if not os.path.exists(self.file_utenti):
            self.crea_primo_admin()
        else:
            self.mostra_login()

    def mostra_login(self):
        win = ctk.CTkToplevel(self.root)
        win.title("Login")
        win.geometry("400x350+100+100")
        win.attributes('-topmost', True)
        ctk.CTkLabel(win, text="ACCESSO SISTEMA", font=self.font_titoli).pack(pady=30)
        u_ent = ctk.CTkEntry(win, placeholder_text="Username", width=200)
        u_ent.pack(pady=10)
        p_ent = ctk.CTkEntry(win, placeholder_text="Password", show="*", width=200)
        p_ent.pack(pady=10)

        def verifica():
            with open(self.file_utenti, 'r') as f:
                uts = json.load(f)
            u, p = u_ent.get(), p_ent.get()
            if u in uts and uts[u]["pass"] == p:
                self.utente_attuale = {"nome": u, "ruolo": uts[u]["ruolo"]}
                win.destroy()
                self.avvia_applicazione()
            else:
                messagebox.showerror("Errore", "Credenziali errate", parent=win)

        ctk.CTkButton(win, text="Entra", command=verifica, width=150).pack(pady=30)

    def crea_primo_admin(self):
        win = ctk.CTkToplevel(self.root)
        win.title("Setup Iniziale")
        win.geometry("400x350+100+100")
        u_v, p_v = ctk.StringVar(), ctk.StringVar()
        ctk.CTkLabel(win, text="CREA ADMIN", font=self.font_titoli).pack(pady=20)
        ctk.CTkEntry(win, textvariable=u_v, placeholder_text="Username").pack(pady=5)
        ctk.CTkEntry(win, textvariable=p_v, placeholder_text="Password", show="*").pack(pady=5)

        def salva():
            if u_v.get() and p_v.get():
                with open(self.file_utenti, 'w') as f:
                    json.dump({u_v.get(): {"pass": p_v.get(), "ruolo": "admin"}}, f, indent=4)
                win.destroy()
                self.mostra_login()

        ctk.CTkButton(win, text="Salva Admin", command=salva).pack(pady=20)

    def avvia_applicazione(self):
        self.root.deiconify()
        perm_admin = "normal" if self.utente_attuale["ruolo"] == "admin" else "disabled"

        # Menu Superiore
        menu = ctk.CTkFrame(self.root, height=60, fg_color="#1e1e1e")
        menu.pack(side="top", fill="x", padx=5, pady=5)

        ctk.CTkButton(menu, text="💾 SALVA", fg_color="#2ecc71", width=90, command=self.azione_salva,
                      state=perm_admin).pack(side="left", padx=5)
        ctk.CTkButton(menu, text="📂 APRI", fg_color="#34495e", width=90, command=self.apri_file, state=perm_admin).pack(
            side="left", padx=5)
        ctk.CTkButton(menu, text="💾 SALVA CON...", fg_color="#34495e", width=110, command=self.salva_con_nome,
                      state=perm_admin).pack(side="left", padx=5)
        ctk.CTkButton(menu, text="📤 ESPORTA", fg_color="#d35400", width=100, command=self.popup_esporta,
                      state=perm_admin).pack(side="left", padx=5)
        ctk.CTkButton(menu, text="❌ ESCI", fg_color="#e74c3c", width=90, command=self.chiedi_conferma_uscita).pack(
            side="right", padx=10)
        ctk.CTkLabel(menu, text=f"👤 {self.utente_attuale['nome'].upper()}", font=self.font_bottoni).pack(side="right",
                                                                                                         padx=20)

        # Tab View
        self.tabs = ctk.CTkTabview(self.root)
        self.tabs._segmented_button.configure(font=("Helvetica", 16, "bold"))
        self.tabs.pack(expand=True, fill="both", padx=10, pady=5)

        self.tab_driver = self.tabs.add("       👤 Anagrafica & Giri      ")
        self.tab_veicoli = self.tabs.add("       🚛 Parco Veicoli         ")

        self.setup_tab_driver()
        self.setup_tab_veicoli()

        if self.utente_attuale["ruolo"] == "admin":
            ctk.CTkButton(self.root, text="⚙️ UTENTI", command=self.apri_gestione_utenti, fg_color="#607D8B").pack(
                side="bottom", anchor="e", padx=20, pady=10)

        self.aggiorna_tutto()

    # --- AGGIORNAMENTO TREEVIEW ---
    def aggiorna_tutto(self):
        # Update Driver
        for i in self.tree_d.get_children(): self.tree_d.delete(i)
        for _, r in self.df_driver.iterrows():
            self.tree_d.insert("", "end", values=[r.get(c, "") for c in self.campi_d])

        # Update Veicoli
        for i in self.tree_v.get_children(): self.tree_v.delete(i)
        mappa = {r['Targa']: f"{r['Nome']} {r['Cognome']}" for _, r in self.df_driver.iterrows() if r.get('Targa')}
        oggi = datetime.now()

        for _, r in self.df_veicoli.iterrows():
            st = mappa.get(r['Targa'], "Disponibile")
            if self.filtro_veicoli_liberi and st != "Disponibile": continue

            tag = ()
            data_ins = r.get("Assicurazione")
            if data_ins and data_ins.strip():
                try:
                    data_scadenza = datetime.strptime(data_ins, "%d/%m/%Y")
                    giorni_mancanti = (data_scadenza - oggi).days
                    if giorni_mancanti < 0:
                        tag = ('scaduto',)
                    elif giorni_mancanti <= 30:
                        tag = ('avviso',)
                except ValueError:
                    pass

            valori = [r.get(c, "") for c in self.campi_v[:-1]] + [st]
            self.tree_v.insert("", "end", values=valori, tags=tag)

    # --- POPUP OPERATIVI ---
    def popup_driver(self, dati=None):
        win = ctk.CTkToplevel(self.root)
        win.geometry("500x650+10+10")
        win.grab_set()
        fr = ctk.CTkFrame(win, fg_color="transparent")
        fr.pack(expand=True, fill="both", padx=40, pady=20)
        loc_vars = {}
        for i, c in enumerate(self.campi_d):
            ctk.CTkLabel(fr, text=c).grid(row=i, column=0, sticky="w", pady=5)
            v = ctk.StringVar(value=str(dati[i]) if dati else "")
            if c == "Targa":
                ent = ctk.CTkComboBox(fr, variable=v, values=[""] + sorted(self.df_veicoli['Targa'].tolist()),
                                      width=220)
            else:
                ent = ctk.CTkEntry(fr, textvariable=v, width=220)
            if c == "Nascita": ent.bind("<KeyRelease>", lambda e, w=ent, var=v: self.formatta_data(e, w, var))
            ent.grid(row=i, column=1, pady=5, padx=10)
            loc_vars[c] = v

        def salva():
            nome, cognome, giro = loc_vars["Nome"].get().strip(), loc_vars["Cognome"].get().strip(), loc_vars[
                "Giro"].get().strip()
            if not dati:
                if not self.df_driver[(self.df_driver['Nome'] == nome) & (self.df_driver['Cognome'] == cognome)].empty:
                    if not messagebox.askyesno("Attenzione", f"{nome} {cognome} esiste già. Continuare?",
                                               parent=win): return
                if giro:
                    giro_occupato = self.df_driver[self.df_driver['Giro'] == giro]
                    if not giro_occupato.empty:
                        msg = f"Il giro '{giro}' è già assegnato a {giro_occupato.iloc[0]['Nome']}.\nVuoi procedere?"
                        if not messagebox.askyesno("Giro Duplicato", msg, parent=win): return

            d = {k: var.get().strip() for k, var in loc_vars.items()}
            if dati:
                self.df_driver = self.df_driver[
                    ~((self.df_driver['Nome'] == str(dati[0])) & (self.df_driver['Cognome'] == str(dati[1])))]
            self.df_driver = pd.concat([self.df_driver, pd.DataFrame([d])], ignore_index=True)
            self.modificato = True
            self.aggiorna_tutto()
            win.destroy()

        ctk.CTkButton(win, text="SALVA", fg_color="#2ecc71", command=salva).pack(pady=20)

    def popup_veicolo(self, dati=None):
        win = ctk.CTkToplevel(self.root)
        win.geometry("450x550+10+10")
        win.grab_set()
        fr = ctk.CTkFrame(win, fg_color="transparent")
        fr.pack(expand=True, fill="both", padx=30, pady=20)
        loc_vars = {}
        for i, c in enumerate(self.campi_v[:-1]):
            ctk.CTkLabel(fr, text=c).grid(row=i, column=0, sticky="w", pady=5)
            v = ctk.StringVar(value=str(dati[i]) if dati else "")
            ent = ctk.CTkEntry(fr, textvariable=v, width=220)
            if c == "Assicurazione": ent.bind("<KeyRelease>", lambda e, w=ent, var=v: self.formatta_data(e, w, var))
            ent.grid(row=i, column=1, pady=5, padx=10)
            loc_vars[c] = v

        def salva():
            t = loc_vars["Targa"].get().strip().upper()
            if not dati and t in self.df_veicoli['Targa'].values:
                messagebox.showerror("Errore", "Targa già presente!", parent=win);
                return
            d = {k: var.get().strip().upper() for k, var in loc_vars.items()}
            self.df_veicoli = self.df_veicoli[self.df_veicoli['Targa'] != d["Targa"]]
            self.df_veicoli = pd.concat([self.df_veicoli, pd.DataFrame([d])], ignore_index=True)
            self.modificato = True
            self.aggiorna_tutto()
            win.destroy()

        ctk.CTkButton(win, text="SALVA MEZZO", fg_color="#2ecc71", command=salva).pack(pady=20)

    def formatta_data(self, event, widget, var):
        if event.keysym in ("BackSpace", "Delete"): return
        t = "".join(re.findall(r'\d', var.get()))[:8]
        nt = "".join([c + ("/" if i in (1, 3) and i < len(t) - 1 else "") for i, c in enumerate(t)])
        if var.get() != nt: var.set(nt); widget.icursor(ctk.END)

    def toggle_liberi(self):
        self.filtro_veicoli_liberi = not self.filtro_veicoli_liberi
        self.aggiorna_tutto()

    # --- METODI AUSILIARI (RICERCA, ELIMINA, UTENTI) ---
    def popup_ricerca(self, tipo):
        win = ctk.CTkToplevel(self.root)
        win.geometry("350x200+10+10")
        win.grab_set()
        ctk.CTkLabel(win, text=f"CERCA {tipo.upper()}").pack(pady=20)
        ent = ctk.CTkEntry(win, width=250);
        ent.pack(pady=10);
        ent.focus()

        def esegui():
            val = ent.get().strip().lower()
            tree = self.tree_d if tipo == "Giro" else self.tree_v
            idx = 3 if tipo == "Giro" else 0
            for item in tree.get_children():
                if val in str(tree.item(item)['values'][idx]).lower():
                    tree.selection_set(item);
                    tree.see(item);
                    win.destroy();
                    return
            messagebox.showinfo("Esito", "Non trovato", parent=win)

        ctk.CTkButton(win, text="CERCA", command=esegui).pack(pady=10)

    def apri_gestione_utenti(self):
        win = ctk.CTkToplevel(self.root);
        win.title("Utenti");
        win.geometry("600x600+10+10");
        win.grab_set()
        tree = self.crea_treeview(win, ("Username", "Ruolo"));
        tree.pack(fill="both", expand=True, padx=20, pady=10)

        def ricarica():
            for i in tree.get_children(): tree.delete(i)
            with open(self.file_utenti, 'r') as f:
                uts = json.load(f)
                for u, info in uts.items(): tree.insert("", "end", values=(u, info["ruolo"]))

        ricarica()
        fr = ctk.CTkFrame(win, fg_color="transparent");
        fr.pack(fill="x", padx=20, pady=10)
        u_e = ctk.CTkEntry(fr, placeholder_text="User", width=140);
        u_e.grid(row=0, column=0, padx=5)
        p_e = ctk.CTkEntry(fr, placeholder_text="Pass", show="*", width=140);
        p_e.grid(row=0, column=1, padx=5)

        def aggiungi():
            if u_e.get() and p_e.get():
                with open(self.file_utenti, 'r') as f: uts = json.load(f)
                uts[u_e.get()] = {"pass": p_e.get(), "ruolo": "user"}
                with open(self.file_utenti, 'w') as f: json.dump(uts, f, indent=4)
                ricarica()

        ctk.CTkButton(fr, text="➕ AGGIUNGI", command=aggiungi, fg_color="#2ecc71").grid(row=0, column=2, padx=5)

        def elimina():
            sel = tree.selection()
            if sel:
                u_sel = tree.item(sel[0])['values'][0]
                if u_sel == self.utente_attuale["nome"]: messagebox.showerror("No", "Non puoi eliminarti!",
                                                                              parent=win); return
                with open(self.file_utenti, 'r') as f:
                    uts = json.load(f)
                if u_sel in uts: del uts[u_sel]
                with open(self.file_utenti, 'w') as f:
                    json.dump(uts, f, indent=4)
                ricarica()

        ctk.CTkButton(win, text="🗑️ ELIMINA", command=elimina, fg_color="#e74c3c").pack(pady=20)

    def popup_esporta(self):
        win = ctk.CTkToplevel(self.root);
        win.geometry("400x350+10+10");
        win.grab_set()
        ctk.CTkLabel(win, text="COSA VUOI ESPORTARE?", font=self.font_bottoni).pack(pady=20)
        tipo_var = ctk.StringVar(value="Driver")
        ctk.CTkRadioButton(win, text="Driver", variable=tipo_var, value="Driver").pack(pady=5)
        ctk.CTkRadioButton(win, text="Veicoli", variable=tipo_var, value="Veicoli").pack(pady=5)
        ctk.CTkLabel(win, text="FORMATO:", font=self.font_bottoni).pack(pady=15)
        formato_var = ctk.StringVar(value="CSV")
        ctk.CTkSegmentedButton(win, values=["CSV", "JSON"], variable=formato_var).pack(pady=5)

        def esegui():
            df = self.df_driver if tipo_var.get() == "Driver" else self.df_veicoli
            fmt = formato_var.get().lower()
            f = filedialog.asksaveasfilename(defaultextension=f".{fmt}",
                                             filetypes=[(f"File {fmt.upper()}", f"*.{fmt}")])
            if f:
                try:
                    if fmt == "csv":
                        df.to_csv(f, index=False, sep=';', encoding='utf-8-sig')
                    else:
                        df.to_json(f, orient='records', indent=4)
                    messagebox.showinfo("OK", "Esportazione completata!", parent=win);
                    win.destroy()
                except Exception as e:
                    messagebox.showerror("Errore", str(e), parent=win)

        ctk.CTkButton(win, text="SCARICA", fg_color="#2ecc71", command=esegui).pack(pady=30)

    def assegna_targa_a_driver(self):
        sel = self.tree_d.selection()
        if not sel: return
        valori = self.tree_d.item(sel[0])['values']
        nome, cognome = valori[0], valori[1]
        targhe_occupate = self.df_driver['Targa'].dropna().unique().tolist()
        targhe_disponibili = [t for t in self.df_veicoli['Targa'].tolist() if t not in targhe_occupate or t == ""]
        win = ctk.CTkToplevel(self.root);
        win.geometry("350x250+10+10");
        win.grab_set()
        ctk.CTkLabel(win, text=f"Scegli targa per {nome} {cognome}").pack(pady=20)
        cb = ctk.CTkComboBox(win, values=["NESSUNA"] + sorted(targhe_disponibili), width=200);
        cb.pack(pady=10)

        def conferma():
            t = cb.get() if cb.get() != "NESSUNA" else ""
            idx = self.df_driver[(self.df_driver['Nome'] == nome) & (self.df_driver['Cognome'] == cognome)].index
            if not idx.empty:
                self.df_driver.at[idx[0], 'Targa'] = t
                self.modificato = True;
                self.aggiorna_tutto();
                win.destroy()

        ctk.CTkButton(win, text="CONFERMA", command=conferma).pack(pady=20)

    def collega_driver_a_veicolo(self):
        sel = self.tree_v.selection()
        if not sel: return
        targa = self.tree_v.item(sel[0])['values'][0]
        driver_nomi = [f"{r['Nome']} {r['Cognome']}" for _, r in self.df_driver.iterrows()]
        win = ctk.CTkToplevel(self.root);
        win.geometry("350x250+10+10");
        win.grab_set()
        ctk.CTkLabel(win, text=f"Chi guida il mezzo {targa}?").pack(pady=20)
        cb = ctk.CTkComboBox(win, values=sorted(driver_nomi), width=200);
        cb.pack(pady=10)

        def conferma():
            scelto = cb.get()
            if scelto:
                parti = scelto.split(" ")
                n, c = parti[0], " ".join(parti[1:])
                self.df_driver.loc[self.df_driver['Targa'] == targa, 'Targa'] = ""
                idx = self.df_driver[(self.df_driver['Nome'] == n) & (self.df_driver['Cognome'] == c)].index
                if not idx.empty:
                    self.df_driver.at[idx[0], 'Targa'] = targa
                    self.modificato = True;
                    self.aggiorna_tutto();
                    win.destroy()

        ctk.CTkButton(win, text="ASSEGNA", command=conferma).pack(pady=20)

    def elimina_driver(self):
        sel = self.tree_d.selection()
        if sel and messagebox.askyesno("Confirm", "Elimina?"):
            v = self.tree_d.item(sel[0])['values']
            self.df_driver = self.df_driver[
                ~((self.df_driver['Nome'] == str(v[0])) & (self.df_driver['Cognome'] == str(v[1])))]
            self.modificato = True;
            self.aggiorna_tutto()

    def elimina_v(self):
        sel = self.tree_v.selection()
        if sel and messagebox.askyesno("Confirm", "Elimina?"):
            t = self.tree_v.item(sel[0])['values'][0]
            self.df_veicoli = self.df_veicoli[self.df_veicoli['Targa'] != t]
            self.modificato = True;
            self.aggiorna_tutto()

    def libera_veicolo_selezionato(self):
        sel = self.tree_v.selection()
        if sel:
            t = self.tree_v.item(sel[0])['values'][0]
            self.df_driver.loc[self.df_driver['Targa'] == t, 'Targa'] = ""
            self.modificato = True;
            self.aggiorna_tutto()

    def modifica_driver_selezionato(self):
        sel = self.tree_d.selection()
        if sel: self.popup_driver(self.tree_d.item(sel[0])['values'])

    def modifica_veicolo_selezionato(self):
        sel = self.tree_v.selection()
        if sel: self.popup_veicolo(self.tree_v.item(sel[0])['values'])


if __name__ == "__main__":
    root = ctk.CTk()
    app = SistemaGestionaleFlotta(root)
    root.mainloop()
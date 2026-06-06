import sqlite3
import hashlib
import json
import os
import getpass
#import base64
# Implementiamo la protezione del script
print("Made by Bars Media".center(100))
def password():
    while True:
        dati = getpass.getpass("Inserisci il password per iniziare: ")
        if dati == "vbarsa06051977":
            print("Accesso consentito!!!")

            break
        else:
            print("Errato, riprovare!!!")
password()
def scegli_database():
    print("=== RIPRISTINO PASSWORD GESTIONALE ===")

    # 1. Cerca l'ultimo database usato nel config (se esiste)
    db_config = None
    if os.path.exists("config.json"):
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                db_config = json.load(f).get("ultimo_db")
        except:
            pass

    # 2. Trova tutti i file .db nella cartella corrente
    file_db = [f for f in os.listdir('.') if f.endswith('.db')]

    print("\nDatabase rilevati nella cartella corrente:")
    for i, file in enumerate(file_db, 1):
        nota = " (Ultimo utilizzato)" if file == db_config or (
                    db_config and os.path.basename(db_config) == file) else ""
        print(f"[{i}] {file}{nota}")

    print(f"[{len(file_db) + 1}] Inserisci un percorso personalizzato a mano...")

    # 3. Input dell'utente per la scelta
    while True:
        try:
            scelta = input("\nSeleziona il numero del database da modificare: ").strip()
            scelta_int = int(scelta)

            if 1 <= scelta_int <= len(file_db):
                return file_db[scelta_int - 1]
            elif scelta_int == len(file_db) + 1:
                percorso = input("Inserisci il percorso completo o il nome del file .db: ").strip()
                if os.path.exists(percorso):
                    return percorso
                else:
                    print("⚠️ Il file specificato non esiste. Riprova.")
            else:
                print("⚠️ Numero non valido. Scegli uno dei numeri in elenco.")
        except ValueError:
            print("⚠️ Inserisci un numero valido.")


# Esecuzione dello script
if __name__ == "__main__":
    db_scelto = scegli_database()
    print(f"\nHai selezionato: {db_scelto}")

    # Richiede i dati per il reset
    nuovo_utente = input("Inserisci lo Username da resettare (es. admin): ").strip()
    nuova_password = input("Inserisci la NUOVA Password desiderata: ").strip()

    if not nuovo_utente or not nuova_password:
        print("❌ Errore: Username e Password non possono essere vuoti.")
        input("\nPremi Invio per uscire...")
        exit()

    try:
        conn = sqlite3.connect(db_scelto)
        cursor = conn.cursor()

        # Genera l'hash SHA-256 richiesto dal tuo sistema
        password_hash = hashlib.sha256(nuova_password.encode()).hexdigest()

        # Tenta l'aggiornamento
        cursor.execute("UPDATE utenti SET password=? WHERE username=?", (password_hash, nuovo_utente))

        if cursor.rowcount == 0:
            # Se l'utente scritto non esiste, chiede se crearlo
            crea = input(
                f"L'utente '{nuovo_utente}' non esiste in questo database. Vuoi crearlo come Admin? (s/n): ").strip().lower()
            if crea == 's':
                cursor.execute("INSERT INTO utenti VALUES (?,?,?)", (nuovo_utente, password_hash, "admin"))
                print(f"✅ Utente '{nuovo_utente}' creato da zero con ruolo Admin!")
            else:
                print("❌ Operazione annullata.")
                conn.close()
                input("\nPremi Invio per uscire...")
                exit()
        else:
            print(f"✅ Password per l'utente '{nuovo_utente}' aggiornata con successo!")

        conn.commit()
        conn.close()

        print("\n=== OPERAZIONE COMPLETATA ===")
        print(f"Ora puoi avviare il gestionale e accedere a '{db_scelto}' con le nuove credenziali.")

    except Exception as e:
        print(f"❌ Errore durante la connessione o la modifica del database: {e}")

    input("\nPremi Invio per chiudere lo script...")
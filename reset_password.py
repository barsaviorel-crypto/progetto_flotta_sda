import sqlite3
import hashlib
import json
import os

# 1. Recupera il database corretto (legge l'ultimo aperto se esiste il config)
db_path = "database_flotta_pro.db"
if os.path.exists("config.json"):
    try:
        with open("config.json", "r") as f:
            db_path = json.load(f).get("ultimo_db", db_path)
    except:
        pass

# 2. Connessione e reset della password
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Scegli qui il nome utente e la nuova password (es: user='admin', password='password123')
    nuovo_utente = "admin"
    nuova_password_in_chiaro = "admin"

    # Genera l'hash SHA-256 corretto richiesto dal tuo programma
    password_hash = hashlib.sha256(nuova_password_in_chiaro.encode()).hexdigest()

    # Aggiorna la password nel database
    cursor.execute("UPDATE utenti SET password=? WHERE username=?", (password_hash, nuovo_utente))

    if cursor.rowcount == 0:
        # Se l'utente non esisteva affatto, lo crea da zero come admin
        cursor.execute("INSERT INTO utenti VALUES (?,?,?)", (nuovo_utente, password_hash, "admin"))
        print(f"Utente '{nuovo_utente}' non trovato. Creato da zero con ruolo Admin!")
    else:
        print(f"Password per l'utente '{nuovo_utente}' ripristinata con successo!")

    conn.commit()
    conn.close()

    print(f"Ora puoi accedere usando:\nUsername: {nuovo_utente}\nPassword: {nuova_password_in_chiaro}")

except Exception as e:
    print(f"Errore durante il reset: {e}")
import base64
import os
import getpass
print("Made by Bars Media".center(100))

def genera_licenza_per_cliente(hwid_cliente):
    # Criptiamo l'ID del cliente in Base64 (giusto per non farlo leggere in chiaro)
    chiave = base64.b64encode(hwid_cliente.encode()).decode()
    with open("license.key", "w") as f:
        f.write(chiave)
    print("\nFile 'license.key' generato con successo. Invialo al cliente!")

# Chiede l'ID all'utente direttamente dal terminale
print("--- GENERATORE DI LICENZE ---")
id_ricevuto = input("Incolla qui l'ID che ti ha mandato il cliente: ").strip()

# Verifica che l'utente non abbia premuto invio per sbaglio lasciando il campo vuoto
if id_ricevuto:
    genera_licenza_per_cliente(id_ricevuto)
else:
    print("Errore: Non hai inserito alcun ID. Riavvia il programma e riprova.")
import base64
import os
import getpass
print("Made by Bars Media".center(100))


def genera_licenza_per_cliente(hwid_cliente):
    try:
        # Criptiamo l'ID in Base64
        chiave = base64.b64encode(hwid_cliente.strip().encode()).decode()

        with open("license.key", "w") as f:
            f.write(chiave)

        print(f"\n[OK] File 'license.key' generato per l'ID: {hwid_cliente}")
        print(f"Percorso: {os.path.abspath('license.key')}\n")
    except Exception as e:
        print(f"[ERRORE] Qualcosa è andato storto: {e}")


if __name__ == "__main__":
    print("--- GENERATORE DI LICENZE ---")
    while True:
        id_ricevuto = input("Inserisci l'ID del cliente (o scrivi 'esci' per chiudere): ")

        if id_ricevuto.lower() == 'esci':
            break

        if id_ricevuto.strip():
            genera_licenza_per_cliente(id_ricevuto)
        else:
            print("ID non valido. Riprova.")
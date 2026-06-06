import base64

def genera_licenza_per_cliente(hwid_cliente):
    # Criptiamo l'ID del cliente in Base64 (giusto per non farlo leggere in chiaro)
    chiave = base64.b64encode(hwid_cliente.encode()).decode()
    with open("license.key", "w") as f:
        f.write(chiave)
    print("File 'license.key' generato con successo. Invialo al cliente!")

# Esempio d'uso: incolla qui l'ID che ti manda il cliente
id_ricevuto = "4C4C4544-0032-5710-8054-B2C04F533734"
genera_licenza_per_cliente(id_ricevuto)
import folium
import json
import pandas as pd
import paho.mqtt.client as mqtt
import plotly.graph_objects as go
import re
import requests
import streamlit as st
import threading
import time
from io import StringIO
from streamlit_folium import folium_static

# Configuration MQTT
BROKER = "194.57.103.203"
PORT = 1883
TOPIC = "antenne"

antennes_reims = {
    "402129": {"tac": 5102, "adresse": "15 Rue de l'Escaut, 51100 Reims", "latitude": "49.247917", "longitude": "4.067603"},
    "401892": {"tac": 5101, "adresse": "23 Bd Pasteur, 51100 Reims", "latitude": "49.249539", "longitude": "4.043129"},
    "2523": {"tac": -1, "adresse": "5 R des Moulins, 51100 Reims", "latitude": "49.246018", "longitude": "4.037953"},
    "413895": {"tac": 5101, "adresse": "40 Rue St-Léonard, 51100 Reims", "latitude": "49.232829", "longitude": "4.059376"},
    "402522": {"tac": 5102, "adresse": "2 All du Bellay, 51100 Reims", "latitude": "49.238848", "longitude": "4.041301"},
    "403850": {"tac": 5102, "adresse": "36 rue Maison Blanche, 51100 Reims", "latitude": "49.237869", "longitude": "4.028901"},
    "2110": {"tac": 5101, "adresse": "5 BD Franchet d'Esperey Tour Franchet, 51100 Reims", "latitude": "49.24194", "longitude": "4.01667"},
    "402111": {"tac": 5101, "adresse": "18 R des Bons Malades, 51100 Reims", "latitude": "49.249639", "longitude": "4.015367"},
    "22729": {"tac": 5101, "adresse": "31, r Paul Doumer Hôtel Mercure, 51100 Reims", "latitude": "49.242622", "longitude": "4.027535"},
    "408493": {"tac": 5101, "adresse": "15 Rue Jadart, 51100 Reims", "latitude": "49.25278", "longitude": "4.02944"},
    "408045": {"tac": 5101, "adresse": "28 r Buirette parc auto Buirette, 51100 Reims", "latitude": "49.2558881", "longitude": "4.0229961"},
    "402392": {"tac": 5101, "adresse": "1 r de l'Arbalète, 51100 Reims", "latitude": "49.25643", "longitude": "4.03225"},
    "402175": {"tac": 5101, "adresse": "53 R Vernouillet Centre d'affaires, 51100 Reims", "latitude": "49.2575", "longitude": "4.0175"},
    "402424": {"tac": 5101, "adresse": "60 R Geruzez, 51100 Reims", "latitude": "49.2636089", "longitude": "4.0141145"},
    "402174": {"tac": 5101, "adresse": "49 r Mont d'Arène, 51100 Reims", "latitude": "49.262284", "longitude": "4.022182"},
    "402599": {"tac": 5101, "adresse": "6 Rue du Champ de Mars, 51100 Reims", "latitude": "49.261616", "longitude": "4.032993"},
    "1894": {"tac": 5101, "adresse": "5 r Paul Fort 51100 Reims", "latitude": "49.25389", "longitude": "4.05667"}
}

# Initialisation des variables dans Streamlit
if "data" not in st.session_state:
    st.session_state["data"] = {
        "temps": [],
        "temps_lisible": [],
        "latitude": [],
        "longitude": [],
        "wifi_ssid": [],
        "signal_wifi": [],
        "upload_total_kb": [],
        "download_total_kb": [],
        "upload_vitesse_kb_s": [],
        "download_vitesse_kb_s": [],
        "upload_vitesse_moyenne_kb_s": [],
        "download_vitesse_moyenne_kb_s": []
    }

if "last_message" not in st.session_state:
    st.session_state["last_message"] = {}

def on_message(client, userdata, msg):
    try:
        raw_message = msg.payload.decode()
        print("Message brut reçu :", raw_message)
        message = json.loads(raw_message)
        if isinstance(message, str):
            print("JSON double encodé détecté, nouvelle conversion...")
            message = json.loads(message)
        print("Message JSON converti :", message)
        st.session_state["last_message"] = message

        if isinstance(message, dict):
            if "Temps" in message:
                st.session_state["data"]["temps"].append(message["Temps"])
            if "Temps Lisible" in message:
                st.session_state["data"]["temps_lisible"].append(message["Temps Lisible"])
            if "Latitude" in message:
                st.session_state["data"]["latitude"].append(message["Latitude"])
            if "Longitude" in message:
                st.session_state["data"]["longitude"].append(message["Longitude"])
            if "WiFi SSID" in message:
                st.session_state["data"]["wifi_ssid"].append(message["WiFi SSID"])
            if "Signal WiFi" in message:
                st.session_state["data"]["signal_wifi"].append(message["Signal WiFi"])
            if "Upload Total KB" in message:
                st.session_state["data"]["upload_total_kb"].append(message["Upload Total KB"])
            if "Download Total KB" in message:
                st.session_state["data"]["download_total_kb"].append(message["Download Total KB"])
            if "Upload Vitesse KB/s" in message:
                st.session_state["data"]["upload_vitesse_kb_s"].append(message["Upload Vitesse KB/s"])
            if "Download Vitesse KB/s" in message:
                st.session_state["data"]["download_vitesse_kb_s"].append(message["Download Vitesse KB/s"])
            if "Upload Vitesse Moyenne KB/s" in message:
                st.session_state["data"]["upload_vitesse_moyenne_kb_s"].append(message["Upload Vitesse Moyenne KB/s"])
            if "Download Vitesse Moyenne KB/s" in message:
                st.session_state["data"]["download_vitesse_moyenne_kb_s"].append(message["Download Vitesse Moyenne KB/s"])

            # Traitement des infos antenne
            if "Antenne 4G" in message:
                antenne_info = message["Antenne 4G"]
                parsed_antenne = parse_antenne_info(antenne_info)
                st.session_state["data"]["eNbID"].append(parsed_antenne["eNbID"])
                st.session_state["data"]["CellID"].append(parsed_antenne["CellID"])
                st.session_state["data"]["TAC"].append(parsed_antenne["TAC"])
                st.session_state["data"]["Signal"].append(parsed_antenne["Signal"])

            print("Données mises à jour :", st.session_state["data"])
    except json.JSONDecodeError as e:
        print(f"Erreur de décodage JSON : {e}")
    except Exception as e:
        print(f"Erreur lors du traitement du message MQTT : {e}")

def parse_antenne_info(antenne_str):
    match = re.search(r"eNbID=(\d+), CellID=(\d+), TAC=(\d+), Signal=(-?\d+) dBm", antenne_str)
    if match:
        return {
            "eNbID": int(match.group(1)),
            "CellID": int(match.group(2)),
            "TAC": int(match.group(3)),
            "Signal": int(match.group(4))
        }
    return {"eNbID": None, "CellID": None, "TAC": None, "Signal": None}

def mqtt_thread():
    client = mqtt.Client()
    client.on_message = on_message
    client.connect(BROKER, PORT, 60)
    client.subscribe(TOPIC)
    client.loop_forever()

def load_csv_data(file):
    try:
        df = pd.read_csv(file)

        # Vérification que "Antenne 4G" est bien présente
        if "Antenne 4G" not in df.columns:
            st.error("La colonne 'Antenne 4G' est manquante dans le fichier CSV.")
            return

        # Création des nouvelles colonnes à partir de "Antenne 4G"
        df["eNbID"] = None
        df["CellID"] = None
        df["TAC"] = None
        df["Signal"] = None

        for i, antenne_str in enumerate(df["Antenne 4G"]):
            parsed_antenne = parse_antenne_info(antenne_str)
            df.at[i, "eNbID"] = parsed_antenne["eNbID"]
            df.at[i, "CellID"] = parsed_antenne["CellID"]
            df.at[i, "TAC"] = parsed_antenne["TAC"]
            df.at[i, "Signal"] = parsed_antenne["Signal"]

        # Suppression de la colonne "Antenne 4G" si nécessaire
        df.drop(columns=["Antenne 4G"], inplace=True)

        # Stockage des données dans la session Streamlit
        st.session_state["data"]["temps"] = df["Temps"].tolist()
        st.session_state["data"]["temps_lisible"] = df["Temps Lisible"].tolist()
        st.session_state["data"]["latitude"] = df["Latitude"].tolist()
        st.session_state["data"]["longitude"] = df["Longitude"].tolist()
        st.session_state["data"]["wifi_ssid"] = df["WiFi SSID"].tolist()
        st.session_state["data"]["signal_wifi"] = df["Signal WiFi"].tolist()
        st.session_state["data"]["upload_total_kb"] = df["Upload Total KB"].tolist()
        st.session_state["data"]["download_total_kb"] = df["Download Total KB"].tolist()
        st.session_state["data"]["upload_vitesse_kb_s"] = df["Upload Vitesse KB/s"].tolist()
        st.session_state["data"]["download_vitesse_kb_s"] = df["Download Vitesse KB/s"].tolist()
        st.session_state["data"]["upload_vitesse_moyenne_kb_s"] = df["Upload Vitesse Moyenne KB/s"].tolist()
        st.session_state["data"]["download_vitesse_moyenne_kb_s"] = df["Download Vitesse Moyenne KB/s"].tolist()
        st.session_state["data"]["eNbID"] = df["eNbID"].tolist()
        st.session_state["data"]["CellID"] = df["CellID"].tolist()
        st.session_state["data"]["TAC"] = df["TAC"].tolist()
        st.session_state["data"]["Signal"] = df["Signal"].tolist()

        st.write("Aperçu des premières lignes du fichier chargé :")
        st.dataframe(df.head(5))
    except Exception as e:
        st.error(f"Erreur lors de la lecture du fichier CSV: {e}")

threading.Thread(target=mqtt_thread, daemon=True).start()
########################Interface Streamlit################################
st.title("Visualisation des données en temps réel")
st.subheader("Dernier message reçu :")
st.json(st.session_state["last_message"])

uploaded_file = st.file_uploader("Télécharger un fichier CSV", type=["csv"])
if uploaded_file is not None:
    try:
        load_csv_data(uploaded_file)
    except Exception as e:
        st.error(f"Erreur lors de la lecture du fichier CSV: {e}")
else:
    st.write("Veuillez télécharger un fichier CSV.")

st.subheader("Graphiques des données")
#Graphique pour les vitesses de téléchargement et d'upload
fig = go.Figure()
if st.session_state["data"]["download_vitesse_kb_s"]:
    fig.add_trace(go.Scatter(
        y=st.session_state["data"]["download_vitesse_kb_s"],
        mode="lines",
        name="Vitesse de téléchargement (KB/s)",
        line=dict(color='blue')
    ))
if st.session_state["data"]["upload_vitesse_kb_s"]:
    fig.add_trace(go.Scatter(
        y=st.session_state["data"]["upload_vitesse_kb_s"],
        mode="lines",
        name="Vitesse d'upload (KB/s)",
        line=dict(color='green')
    ))
st.plotly_chart(fig, use_container_width=True)

# Carte de localisation
st.subheader("Carte de localisation avec antennes 4G")

if st.session_state["data"]["latitude"] and st.session_state["data"]["longitude"]:
    # Création de la carte centrée sur la dernière position
    m = folium.Map(location=[st.session_state["data"]["latitude"][-1], st.session_state["data"]["longitude"][-1]], zoom_start=12)

    # Dictionnaire pour stocker les trajets par antenne
    antenne_trajets = {}
    dernier_enb = None  # Variable pour détecter les changements d'antenne

    for lat, lon, antenne in zip(st.session_state["data"]["latitude"],
                                 st.session_state["data"]["longitude"],
                                 st.session_state["data"]["eNbID"]):
        # Ajouter un marqueur pour chaque position GPS
        folium.CircleMarker(
            location=[lat, lon],
            radius=3,
            color="blue",
            fill=True,
            fill_color="blue",
            fill_opacity=0.6
        ).add_to(m)

        # Vérifier s'il y a un changement d'antenne
        if antenne != dernier_enb:
            folium.Marker(
                location=[lat, lon],
                popup=f"Changement d'antenne eNbID: {antenne}",
                icon=folium.Icon(color="red", icon="info-sign")  # Marqueur rouge pour le changement
            ).add_to(m)
            dernier_enb = antenne  # Mettre à jour l'antenne actuelle

        # Grouper les positions par antenne
        if antenne not in antenne_trajets:
            antenne_trajets[antenne] = []
        antenne_trajets[antenne].append([lat, lon])

    # Ajouter toutes les antennes du dictionnaire sur la carte
    for enb_id, info in antennes_reims.items():
        folium.Marker(
            location=[info["latitude"], info["longitude"]],
            popup=f"Antenne eNB: {enb_id}, TAC: {info['tac']}, Adresse: {info['adresse']}",
            icon=folium.Icon(color="green", icon="tower")  # Vert pour différencier des positions mobiles
        ).add_to(m)

    # Afficher la carte
    folium_static(m)

else:
    st.write("Aucune position GPS reçue pour le moment.")
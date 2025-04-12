import folium
import json
import pandas as pd
import numpy as np
import paho.mqtt.client as mqtt
import plotly.express as px
import plotly.graph_objects as go
import re
import requests
import streamlit as st
import threading
import time
import pandas as pd
from io import StringIO
from streamlit_folium import folium_static
from scipy.spatial import distance
from collections import defaultdict

#Configuration MQTT
BROKER = "194.57.103.203"
PORT = 1883
TOPIC = "antenne"

antennes_reims = {
    "402129": {"tac": 5102, "adresse": "15 Rue de l'Escaut, 51100 Reims", "latitude": "49.247917", "longitude": "4.067603"},
    "401892": {"tac": 5101, "adresse": "23 Bd Pasteur, 51100 Reims", "latitude": "49.249539", "longitude": "4.043129"},
    "2523": {"tac": -1, "adresse": "5 R des Moulins, 51100 Reims", "latitude": "49.246018", "longitude": "4.037953"},
    "402522": {"tac": 5102, "adresse": "2 All du Bellay, 51100 Reims", "latitude": "49.238848", "longitude": "4.041301"},
    "403850": {"tac": 5102, "adresse": "36 rue Maison Blanche, 51100 Reims", "latitude": "49.237869", "longitude": "4.028901"},
    "2110": {"tac": 5101, "adresse": "5 BD Franchet d'Esperey Tour Franchet, 51100 Reims", "latitude": "49.24194", "longitude": "4.01667"},
    "402111": {"tac": 5101, "adresse": "18 R des Bons Malades, 51100 Reims", "latitude": "49.249639", "longitude": "4.015367"},
    "22729": {"tac": 5101, "adresse": "31, r Paul Doumer Hôtel Mercure, 51100 Reims", "latitude": "49.242622", "longitude": "4.027535"},
    "408493": {"tac": 5101, "adresse": "15 Rue Jadart, 51100 Reims", "latitude": "49.25278", "longitude": "4.02944"},
    "408045": {"tac": 5101, "adresse": "28 r Buirette parc auto Buirette, 51100 Reims", "latitude": "49.2558881", "longitude": "4.0229961"},
    "402392": {"tac": 5101, "adresse": "1 r de l'Arbalète, 51100 Reims", "latitude": "49.25643", "longitude": "4.03225"},
    "402175": {"tac": 5101, "adresse": "53 R Vernouillet Centre d'affaires, 51100 Reims", "latitude": "49.2575", "longitude": "4.0175"},
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
        "download_vitesse_moyenne_kb_s": [],
        "eNbID": [],
        "CellID": [],
        "TAC": [],
        "Signal": []
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

        #Création des nouvelles colonnes à partir de "Antenne 4G"
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

        #Suppression de la colonne "Antenne 4G" si nécessaire
        df.drop(columns=["Antenne 4G"], inplace=True)

        #Stockage des données dans la session Streamlit
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

def normaliser_donnees(df, colonnes):
    return (df[colonnes] - df[colonnes].min()) / (df[colonnes].max() - df[colonnes].min())

def distance_minkowski(x, y, m=2):
    return distance.minkowski(x, y, m)

#Implémentation de l'algorithme k-Iterative Neighbors (kIN)
def kIN_classification(df, point_cible, k=5, m=2):
    df_temp = df.copy()
    nb_features = df_temp.shape[1] - 1
    if len(point_cible) != nb_features:
        raise ValueError(f"Le point cible a {len(point_cible)} dimensions, mais doit en avoir {nb_features}")

    #Calcul des distances avec vérification
    def safe_distance(row):
        x = row[:-1].values  # Convertir en array
        if len(x) != len(point_cible):
            raise ValueError(f"Dimension mismatch: row={len(x)}, point_cible={len(point_cible)}")
        return distance.minkowski(x, point_cible, m)
    df_temp['distance'] = df_temp.apply(safe_distance, axis=1)

    #Sélection des k plus proches voisins
    df_temp = df_temp.sort_values(by='distance')
    voisins_proches = df_temp.iloc[:k]

    #Retourne la classe majoritaire parmi les k voisins
    classe_predite = voisins_proches.iloc[:, -2].mode()[0]
    return classe_predite

threading.Thread(target=mqtt_thread, daemon=True).start()
########################Interface Streamlit################################
page = st.sidebar.radio("Choisissez une page", ["Accueil", "Classification kIN"])
if page == "Accueil":
    st.title("Dashboard des Antennes 4G")
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

    #Graphique pour les vitesses de téléchargement et d'upload
    if st.session_state["data"]["Signal"]:
        st.subheader("Graphiques des données")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            y=st.session_state["data"]["download_vitesse_kb_s"],
            mode="lines",
            name="Vitesse de téléchargement (KB/s)",
            line=dict(color='blue')
        ))
        fig.add_trace(go.Scatter(
            y=st.session_state["data"]["upload_vitesse_kb_s"],
            mode="lines",
            name="Vitesse d'upload (KB/s)",
            line=dict(color='green')
        ))
        st.plotly_chart(fig, use_container_width=True)

        # Graphique de l'évolution du signal 4G
        st.subheader("Évolution du Signal 4G dans le Temps")
        changement_antenne = [True] + [(st.session_state["data"]["eNbID"][i] != st.session_state["data"]["eNbID"][i - 1]) for i in range(1, len(st.session_state["data"]["eNbID"]))]
        fig_signal = px.line(
            x=st.session_state["data"]["temps_lisible"],
            y=st.session_state["data"]["Signal"],
            title="Évolution du Signal 4G",
            labels={"Signal": "Puissance du Signal 4G (dBm)", "Temps Lisible": "Temps"},
            line_shape="linear",
            hover_data={"Latitude": st.session_state["data"]["latitude"], "Longitude": st.session_state["data"]["longitude"]}
        )
        fig_signal.add_scatter(
            x=[st.session_state["data"]["temps_lisible"][i] for i in range(len(st.session_state["data"]["temps_lisible"])) if changement_antenne[i]],
            y=[st.session_state["data"]["Signal"][i] for i in range(len(st.session_state["data"]["Signal"])) if changement_antenne[i]],
            mode="markers",
            marker=dict(color="red", size=8),
            name="Changement d'Antenne",
            hovertemplate="<b>Changement d'Antenne</b><br>Latitude: %{customdata[0]}<br>Longitude: %{customdata[1]}<br>eNbID: %{customdata[2]}<extra></extra>",
            customdata=[
                (st.session_state["data"]["latitude"][i], st.session_state["data"]["longitude"][i], st.session_state["data"]["eNbID"][i])
                for i in range(len(st.session_state["data"]["temps_lisible"])) if changement_antenne[i]
            ]
        )
        st.plotly_chart(fig_signal)

        st.subheader("Distribution des puissances du signal 4G")
        fig_hist = px.histogram(
            st.session_state["data"],
            x="Signal",
            nbins=30,
            title="Histogramme de la puissance du signal",
            labels={"Signal": "Puissance (dBm)"},
            color_discrete_sequence=["#00CC96"]
        )
        st.plotly_chart(fig_hist, use_container_width=True)

        st.subheader("Temps passé par antenne")
        data = pd.DataFrame(st.session_state["data"])
        data["temps_lisible"] = pd.to_datetime(data["temps_lisible"])
        duree_par_antenne = defaultdict(int)
        grouped = data.groupby((data["eNbID"] != data["eNbID"].shift()).cumsum())
        for _, groupe in grouped:
            antenne = groupe["eNbID"].iloc[0]
            if len(groupe) > 1:
                duree = (groupe["temps_lisible"].iloc[-1] - groupe["temps_lisible"].iloc[0]).total_seconds() / 60
                duree_par_antenne[antenne] += duree
        df_duree = pd.DataFrame(list(duree_par_antenne.items()), columns=["eNbID", "Durée (min)"]).sort_values(by="Durée (min)", ascending=False)
        st.bar_chart(df_duree.set_index("eNbID"))

        #Carte de localisation
        st.subheader("Carte de localisation avec antennes 4G")
        m = folium.Map(location=[st.session_state["data"]["latitude"][-1], st.session_state["data"]["longitude"][-1]], zoom_start=12)
        antenne_trajets = {}
        dernier_enb = None
        for lat, lon, antenne in zip(st.session_state["data"]["latitude"], st.session_state["data"]["longitude"], st.session_state["data"]["eNbID"]):
            #Ajoute un marqueur pour chaque position GPS
            folium.CircleMarker(
                location=[lat, lon],
                radius=3,
                color="blue",
                fill=True,
                fill_color="blue",
                fill_opacity=0.6
            ).add_to(m)

            #Vérifie s'il y a un changement d'antenne
            if antenne != dernier_enb:
                folium.Marker(
                    location=[lat, lon],
                    popup=f"Changement d'antenne eNbID: {antenne}",
                    icon=folium.Icon(color="red", icon="info-sign")
                ).add_to(m)
                for enb_id, info in antennes_reims.items():
                    enb_id = int(enb_id)
                    print(f"ID de l'antenne du dico : {enb_id} (type: {type(enb_id)})")
                    print(f"ID de l'antenne du marqueur : {antenne} (type: {type(antenne)})")
                    if enb_id == antenne:
                        print("Validé")
                        folium.PolyLine(
                            locations=[[lat, lon], [info["latitude"], info["longitude"]]],
                            color="purple",
                            weight=3,
                            opacity=0.7,
                            dash_array="5,5"
                        ).add_to(m)
                dernier_enb = antenne

            #Groupe les positions par antenne
            if antenne not in antenne_trajets:
                antenne_trajets[antenne] = []
            antenne_trajets[antenne].append([lat, lon])

        #Ajoute toutes les antennes du dictionnaire sur la carte
        for enb_id, info in antennes_reims.items():
            folium.Marker(
                location=[info["latitude"], info["longitude"]],
                popup=f"Antenne eNB: {enb_id}, TAC: {info['tac']}, Adresse: {info['adresse']}",
                icon=folium.Icon(color="green", icon="tower")
            ).add_to(m)
        folium_static(m)
    else:
        st.write("Aucune position GPS reçue pour le moment.")

elif page == "Classification kIN":
    st.title("Classification des antennes par kIN")
    uploaded_file = st.file_uploader("Télécharger un fichier CSV", type=["csv"])
    if uploaded_file is not None:
        try:
            load_csv_data(uploaded_file)
        except Exception as e:
            st.error(f"Erreur lors de la lecture du fichier CSV: {e}")
    else:
        st.write("Veuillez télécharger un fichier CSV.")
    st.subheader("Graphiques des données")
    antenne_trajets = {}
    dernier_enb = None
    if not st.session_state["data"]["Signal"]:
        st.write("Aucune donnée disponible. Veuillez charger un fichier CSV")
    else:
        df = pd.DataFrame({
            "Latitude": st.session_state["data"]["latitude"],
            "Longitude": st.session_state["data"]["longitude"],
            "Signal": st.session_state["data"]["Signal"]
        })
        df = df.dropna(subset=["Signal"])
        if df.empty:
            st.write("Les données de signal sont vides après suppression des valeurs NaN.")
        else:
            #Création des classes de signal
            df["Classe_Signal"] = pd.cut(df["Signal"], bins=3, labels=[0, 1, 2])

            #Sélection d'un point aléatoire à classifier
            index_aleatoire = np.random.randint(0, len(df))
            point_cible = df.iloc[index_aleatoire][["Signal", "Latitude", "Longitude"]].values

            # Classification avec kIN
            classe_predite = kIN_classification(df, point_cible)
            st.write(f"Point à classifier : Signal = {point_cible[0]} dBm")
            st.write(f"Classe prédite : {classe_predite}")

            #Affichage de la carte
            st.subheader("Carte des antennes classées")
            m = folium.Map(location=[df["Latitude"].mean(), df["Longitude"].mean()], zoom_start=12)
            couleurs = {0: "red", 1: "orange", 2: "green"}
            for _, row in df.iterrows():
                folium.CircleMarker(
                    location=[row["Latitude"], row["Longitude"]],
                    radius=5,
                    color=couleurs[row["Classe_Signal"]],
                    fill=True,
                    fill_color=couleurs[row["Classe_Signal"]],
                    fill_opacity=0.6,
                    popup=f"Signal: {row['Signal']} dBm"
                ).add_to(m)
            for lat, lon, antenne in zip(st.session_state["data"]["latitude"],
                                         st.session_state["data"]["longitude"],
                                         st.session_state["data"]["eNbID"]):
                #Vérifie s'il y a un changement d'antenne
                if antenne != dernier_enb:
                    folium.Marker(
                        location=[lat, lon],
                        popup=f"Changement d'antenne eNbID: {antenne}",
                        icon=folium.Icon(color="red", icon="info-sign")
                    ).add_to(m)
                    for enb_id, info in antennes_reims.items():
                        enb_id = int(enb_id)
                        print(f"ID de l'antenne du dico : {enb_id} (type: {type(enb_id)})")
                        print(f"ID de l'antenne du marqueur : {antenne} (type: {type(antenne)})")
                        if enb_id == antenne:
                            print("Validé")
                            folium.PolyLine(
                                locations=[[lat, lon], [info["latitude"], info["longitude"]]],
                                color="purple",
                                weight=3,
                                opacity=0.7,
                                dash_array="5,5"
                            ).add_to(m)
                    dernier_enb = antenne

            #Groupe les positions par antenne
            if antenne not in antenne_trajets:
                antenne_trajets[antenne] = []
            antenne_trajets[antenne].append([lat, lon])
            for enb_id, info in antennes_reims.items():
                folium.Marker(
                    location=[info["latitude"], info["longitude"]],
                    popup=f"Antenne eNB: {enb_id}, TAC: {info['tac']}, Adresse: {info['adresse']}",
                    icon=folium.Icon(color="green", icon="tower")  # Vert pour différencier des positions mobiles
                ).add_to(m)
            folium_static(m)
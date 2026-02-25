import streamlit as st
import yfinance as yf
import requests
import pandas as pd
from datetime import datetime
import xml.etree.ElementTree as ET
import plotly.graph_objects as go





# Fonct de départs



def trouver_ticker(recherche: str) -> str:
    url = "https://query2.finance.yahoo.com/v1/finance/search"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        reponse = requests.get(url, headers=headers, params={'q': recherche}, timeout=5)
        data = reponse.json()
        if 'quotes' in data and data['quotes']:
            return data['quotes'][0]['symbol']
    except Exception:
        return None
    return None

def recuperer_actualites(ticker: str) -> list:
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        reponse = requests.get(url, headers=headers, timeout=5)
        root = ET.fromstring(reponse.content)
        articles = []
        
        for item in root.findall('.//item')[:5]:
            titre = item.find('title').text if item.find('title') is not None else "Titre indisponible"
            lien = item.find('link').text if item.find('link') is not None else "#"
            
            description_brute = item.find('description').text if item.find('description') is not None else ""
            resume = description_brute.split('<')[0] if description_brute else ""
            
            date_brute = item.find('pubDate').text if item.find('pubDate') is not None else ""
            date_propre = date_brute.replace(" +0000", "") if date_brute else "Date inconnue"
            
            articles.append({
                'title': titre, 
                'link': lien, 
                'summary': resume, 
                'pubDate': date_propre
            })
        return articles
    except Exception:
        return []

def calculer_tendance(historique: pd.DataFrame, jours_ouvres: int) -> float:
    if len(historique) > jours_ouvres:
        prix_actuel = historique['Close'].iloc[-1]
        prix_ancien = historique['Close'].iloc[-jours_ouvres]
        return ((prix_actuel - prix_ancien) / prix_ancien) * 100
    return None

def formater_metrique(valeur, format_str="{:.2f}", suffixe="") -> str:
    if valeur is None or str(valeur).lower() == 'nan':
        return "N/A"
    return f"{format_str.format(valeur)} {suffixe}".strip()

def formater_capitalisation(nombre: float) -> str:
    if nombre is None or nombre == 0:
        return "N/A"
    if nombre >= 1_000_000_000_000:
        return f"{nombre / 1_000_000_000_000:.2f} T"
    elif nombre >= 1_000_000_000:
        return f"{nombre / 1_000_000_000:.2f} B"
    elif nombre >= 1_000_000:
        return f"{nombre / 1_000_000:.2f} M"
    return f"{nombre:,}"

def recuperer_valeur_marche(ticker: str) -> float:
    try:
        actif = yf.Ticker(ticker)
        data = actif.history(period="1d")
        if not data.empty:
            return data['Close'].iloc[-1]
    except Exception:
        return None
    return None

# CONFIGUE INTERFACE

st.set_page_config(page_title="Dashboard Bourse Pro", layout="wide", page_icon="📈")

# BARRE MACROÉCONOMIE 
with st.sidebar:
    st.header("🌍 Vue Macroéconomique")
    
    st.subheader("🏦 Taux Obligataires (10Y)")
    us_10y = recuperer_valeur_marche("^TNX")
    st.metric(label="🇺🇸 US Treasury", value=formater_metrique(us_10y, "{:.3f}", "%"))
    
    st.metric(label="🇫🇷 OAT France", value="2.85 %", help="Valeur indicative (Limitation API)")
    st.metric(label="🇩🇪 Bund Allemagne", value="2.35 %", help="Valeur indicative (Limitation API)")
    
    st.divider()
    
    st.subheader("💱 Forex (Base EUR)")
    paires = {
        "EUR / USD": "EURUSD=X",
        "EUR / GBP": "EURGBP=X",
        "EUR / CHF": "EURCHF=X",
        "EUR / JPY": "EURJPY=X"
    }
    for nom_paire, ticker_paire in paires.items():
        taux = recuperer_valeur_marche(ticker_paire)
        if taux:
            st.metric(label=nom_paire, value=formater_metrique(taux, "{:.4f}"))

# DASHBOARD 


st.title("📊 ANALYSE D'ENTREPRISE 📊")

saisie_utilisateur = st.text_input("Recherche d'actif (Nom de l'entreprise ou Ticker) :", "BNP Paribas")

if saisie_utilisateur:
    ticker_symbol = trouver_ticker(saisie_utilisateur)
    
    if ticker_symbol:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info
        
        # EN-TÊTE 
        col_header, col_price = st.columns([3, 1])
        
        with col_header:
            st.header(info.get('shortName', ticker_symbol))
            st.caption(f"📍 {info.get('city', 'N/A')}, {info.get('country', 'N/A')} | 🏢 Secteur : {info.get('sector', 'N/A')}")
            desc = info.get('longBusinessSummary', '')
            st.write('. '.join(desc.split('. ')[:2]) + '.' if desc else "Description non disponible.")
            
        with col_price:
            prix = info.get('currentPrice')
            devise = info.get('currency', '')
            st.metric(label="Dernier Cours", value=formater_metrique(prix, "{:.2f}", devise))
        
        st.divider()
        
        # ANALYSE 
        tab1, tab2, tab3, tab4 = st.tabs(["📈 Dynamique des Prix", "🔎 Analyse Fondamentale", "📅 Historique (Earnings & Div)", "📰 Actualités"])        
        # GRAPH
        with tab1:
            historique = stock.history(period="1y")
            if not historique.empty:
                c1, c2, c3, c4 = st.columns(4)
                
                perf_1m = calculer_tendance(historique, 21)
                perf_3m = calculer_tendance(historique, 63)
                perf_6m = calculer_tendance(historique, 126)
                perf_1y = calculer_tendance(historique, 252)
                
                c1.metric("Performance (1 Mois)", formater_metrique(perf_1m, "{:+.2f}", "%"))
                c2.metric("Performance (3 Mois)", formater_metrique(perf_3m, "{:+.2f}", "%"))
                c3.metric("Performance (6 Mois)", formater_metrique(perf_6m, "{:+.2f}", "%"))
                c4.metric("Performance (1 An)", formater_metrique(perf_1y, "{:+.2f}", "%"))
                
                st.line_chart(historique['Close'], use_container_width=True)
            else:
                st.warning("Données historiques non disponibles.")
        
        # HISTORIQUE 
        with tab3:
            col_gauche, col_droite = st.columns(2)
            
            with col_gauche:
                st.markdown("### 💰 Historique des Dividendes")
                historique_div = stock.dividends
                if not historique_div.empty:
                    derniers_div = historique_div.tail(10).sort_index(ascending=False)
                    derniers_div.index = derniers_div.index.strftime('%d/%m/%Y')
                    st.dataframe(derniers_div, use_container_width=True)
                else:
                    st.info("Cette entreprise ne verse pas de dividendes.")
                    
            with col_droite:
                st.markdown("### 📊 Historique des Bénéfices")
                compte_resultat = stock.income_stmt
                if not compte_resultat.empty:
                    donnees_fin = compte_resultat.T
                    
                    if 'Total Revenue' in donnees_fin.columns and 'Net Income' in donnees_fin.columns:
                        graph_data = donnees_fin[['Total Revenue', 'Net Income']].sort_index()
                        annees = graph_data.index.year.astype(str)
                        
                        # graphique 
                        fig = go.Figure()
                        
                        # Barre du Chiffre d'Affaires 
                        fig.add_trace(go.Bar(
                            x=annees, 
                            y=graph_data['Total Revenue'], 
                            name="Chiffre d'Affaires", 
                            marker_color='#8ab4f8'
                        ))
                        
                        # Barre du Résultat 
                        fig.add_trace(go.Bar(
                            x=annees, 
                            y=graph_data['Net Income'], 
                            name="Résultat Net", 
                            marker_color='#1967d2'
                        ))
                        
                        # Mise en page 
                        fig.update_layout(
                            barmode='group', 
                            margin=dict(l=0, r=0, t=10, b=0),
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                            plot_bgcolor='rgba(0,0,0,0)',
                            yaxis=dict(showgrid=True, gridcolor='lightgrey')
                        )
                        
                        # Affichage 
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("Données insuffisantes pour le graphique.")
                else:
                    st.info("Aucun compte de résultat disponible.")

        # RATIO
        with tab2:
            st.markdown("### Métriques de Valorisation et Structure")
            r1, r2, r3, r4 = st.columns(4)
            
            # Valo
            r1.metric("Capitalisation", formater_capitalisation(info.get('marketCap')))
            r1.metric("P/E Ratio (Trailing)", formater_metrique(info.get('trailingPE')))
            r1.metric("EV / EBITDA", formater_metrique(info.get('enterpriseToEbitda')))
            
            # Renta
            r2.metric("Marge Nette", formater_metrique(info.get('profitMargins') * 100 if info.get('profitMargins') else None, "{:.2f}", "%"))
            r2.metric("ROE ", formater_metrique(info.get('returnOnEquity') * 100 if info.get('returnOnEquity') else None, "{:.2f}", "%"))
            r2.metric("ROA ", formater_metrique(info.get('returnOnAssets') * 100 if info.get('returnOnAssets') else None, "{:.2f}", "%"))
            
            # Risque
            r3.metric("Bêta (1Y)", formater_metrique(info.get('beta')))
            r3.metric("Debt to Equity", formater_metrique(info.get('debtToEquity'), "{:.2f}", " %"))
            r3.metric("Current Ratio", formater_metrique(info.get('currentRatio')))
            
            # Divid
            div_rate = info.get('dividendRate')
            if div_rate and prix:
                rendement_div = (div_rate / prix) * 100
            else:
                rendement_div = None
                
            r4.metric("Rendement du Dividende", formater_metrique(rendement_div, "{:.2f}", "%"))
            r4.metric("Price to Book (P/B)", formater_metrique(info.get('priceToBook')))
            
            date_div_brute = info.get('exDividendDate')
            if date_div_brute:
                date_div_formatee = datetime.fromtimestamp(date_div_brute).strftime('%d/%m/%Y')
            else:
                date_div_formatee = "N/A"
            r4.metric("Dernier Div. Date", date_div_formatee) 

        # ACTU
        with tab4:
            st.markdown("### Flux d'Information en Continu")
            news = recuperer_actualites(ticker_symbol)
            if news:
                for article in news:
                    st.markdown(f"**[{article['title']}]({article['link']})**")
                    st.caption(f"🕒 {article['pubDate']}")
                    
                    if article['summary']:
                        st.write(f"*{article['summary']}*")
                        
                    st.write("---")
            else:
                st.info("Aucune actualité récente trouvée pour cette entreprise.")
                
    else:
        st.error("❌ Ticker introuvable. Veuillez vérifier l'orthographe ou utiliser directement le Ticker officiel.")

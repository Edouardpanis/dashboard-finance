import streamlit as st
import yfinance as yf
import requests

def trouver_ticker(recherche):
    """Trouve le Ticker"""
    url = "https://query2.finance.yahoo.com/v1/finance/search"
    headers = {'User-Agent': 'Mozilla/5.0'} 
    parametres = {'q': recherche} 
    
    try:
        reponse = requests.get(url, headers=headers, params=parametres)
        data = reponse.json()
        if 'quotes' in data and len(data['quotes']) > 0:
            return data['quotes'][0]['symbol']
    except Exception:
        return None
    return None

def calculer_tendance(historique, jours_ouvres):
    """Calcule la variation en pourcentage sur un nombre de jours de cotation."""
    if len(historique) > jours_ouvres:
        prix_actuel = historique['Close'].iloc[-1]
        prix_ancien = historique['Close'].iloc[-jours_ouvres]
        return ((prix_actuel - prix_ancien) / prix_ancien) * 100
    return None

def formater_grands_nombres(nombre):
    """Transforme les grands nombres en format lisible (Milliards/Millions)."""
    if nombre is None or nombre == 0:
        return "N/A"
    if nombre >= 1_000_000_000_000:
        return f"{nombre / 1_000_000_000_000:.2f} T"
    elif nombre >= 1_000_000_000:
        return f"{nombre / 1_000_000_000:.2f} B"
    elif nombre >= 1_000_000:
        return f"{nombre / 1_000_000:.2f} M"
    return f"{nombre:,}"

def recuperer_prix_direct(ticker):
    """Récupère rapidement le dernier prix d'un actif (pour les taux/forex)."""
    try:
        actif = yf.Ticker(ticker)
        prix = actif.history(period="1d")['Close'].iloc[-1]
        return prix
    except:
        return None

st.set_page_config(page_title="Dashboard Bourse", layout="wide")

# --- Barre latérale Macro dynamique ---
with st.sidebar:
    st.header("🌍 Macroéconomie")
    
    st.subheader("🏦 Taux Directeurs & Obligataires")
    us_10y = recuperer_prix_direct("^TNX")
    if us_10y:
        st.metric(label="🇺🇸 US 10 Years", value=f"{us_10y:.3f} %")
    
    st.metric(label="🇫🇷 OAT France (10 ans)", value="2.85 %")
    st.metric(label="🇩🇪 Bund Allemagne (10 ans)", value="2.35 %")
    
    st.divider()
    
    st.subheader("💱 Taux de Change")
    eur_usd = recuperer_prix_direct("EURUSD=X")
    gbp_usd = recuperer_prix_direct("GBPUSD=X")
    usd_jpy = recuperer_prix_direct("JPY=X")
    
    if eur_usd: st.metric(label="EUR / USD", value=f"{eur_usd:.4f}")
    if gbp_usd: st.metric(label="GBP / USD", value=f"{gbp_usd:.4f}")
    if usd_jpy: st.metric(label="USD / JPY", value=f"{usd_jpy:.2f}")


st.title("📊 ANALYSE D'ENTREPRISE 📊")

saisie_utilisateur = st.text_input("Entrez un nom d'entreprise ou un Ticker", "BNP")

if saisie_utilisateur:
    ticker_symbol = trouver_ticker(saisie_utilisateur)
    
    if ticker_symbol:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info
        
        nom_entreprise = info.get('shortName', ticker_symbol)
        ville = info.get('city', 'Ville inconnue')
        pays = info.get('country', 'Pays inconnu')
        
        st.subheader(nom_entreprise)
        st.caption(f"📍 Siège social : {ville}, {pays}")
        
        description_complete = info.get('longBusinessSummary', 'Description non disponible.')
        phrases = description_complete.split('. ')
        description_courte = '. '.join(phrases[:2]) + '.' if len(phrases) > 1 else description_complete
        st.info(description_courte)
        
        # --- CORRECTION 1 : Largeur des colonnes ---
        # On donne 1.5x plus de place à la colonne Secteur pour éviter que le texte soit coupé
        col1, col2, col3, col4 = st.columns([1, 1.5, 1, 0.8])
        
        prix_actuel = info.get('currentPrice', 0)
        devise = info.get('currency', '')
        
        col1.metric("Prix Actuel", f"{prix_actuel} {devise}")
        col2.metric("Secteur", info.get('sector', 'N/A'))
        
        cap_formatee = formater_grands_nombres(info.get('marketCap'))
        col3.metric("Capitalisation", f"{cap_formatee} {devise}")
        
        pe_ratio = info.get('trailingPE')
        pe_affiche = f"{pe_ratio:.2f}" if pe_ratio is not None else "N/A"
        col4.metric("P/E Ratio", pe_affiche)
            
        st.divider()
        
        st.subheader("📈 Dynamique et historique du cours")
        historique = stock.history(period="1y")
        
        if not historique.empty:
            tendance_1m = calculer_tendance(historique, 21)
            tendance_3m = calculer_tendance(historique, 63)
            tendance_6m = calculer_tendance(historique, 126)
            tendance_1an = calculer_tendance(historique, 252)
            
            c1, c2, c3, c4 = st.columns(4)
            
            # --- CORRECTION 2 : Affichage pur de la performance ---
            def afficher_metrique(col, label, valeur):
                if valeur is not None:
                    # Le format :+.2f force l'affichage du signe + pour les nombres positifs
                    col.metric(label, value=f"{valeur:+.2f} %")
                else:
                    col.metric(label, "N/A")

            afficher_metrique(c1, "Performance 1 Mois", tendance_1m)
            afficher_metrique(c2, "Performance 3 Mois", tendance_3m)
            afficher_metrique(c3, "Performance 6 Mois", tendance_6m)
            afficher_metrique(c4, "Performance 1 An", tendance_1an)

            st.line_chart(historique['Close'])
        else:
            st.warning("Données historiques non disponibles pour ce Ticker.")
            
    else:
        st.error("❌ Impossible de trouver un Ticker correspondant. Essayez d'être plus précis.")


from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import yfinance as yf
import pandas as pd
import numpy as np

app = FastAPI()

# Universo inicial de ativos (Blue Chips e Mid Caps líquidas)
TICKERS = [
    'VALE3.SA', 'PETR4.SA', 'ITUB4.SA', 'BBAS3.SA', 'WEGE3.SA', 
    'PRIO3.SA', 'CMIG4.SA', 'CPLE6.SA', 'GGBR4.SA', 'JBSS3.SA', 
    'SUZB3.SA', 'VIVT3.SA', 'RENT3.SA', 'EGIE3.SA', 'TIMS3.SA', 
    'CSAN3.SA', 'B3SA3.SA', 'BBSE3.SA', 'ELET3.SA', 'ABEV3.SA'
]

def check_fundamentals(ticker_symbol):
    """
    CAMADA 1: Filtro de Qualidade (O Bouncer).
    Retorna True se a empresa for lucrativa, False caso contrário.
    """
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info
        
        # Puxa o Preço/Lucro (P/L) e o Retorno sobre Patrimônio (ROE)
        pe_ratio = info.get('trailingPE', 0)
        roe = info.get('returnOnEquity', 0)
        
        # Regra de Ouro: P/L deve ser positivo (empresa dá lucro) e menor que 30 (não está absurdamente cara)
        # ROE deve ser positivo.
        if pe_ratio is not None and roe is not None:
            if 0 < pe_ratio < 30 and roe > 0:
                return True
        return False
    except Exception:
        # Se a API falhar ou faltar dados, bloqueia a ação por segurança
        return False

def run_deep_research():
    """
    CAMADA 2: Análise Quantitativa (Risco x Retorno) apenas nas aprovadas.
    """
    try:
        print("Iniciando Filtro de Qualidade...")
        approved_tickers = []
        
        # Passa cada ticker pelo filtro de fundamentos
        for ticker in TICKERS:
            if check_fundamentals(ticker):
                approved_tickers.append(ticker)
                
        if not approved_tickers:
            return [] # Fallback se tudo falhar
            
        print(f"Ações aprovadas na Camada 1: {len(approved_tickers)}")
        
        # Baixa dados históricos apenas das empresas saudáveis
        df = yf.download(approved_tickers, period="6mo", progress=False)['Close']
        
        results = []
        for ticker in approved_tickers:
            try:
                start_price = float(df[ticker].iloc[0])
                end_price = float(df[ticker].iloc[-1])
                momentum = (end_price / start_price) - 1
                
                daily_pct = df[ticker].pct_change()
                volatility = float(daily_pct.std() * np.sqrt(252))
                
                score = momentum / volatility if volatility > 0 else 0
                
                results.append({
                    "ticker": ticker,
                    "price": round(end_price, 2),
                    "momentum": round(momentum * 100, 2),
                    "volatility": round(volatility * 100, 2),
                    "score": round(score, 2)
                })
            except Exception:
                continue
                
        ranking = pd.DataFrame(results).sort_values(by="score", ascending=False)
        return ranking.head(4).to_dict(orient="records")
        
    except Exception as e:
        print(f"Erro na análise: {e}")
        return []

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    top_4 = run_deep_research()
    budget_per_stock = 2500
    
    html_content = f"""
    <html>
        <head>
            <title>Sistema Alpha 20% (Blindado)</title>
            <style>
                body {{ font-family: Arial, sans-serif; background: #121212; color: #e0e0e0; padding: 20px; }}
                .card {{ background: #1e1e1e; padding: 20px; margin: 10px 0; border-radius: 8px; border-left: 5px solid #00ff88; }}
                h1 {{ color: #00ff88; }}
                .price {{ color: #00ff88; font-weight: bold; font-size: 1.2em; }}
                .tag {{ background: #333; padding: 5px 10px; border-radius: 4px; font-size: 0.9em; }}
            </style>
        </head>
        <body>
            <h1>🛡️ Deep Research: Carteira Alpha Blindada</h1>
            <p>Filtro de Qualidade (Lucro/ROE) + Algoritmo de Tendência (Sharpe)</p>
            <hr>
            
            {''.join([f'''
            <div class="card">
                <h2>{stock['ticker'].replace('.SA', '')}</h2>
                <p>Cotação: <span class="price">R$ {stock['price']}</span></p>
                <p>
                    <span class="tag">Alta 6m: {stock['momentum']}%</span> 
                    <span class="tag">Risco: {stock['volatility']}%</span>
                </p>
                <p>🎯 <strong>Comprar:</strong> {int(budget_per_stock / stock['price'])} ações (Mercado Fracionário: {stock['ticker'].replace('.SA', 'F')})</p>
            </div>
            ''' for stock in top_4])}
            
            <br>
            <p style="color: #666;"><em>O filtro fundamentalista descarta empresas com prejuízo ou dados ausentes antes de calcular a tendência.</em></p>
        </body>
    </html>
    """
    return html_content

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import yfinance as yf
import pandas as pd
import numpy as np

app = FastAPI()

# --- CONFIGURAÇÃO DA ESTRATÉGIA ---
# Universo de ativos: Foco em liquidez e qualidade para reduzir risco de mico
TICKERS = [
    'VALE3.SA', 'PETR4.SA', 'ITUB4.SA', 'BBAS3.SA', 'WEGE3.SA', 
    'PRIO3.SA', 'CMIG4.SA', 'CPLE6.SA', 'GGBR4.SA', 'JBSS3.SA', 
    'SUZB3.SA', 'VIVT3.SA', 'RENT3.SA', 'EGIE3.SA', 'TIMS3.SA', 
    'CSAN3.SA', 'B3SA3.SA', 'BBSE3.SA', 'ELET3.SA', 'ABEV3.SA'
]

def run_deep_research():
    """
    Executa a análise quantitativa em tempo real.
    Critério: Momentum (Alta em 6m) ajustado pela Volatilidade.
    """
    try:
        # Baixa dados dos últimos 6 meses
        df = yf.download(TICKERS, period="6mo", progress=False)['Close']
        
        results = []
        for ticker in TICKERS:
            try:
                # 1. Retorno Acumulado (Momentum)
                start_price = df[ticker].iloc[0]
                end_price = df[ticker].iloc[-1]
                momentum = (end_price / start_price) - 1
                
                # 2. Volatilidade (Risco)
                daily_pct = df[ticker].pct_change()
                volatility = daily_pct.std() * np.sqrt(252) # Anualizada
                
                # 3. Score (Sharpe Simplificado: Retorno / Risco)
                score = momentum / volatility if volatility > 0 else 0
                
                results.append({
                    "ticker": ticker,
                    "price": round(float(end_price), 2),
                    "momentum": round(momentum * 100, 2),
                    "volatility": round(volatility * 100, 2),
                    "score": round(score, 2)
                })
            except Exception:
                continue
                
        # Cria DataFrame e ordena pelo Score (Melhor retorno ajustado ao risco)
        ranking = pd.DataFrame(results).sort_values(by="score", ascending=False)
        
        # Seleciona o Top 4 para o aporte
        top_picks = ranking.head(4).to_dict(orient="records")
        return top_picks
        
    except Exception as e:
        return []

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    top_4 = run_deep_research()
    
    # Cálculo de alocação (R$ 10.000 dividido por 4)
    budget_per_stock = 2500
    
    html_content = f"""
    <html>
        <head>
            <title>Sistema Alpha 20%</title>
            <style>
                body {{ font-family: Arial, sans-serif; background: #f4f4f9; padding: 20px; }}
                .card {{ background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
                h1 {{ color: #333; }}
                .price {{ color: green; font-weight: bold; }}
                .action {{ background: #007bff; color: white; padding: 10px; text-decoration: none; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <h1>🚀 Deep Research: Carteira Top 4</h1>
            <p>Meta: 20% a.a. | Rebalanceamento Mensal</p>
            <hr>
            
            {''.join([f'''
            <div class="card">
                <h2>{stock['ticker']}</h2>
                <p>Preço Atual: <span class="price">R$ {stock['price']}</span></p>
                <p>Performance 6m: {stock['momentum']}% | Risco: {stock['volatility']}%</p>
                <p><strong>Ordem de Compra:</strong> Comprar aprox. {int(budget_per_stock / stock['price'])} ações (R$ 2.500)</p>
            </div>
            ''' for stock in top_4])}
            
            <br>
            <p><em>Dados atualizados em tempo real via Yahoo Finance.</em></p>
        </body>
    </html>
    """
    return html_content

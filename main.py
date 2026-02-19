from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import yfinance as yf
import pandas as pd
import numpy as np

app = FastAPI()

TICKERS = [
    'VALE3.SA', 'PETR4.SA', 'ITUB4.SA', 'BBAS3.SA', 'WEGE3.SA', 
    'PRIO3.SA', 'CMIG4.SA', 'CPLE6.SA', 'GGBR4.SA', 'JBSS3.SA', 
    'SUZB3.SA', 'VIVT3.SA', 'RENT3.SA', 'EGIE3.SA', 'TIMS3.SA', 
    'CSAN3.SA', 'B3SA3.SA', 'BBSE3.SA', 'ELET3.SA', 'ABEV3.SA'
]

def check_fundamentals(ticker_symbol):
    """
    Avalia a empresa e retorna uma tupla: (Status_Aprovacao, Motivo)
    """
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info
        
        pe_ratio = info.get('trailingPE', 0)
        roe = info.get('returnOnEquity', 0)
        
        # Checagem 1: Falta de dados na API
        if pe_ratio is None or roe is None:
            return False, "Dados financeiros ausentes na API."
            
        # Checagem 2: P/L Negativo (Prejuízo) ou Muito Alto (Cara demais)
        if pe_ratio <= 0:
            return False, f"Empresa dando prejuízo (P/L: {round(pe_ratio, 2)})."
        if pe_ratio >= 30:
            return False, f"Ação cara demais (P/L: {round(pe_ratio, 2)} > 30)."
            
        # Checagem 3: ROE Negativo ou Zero (Baixa eficiência)
        if roe <= 0:
            return False, f"Retorno sobre Patrimônio negativo/zero (ROE: {round(roe*100, 2)}%)."
            
        return True, "Aprovada"
        
    except Exception as e:
        return False, "Falha de conexão com a API do Yahoo Finance."

def run_deep_research():
    try:
        approved_tickers = []
        discarded_list = []
        
        # Filtro de Qualidade e Registro de Reprovações
        for ticker in TICKERS:
            is_approved, reason = check_fundamentals(ticker)
            if is_approved:
                approved_tickers.append(ticker)
            else:
                discarded_list.append({
                    "ticker": ticker.replace('.SA', ''),
                    "reason": reason
                })
                
        if not approved_tickers:
            return [], discarded_list
            
        # Baixa dados apenas das aprovadas
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
                    "ticker": ticker.replace('.SA', ''),
                    "price": round(end_price, 2),
                    "momentum": round(momentum * 100, 2),
                    "volatility": round(volatility * 100, 2),
                    "score": round(score, 2)
                })
            except Exception:
                continue
                
        ranking = pd.DataFrame(results).sort_values(by="score", ascending=False)
        top_4 = ranking.head(4).to_dict(orient="records")
        
        return top_4, discarded_list
        
    except Exception as e:
        return [], [{"ticker": "ERRO GERAL", "reason": str(e)}]

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    top_4, discarded_list = run_deep_research()
    budget_per_stock = 2500
    
    html_content = f"""
    <html>
        <head>
            <title>Sistema Alpha 20% (Blindado)</title>
            <style>
                body {{ font-family: Arial, sans-serif; background: #121212; color: #e0e0e0; padding: 20px; }}
                .container {{ max-width: 800px; margin: auto; }}
                .card {{ background: #1e1e1e; padding: 15px 20px; margin: 10px 0; border-radius: 8px; border-left: 5px solid #00ff88; }}
                h1, h2, h3 {{ color: #00ff88; }}
                .price {{ color: #00ff88; font-weight: bold; font-size: 1.2em; }}
                .tag {{ background: #333; padding: 5px 10px; border-radius: 4px; font-size: 0.9em; }}
                .discard-table {{ width: 100%; border-collapse: collapse; margin-top: 20px; background: #1e1e1e; border-radius: 8px; overflow: hidden; }}
                .discard-table th, .discard-table td {{ padding: 12px; text-align: left; border-bottom: 1px solid #333; }}
                .discard-table th {{ background: #2a2a2a; color: #ff4444; }}
                .discard-table tr:last-child td {{ border-bottom: none; }}
                .ticker-cell {{ font-weight: bold; color: #ffaa00; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🛡️ Deep Research: Carteira Alpha Blindada</h1>
                <p>Meta: 20% a.a. | Rebalanceamento Mensal</p>
                <hr>
                
                <h3>✅ Top 4 Ações (Aprovadas para Compra)</h3>
                {''.join([f'''
                <div class="card">
                    <h2>{stock['ticker']}</h2>
                    <p>Cotação: <span class="price">R$ {stock['price']}</span></p>
                    <p>
                        <span class="tag">Alta 6m: {stock['momentum']}%</span> 
                        <span class="tag">Risco: {stock['volatility']}%</span>
                    </p>
                    <p>🎯 <strong>Comprar:</strong> {int(budget_per_stock / stock['price'])} ações (Usar Ticker: {stock['ticker']}F)</p>
                </div>
                ''' for stock in top_4])}
                
                <br><br>
                <h3>🚫 Lista de Corte (Ações Reprovadas)</h3>
                <table class="discard-table">
                    <tr>
                        <th>Ativo</th>
                        <th>Motivo da Reprovação no Filtro</th>
                    </tr>
                    {''.join([f'''
                    <tr>
                        <td class="ticker-cell">{discard['ticker']}</td>
                        <td>{discard['reason']}</td>
                    </tr>
                    ''' for discard in discarded_list])}
                </table>
            </div>
        </body>
    </html>
    """
    return html_content

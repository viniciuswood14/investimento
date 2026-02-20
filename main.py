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

def fetch_data(ticker_symbol):
    """ Busca todos os dados necessários de uma vez para otimizar a API. """
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info
        
        pe_ratio = info.get('trailingPE', 0)
        roe = info.get('returnOnEquity', 0)
        dy = info.get('dividendYield', 0)
        
        # Tratamento para valores ausentes (yfinance costuma retornar None se for 0)
        pe_ratio = float(pe_ratio) if pe_ratio else 0
        roe = float(roe) if roe else 0
        dy = float(dy) if dy else 0
        
        # Filtro de Qualidade (O Bouncer)
        if pe_ratio <= 0:
            return False, f"Prejuízo (P/L: {round(pe_ratio, 2)})", None
        if pe_ratio >= 30:
            return False, f"Muito cara (P/L: {round(pe_ratio, 2)} > 30)", None
        if roe <= 0:
            return False, f"ROE negativo/zero ({round(roe*100, 2)}%)", None
            
        dados_fundamentos = {
            "pe": pe_ratio,
            "roe": roe,
            "dy": dy
        }
        return True, "Aprovada", dados_fundamentos
        
    except Exception as e:
        return False, "Falha na API ou falta de dados.", None

def run_dual_strategy():
    try:
        approved_tickers = {}
        discarded_list = []
        
        # 1. Coleta e Filtro de Fundamentos
        for ticker in TICKERS:
            is_approved, reason, fundamentals = fetch_data(ticker)
            if is_approved:
                approved_tickers[ticker] = fundamentals
            else:
                discarded_list.append({"ticker": ticker.replace('.SA', ''), "reason": reason})
                
        if not approved_tickers:
            return [], [], discarded_list
            
        ativos_aprovados = list(approved_tickers.keys())
        
        # 2. Coleta de Preços para o Curto Prazo (Momentum/Volatilidade)
        df = yf.download(ativos_aprovados, period="6mo", progress=False)['Close']
        
        resultados_curto_prazo = []
        resultados_longo_prazo = []
        
        for ticker in ativos_aprovados:
            try:
                # Dados Técnicos (Curto Prazo)
                start_price = float(df[ticker].iloc[0])
                end_price = float(df[ticker].iloc[-1])
                momentum = (end_price / start_price) - 1
                
                daily_pct = df[ticker].pct_change()
                volatility = float(daily_pct.std() * np.sqrt(252))
                
                # Cálculo Curto Prazo (Sharpe: Retorno / Risco)
                score_cp = momentum / volatility if volatility > 0 else 0
                
                resultados_curto_prazo.append({
                    "ticker": ticker.replace('.SA', ''),
                    "price": round(end_price, 2),
                    "momentum": round(momentum * 100, 2),
                    "volatility": round(volatility * 100, 2),
                    "score_cp": round(score_cp, 2)
                })
                
                # Cálculo Longo Prazo (Value + Dividends: (ROE / P/L) + DY)
                f = approved_tickers[ticker]
                score_lp = (f['roe'] / f['pe']) + f['dy']
                
                resultados_longo_prazo.append({
                    "ticker": ticker.replace('.SA', ''),
                    "price": round(end_price, 2),
                    "roe": round(f['roe'] * 100, 2),
                    "pe": round(f['pe'], 2),
                    "dy": round(f['dy'] * 100, 2),
                    "score_lp": round(score_lp, 4)
                })
                
            except Exception:
                continue
                
        # 3. Ranqueamento Final
        ranking_cp = pd.DataFrame(resultados_curto_prazo).sort_values(by="score_cp", ascending=False)
        top_4_cp = ranking_cp.head(4).to_dict(orient="records")
        
        ranking_lp = pd.DataFrame(resultados_longo_prazo).sort_values(by="score_lp", ascending=False)
        top_4_lp = ranking_lp.head(4).to_dict(orient="records")
        
        return top_4_cp, top_4_lp, discarded_list
        
    except Exception as e:
        print(f"Erro geral: {e}")
        return [], [], [{"ticker": "ERRO", "reason": str(e)}]

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    top_4_cp, top_4_lp, discarded_list = run_dual_strategy()
    budget_per_stock = 2500
    
    html_content = f"""
    <html>
        <head>
            <title>Alpha 20% & Hold</title>
            <style>
                body {{ font-family: Arial, sans-serif; background: #121212; color: #e0e0e0; padding: 20px; }}
                .container {{ max-width: 1000px; margin: auto; }}
                .grid {{ display: flex; gap: 20px; }}
                .col {{ flex: 1; }}
                .card-cp {{ background: #1e1e1e; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 5px solid #00ff88; }}
                .card-lp {{ background: #1e1e1e; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 5px solid #8800ff; }}
                h1, h2 {{ text-align: center; }}
                .title-cp {{ color: #00ff88; }}
                .title-lp {{ color: #8800ff; }}
                .price {{ font-weight: bold; font-size: 1.2em; }}
                .price-cp {{ color: #00ff88; }}
                .price-lp {{ color: #8800ff; }}
                .tag {{ background: #333; padding: 5px 10px; border-radius: 4px; font-size: 0.85em; margin-right: 5px; }}
                .discard-table {{ width: 100%; border-collapse: collapse; margin-top: 30px; background: #1e1e1e; border-radius: 8px; overflow: hidden; }}
                .discard-table th, .discard-table td {{ padding: 12px; text-align: left; border-bottom: 1px solid #333; }}
                .discard-table th {{ background: #2a2a2a; color: #ff4444; }}
                .ticker-cell {{ font-weight: bold; color: #ffaa00; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1 style="color: #fff;">📊 Sistema de Investimento Dual</h1>
                <hr style="border-color: #333;">
                
                <div class="grid">
                    <div class="col">
                        <h2 class="title-cp">⚡ Tática (Curto Prazo)</h2>
                        <p style="text-align: center; font-size: 0.9em; color: #aaa;">Foco: Retorno 20% | Rebalanceamento Mensal</p>
                        {''.join([f'''
                        <div class="card-cp">
                            <h3 style="margin-top: 0;">{stock['ticker']}</h3>
                            <p>Cotação: <span class="price price-cp">R$ {stock['price']}</span></p>
                            <p>
                                <span class="tag">Momentum: {stock['momentum']}%</span> 
                                <span class="tag">Risco: {stock['volatility']}%</span>
                            </p>
                            <p>🛒 Comprar: {int(budget_per_stock / stock['price'])} ações</p>
                        </div>
                        ''' for stock in top_4_cp])}
                    </div>
                    
                    <div class="col">
                        <h2 class="title-lp">🏦 Estrutural (Longo Prazo)</h2>
                        <p style="text-align: center; font-size: 0.9em; color: #aaa;">Foco: Dividendos e Valor | Buy & Hold</p>
                        {''.join([f'''
                        <div class="card-lp">
                            <h3 style="margin-top: 0;">{stock['ticker']}</h3>
                            <p>Cotação: <span class="price price-lp">R$ {stock['price']}</span></p>
                            <p>
                                <span class="tag">P/L: {stock['pe']}</span> 
                                <span class="tag">ROE: {stock['roe']}%</span>
                                <span class="tag" style="background: #440088;">DY: {stock['dy']}%</span>
                            </p>
                            <p>🛒 Comprar para acumular</p>
                        </div>
                        ''' for stock in top_4_lp])}
                    </div>
                </div>
                
                <h3 style="color: #ff4444; margin-top: 40px;">🚫 Reprovadas no Filtro de Qualidade</h3>
                <table class="discard-table">
                    <tr>
                        <th>Ativo</th>
                        <th>Motivo da Reprovação no Balanço</th>
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

import dash
from dash import dcc, html
from dash.dependencies import Output, Input
from dash_iconify import DashIconify
import plotly.graph_objects as go
import numpy as np
import datetime
from waf_api import fetch_attack_logs

COUNTRY_FLAG = {
    "US": "🇺🇸", "ID": "🇮🇩", "PH": "🇵🇭", "SG": "🇸🇬", "CN": "🇨🇳", "RU": "🇷🇺",
    "DE": "🇩🇪", "MY": "🇲🇾", "JP": "🇯🇵", "IN": "🇮🇳", "KR": "🇰🇷", "FR": "🇫🇷",
}
COUNTRY_FULL = {
    "US": "United States", "ID": "Indonesia", "PH": "Philippines", "SG": "Singapore", "CN": "China",
    "RU": "Russia", "DE": "Germany", "MY": "Malaysia", "JP": "Japan", "IN": "India", "KR": "Korea", "FR": "France"
}
TARGET_LAT, TARGET_LON = -1.5789, 101.3033

def patch_record(rec):
    cc = (rec.get('country', '')[:2] or "ID").upper()
    country = rec.get('country', 'Unknown')
    dt = rec.get('start_at', int(datetime.datetime.now().timestamp()*1000))
    domain = rec.get('host', '-')
    deny = int(rec.get('deny_count', 0))
    url_path = rec.get('url_path', '-')
    return {
        'ip': rec.get('ip', '-'),
        'country_code': cc,
        'country': country,
        'start_at': dt,
        'deny_count': deny,
        'domain': domain,
        'url_path': url_path,
    }


# ========== ANIMASI S-CURVE ========== #
def s_curve_points(lat1, lon1, lat2, lon2, steps=28, arch=13):
    mid1_lat = (lat1 + lat2) / 2 + arch
    mid1_lon = (lon1 + lon2) / 2 - arch / 2
    mid2_lat = (lat1 + lat2) / 2 - arch
    mid2_lon = (lon1 + lon2) / 2 + arch / 2
    lats, lons = [], []
    for t in np.linspace(0, 1, steps):
        lat = (1-t)**3*lat1 + 3*(1-t)**2*t*mid1_lat + 3*(1-t)*t**2*mid2_lat + t**3*lat2
        lon = (1-t)**3*lon1 + 3*(1-t)**2*t*mid1_lon + 3*(1-t)*t**2*mid2_lon + t**3*lon2
        lats.append(lat)
        lons.append(lon)
    return lats, lons

def make_map_figure(records, anim_idx=0):
    fig = go.Figure()
    steps = 28
    geo_map = {
        "US": (37.751, -97.822),
        "ID": (-6.2000, 106.8167),
        "PH": (13.41, 122.56),
        "SG": (1.3521, 103.8198),
        "CN": (35.8617, 104.1954),
        "RU": (61.5240, 105.3188),
        "DE": (51.1657, 10.4515),
        "MY": (4.2105, 101.9758),
        "JP": (36.2048, 138.2529),
        "IN": (20.5937, 78.9629),
        "KR": (35.9078, 127.7669),
        "FR": (46.6034, 1.8883)
    }
    np.random.seed(0)
    for i, rec in enumerate(records[:5]):
        cc = rec.get('country_code','')
        country = COUNTRY_FULL.get(cc, cc)
        lat, lon = geo_map.get(cc, (TARGET_LAT + np.random.uniform(-3, 3), TARGET_LON + np.random.uniform(-3, 3)))
        lats, lons = s_curve_points(lat, lon, TARGET_LAT, TARGET_LON, steps=steps, arch=13)
        # S-Curve garis animasi
        fig.add_trace(go.Scattergeo(
            lon=lons,
            lat=lats,
            mode='lines',
            line=dict(width=3, color='rgba(56,189,248,0.18)'),
            opacity=0.7, hoverinfo='none', showlegend=False
        ))
        # Efek burst/animasi bulatan berjalan di garis
        progress = anim_idx % steps
        fade = 6
        for p in range(progress-fade, progress+1):
            if 0 <= p < steps:
                alpha = (p-progress+fade)/fade
                fig.add_trace(go.Scattergeo(
                    lon=[lons[p]], lat=[lats[p]],
                    mode='markers',
                    marker=dict(
                        size=11-(progress-p), color=f'rgba(56,189,248,{0.45+0.5*alpha})',
                        line=dict(width=1, color='#fff')
                    ),
                    hoverinfo='none', showlegend=False
                ))
        # Titik attacker
        fig.add_trace(go.Scattergeo(
            lon=[lon], lat=[lat],
            mode='markers',
            marker=dict(
                size=17,
                color='#38bdf8', line=dict(width=3, color='#fff')
            ),
            hoverinfo='text', text=[f"{COUNTRY_FLAG.get(cc,'')} {country}<br>{rec['ip']}<br>{rec['domain']}"], showlegend=False
        ))
    # Target
    fig.add_trace(go.Scattergeo(
        lon=[TARGET_LON], lat=[TARGET_LAT],
        mode='markers+text',
        marker=dict(
            size=34,
            color="#2563eb", line=dict(width=6, color="#fff")
        ),
        text=["Pemkab Solok Selatan"], textfont=dict(size=18, color="#fff"),
        textposition="top center", hoverinfo='text', showlegend=False
    ))
    fig.update_layout(
        geo=dict(
            projection_type="natural earth",
            showland=True,
            landcolor="#162131",
            countrycolor="#254070",
            lakecolor="#19253b",
            bgcolor="#101728",
            showcountries=True, showframe=False, showcoastlines=True,
        ),
        paper_bgcolor="#101728",
        plot_bgcolor="#101728",
        height=670,
        margin=dict(r=0, l=0, t=0, b=0)
    )
    return fig

def make_top_ip_list(records):
    from collections import Counter
    ip_country = [(r['ip'], r.get('country_code',''), r.get('country','')) for r in records]
    top_ip = Counter([(ip, cc, country) for (ip, cc, country) in ip_country]).most_common(5)
    badge_class = ["ta-gold", "ta-silver", "ta-bronze", "ta-gray", "ta-red"]
    rows = []
    for i, ((ip, cc, country), count) in enumerate(top_ip):
        rows.append(
            html.Div([
                html.Span(str(i+1), className=f"ta-badge {badge_class[i]}", style={"flexShrink": "0"}),
                html.Span(COUNTRY_FLAG.get(cc, ""), className="ta-flag"),
                html.Span(country, className="ta-country", style={
                    "fontWeight": "900",
                    "marginRight": "10px",
                    "fontSize": "1.05em"
                }),
                html.Span(ip, className="ta-ip", style={
                    "fontWeight": "700",
                    "fontSize": "1.07em",
                    "color": "#223251",
                    "marginRight": "10px"
                }),
                html.Span(str(count), className="ta-count", style={
                    "color": "#ef1444",
                    "fontWeight": "900",
                    "fontSize": "1.17em",
                    "marginLeft": "auto",
                    "marginRight": "8px"
                }),
            ],
            className="ta-row",
            style={
                "background": "#f8fafd" if i % 2 == 0 else "#eef4fd",
                "borderRadius": "13px",
                "marginBottom": "8px",
                "padding": "7px 10px 7px 7px",
                "alignItems": "center",
                "minHeight": "36px",
                "display": "flex"
            })
        )
    return html.Div([
        html.Div([
            DashIconify(icon="mdi:ip-network-outline", width=26, color="#2052a8", style={"marginRight": "8px"}),
            html.Span("IP Addr", className="ta-title", style={'color': '#2052a8', 'fontWeight': '900', 'fontSize': '1.13em'}),
            html.Span("24 hours", style={'fontWeight':700, 'color': '#2052a8', 'marginLeft':'auto', 'fontSize':'1.03em'}),
        ], className="ta-header", style={"marginBottom": "14px", "alignItems": "center"}),
        *rows
    ], className="ta-card", style={
        'background': 'linear-gradient(115deg,#f9fbff 60%,#e3eeff 100%)',
        'boxShadow': '0 4px 22px 0 #e3eefe66',
        'borderRadius': '20px',
        "padding": "18px 8px 12px 11px"
    })

def make_attack_log_table(records):
    # Header
    table_header = html.Div([
        html.Span("No", style={"width": "36px", "fontWeight": 800, "paddingLeft": "12px"}),
        html.Span("Domain", style={"width": "300px", "fontWeight": 800}),
        html.Span("IP Address", style={"width": "130px", "fontWeight": 800}),
        html.Span("Country", style={"width": "95px", "fontWeight": 800}),
        html.Span("Datetime", style={"width": "135px", "fontWeight": 800}),
        html.Span("Denied", style={"width": "70px", "fontWeight": 800, "textAlign": "center"}),
        html.Span("URL Path", style={"width": "260px", "fontWeight": 800}),
    ], style={
        "display": "flex",
        "gap": "8px",
        "background": "#eaf3ff",
        "borderRadius": "13px 13px 0 0",
        "padding": "12px 0 10px 0",
        "fontSize": "1.08em"
    })

    # Isi log (max 5 baris)
    table_rows = []
    for idx, rec in enumerate(records[:5]):
        cc = rec.get('country_code', '')
        country = rec.get('country', cc)
        ts = datetime.datetime.fromtimestamp(rec.get('start_at', 0)//1000).strftime('%Y-%m-%d %H:%M:%S')
        domain = rec.get('domain', '-')
        domain_link = f"http://{domain}" if domain != "-" else "#"
        url_path = rec.get('url_path', '-')
        table_rows.append(html.Div([
            html.Span(str(idx+1), style={"width": "36px", "fontWeight": 700, "paddingLeft": "12px"}),
            html.A(domain, href=domain_link, style={
                "width": "300px", "fontWeight": 700, "color": "#2563eb",
                "textDecoration": "none", "overflow": "hidden", "textOverflow": "ellipsis", "whiteSpace": "nowrap"
            }, target="_blank"),
            html.Span(rec['ip'], style={"width": "130px", "fontWeight": 600, "color": "#223251"}),
            html.Span(f"{COUNTRY_FLAG.get(cc,'')} {country}", style={"width": "95px"}),
            html.Span(ts, style={"width": "135px"}),
            html.Span(
                str(rec.get('deny_count', 0)),
                style={
                    "width": "70px",
                    "color": "#ef1444" if rec.get('deny_count', 0) > 0 else "#7890a9",
                    "fontWeight": "900" if rec.get('deny_count', 0) > 0 else 700,
                    "textAlign": "center",
                    "fontSize": "1.1em"
                }
            ),
            html.Span(url_path, style={
                "width": "260px",
                "fontFamily": "JetBrains Mono, monospace",
                "fontSize": "0.99em",
                "color": "#465f8c",
                "overflow": "hidden",
                "textOverflow": "ellipsis",
                "whiteSpace": "nowrap"
            }),
        ], style={
            "display": "flex",
            "gap": "8px",
            "padding": "11px 0",
            "background": "#fff" if idx % 2 == 0 else "#f7fafd",
            "borderRadius": "7px",
            "fontSize": "1.04em",
            "alignItems": "center"
        }))

    return html.Div([
        html.Div("Attack Log Realtime", style={
            "fontWeight": 900,
            "color": "#2052a8",
            "fontSize": "1.21em",
            "margin": "7px 0 13px 2px"
        }),
        html.Div([table_header, *table_rows], style={
            "borderRadius": "13px",
            "boxShadow": "0 2px 12px #bae6fd22",
            "background": "linear-gradient(115deg,#f9fbff 60%,#e3eeff 100%)"
        })
    ], style={"margin": "32px 0 0 0", "padding": "0 4vw"})


def make_realtime_attack(records):
    elements = []
    for rec in records[:5]:
        ip = rec['ip']
        cc = rec.get('country_code','')
        country = COUNTRY_FULL.get(cc, cc)
        flag = COUNTRY_FLAG.get(cc, '')
        ts = datetime.datetime.fromtimestamp(rec.get('start_at', 0)//1000).strftime('%Y-%m-%d %H:%M:%S')
        deny_count = rec.get('deny_count', 0)
        elements.append(
            html.Div([
                html.Div([
                    html.Span(flag, className="rt-flag"),
                    html.Span(country, className="rt-country"),
                    html.A(ip, href=f"https://ipinfo.io/{ip}", target="_blank", className="rt-ip-link"),
                ], className="rt-ipbox"),
                html.Span(ts, className="rt-time"),
                html.Span(
                    str(deny_count),
                    className="rt-deny-badge" if deny_count > 0 else "rt-deny-zero"
                )
            ], className="rt-attack-item")
        )
    return html.Div([
        html.Div("Real-time Attack", className="rt-attack-title"),
        *elements
    ], className="realtime-attack-card")

external_stylesheets = [
    "https://fonts.googleapis.com/css2?family=Inter:wght@600;800&family=JetBrains+Mono:wght@400;600&display=swap",
    "/root/attack-map-dashboard/assets/modern-style.css",
]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div([
    html.Div([
        html.Img(src='https://upload.wikimedia.org/wikipedia/commons/5/50/Lambang_Kabupaten_Solok_Selatan.png', style={
            'height': '48px', 'margin-right':'18px', 'vertical-align':'middle'}),
        html.Span("DASHBOARD MAP ATTACK", style={'font-size':'2.2rem','font-weight':900, 'color':'#fff', 'letter-spacing':'0.08em'}),
        html.Div(id="clock", className="clock-blink", style={
            'font-family':'JetBrains Mono', 'color':'#fff', 'background':'#233257',
            'font-size':'1.21em', 'border-radius':'13px', 'padding':'6px 26px',
            'margin-left':'auto', 'box-shadow':'0 2px 8px #2226'
        }),
    ], style={
        'display':'flex', 'align-items':'center', 'background':'#19223c', 'padding':'17px 38px 14px 28px',
        'border-radius':'0 0 30px 30px', 'box-shadow':'0 8px 36px 0 #1116', 'margin-bottom':'12px',
        'min-width': '900px', 'max-width': '1700px', 'margin': '0 auto 16px auto'
    }),
    html.Div([
        html.Div([
            html.Div(id="top-ip-list"),
            html.Div(id='dashboard-stats'),
        ], className="left-panel", style={
            'min-width': '255px', 'max-width': '315px', 'padding':'10px 0 0 24px'
        }),
        html.Div([
            dcc.Graph(id='attack-map', config={'displayModeBar': False}),
            html.Div(id="attack-log-table"),
            dcc.Interval(id='interval', interval=15000, n_intervals=0)
        ], className="map-panel", style={
            'flex': 2.2, 'min-width': '850px', 'max-width': '1900px', 'margin':'10px 24px 0 24px',
            'background':'#101728', 'border-radius':'30px', 'box-shadow':'0 4px 20px 0 #2223',
            'padding':'8px 8px 0 8px', 'height': '900px'
        }),
        html.Div(id='realtime-attack', className="right-panel", style={
            'min-width': '250px', 'max-width': '325px', 'padding':'10px 18px 0 0'
        }),
    ], className='main-flex', style={
        'display':'flex', 'background':'none', 'padding-bottom':'11px',
        'max-width':'2200px', 'min-width':'900px', 'margin':'0 auto'
    }),
], style={
    'background':'#101728', 'min-height':'100vh', 'font-family':"Inter, 'JetBrains Mono', Arial, sans-serif", 'overflowX':'hidden'
})

def get_dashboard_stats(records):
    uv = len(set([r['ip'] for r in records]))
    pv = len(records)
    blocked = sum(1 for r in records if r.get('deny_count', 0) > 0)
    return {'uv': uv, 'pv': pv, 'blocked': blocked}

@app.callback(
    Output('dashboard-stats', 'children'),
    Output('top-ip-list', 'children'),
    Input('interval', 'n_intervals')
)
def update_stats(n):
    data_api = fetch_attack_logs(page_size=10, page=1)
    records = [patch_record(r) for r in data_api]
    stats = get_dashboard_stats(records)
    return (
        html.Div([
            html.Div(className="stats-card", children=[
                html.Div(className="stats-icon", children=DashIconify(icon="mdi:account-group", width=28, color="#fff")),
                html.Div(className="stats-info", children=[
                    html.Div("UV in 24 hours", className="stats-title"),
                    html.Div(f"{stats['uv']:,}", className="stats-value"),
                ])
            ]),
            html.Div(className="stats-card", children=[
                html.Div(className="stats-icon blue", children=DashIconify(icon="mdi:eye-outline", width=28, color="#fff")),
                html.Div(className="stats-info", children=[
                    html.Div("PV in 24 hours", className="stats-title"),
                    html.Div(f"{stats['pv']:,}", className="stats-value"),
                ])
            ]),
            html.Div(className="stats-card", children=[
                html.Div(className="stats-icon orange", children=DashIconify(icon="mdi:shield-off-outline", width=28, color="#fff")),
                html.Div(className="stats-info", children=[
                    html.Div("Blocked Real-Time", className="stats-title"),
                    html.Div(f"{stats['blocked']:,}", className="stats-value"),
                ])
            ]),
        ], className='stats-card-wrap'),
        make_top_ip_list(records)
    )

@app.callback(
    Output('attack-map', 'figure'),
    Output('realtime-attack', 'children'),
    Output('clock', 'children'),
    Output('attack-log-table', 'children'),
    Input('interval', 'n_intervals')
)
def update_map(n):
    data_api = fetch_attack_logs(page_size=10, page=1)
    records = [patch_record(r) for r in data_api]
    fig = make_map_figure(records, n % 28)
    realtime = make_realtime_attack(records)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    attack_log_table = make_attack_log_table(records)
    return fig, realtime, now, attack_log_table

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8050)
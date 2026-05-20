import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json

df = pd.read_csv('../data/merged_data_k4.csv', index_col=0)

country_jp = {
    'Mexico': 'メキシコ', 'Guatemala': 'グアテマラ', 'Colombia': 'コロンビア',
    'Brazil': 'ブラジル', 'Taiwan': '台湾', 'United States (Hawaii)': 'ハワイ',
    'Honduras': 'ホンジュラス', 'Costa Rica': 'コスタリカ',
}
method_jp = {
    'Washed / Wet': 'ウォッシュド',
    'Natural / Dry': 'ナチュラル',
    'Semi-washed / Semi-pulped': 'セミウォッシュド',
    'Pulped natural / honey': 'ハニー',
    'Other': 'その他',
}
cluster_colors = {
    '酸味系':        '#5B8FD4',
    'バランス系':    '#F5C842',
    'コク・バランス系': '#9B6BCC',
    '香り系':        '#5BBD72',
}
all_clusters = list(cluster_colors.keys())
method_order = ['その他', 'ハニー', 'セミウォッシュド', 'ナチュラル', 'ウォッシュド']

df['Country_JP'] = df['Country.of.Origin'].map(country_jp)
df['Method_JP'] = df['Processing.Method'].map(method_jp)
df = df[df['Country_JP'].notna() & df['Method_JP'].notna()].copy()
df['Region_raw'] = df['Region'].fillna('').str.lower().str.strip()

# 国ごとの地域正規化マッピング
region_normalize = {
    'Mexico': {
        'veracruz': 'ベラクルス',
        'coatepec': 'ベラクルス',  # coatepecはveracruz州の都市
        'xalapa': 'ベラクルス',
        'chiapas': 'チアパス',
        'la concordia': 'チアパス',
        'la concordia, chiapas': 'チアパス',
        'tapachula': 'チアパス',
        'zaragoza itundujia': 'オアハカ',
        'oaxaca': 'オアハカ',
    },
    'Guatemala': {
        'oriente': 'オリエンテ',
        'huehuetenango': 'ウエウエテナンゴ',
        'antigua': 'アンティグア',
        'san marcos': 'サンマルコス',
        'santa rosa': 'サンタロサ',
        'chiquimula': 'オリエンテ',
    },
    'Colombia': {
        'huila': 'ウイラ',
        'cauca': 'カウカ',
        'santander': 'サンタンデール',
        'cundinamarca': 'クンディナマルカ',
        'pitalito': 'ウイラ',
        'nariño': 'ナリーニョ',
        'narino': 'ナリーニョ',
        'tolima': 'トリマ',
    },
    'Brazil': {
        'south of minas': 'ミナスジェライス南部',
        'cerrado': 'セラード',
        'monte carmelo': 'ミナスジェライス南部',
        'grama valley': 'ミナスジェライス南部',
        'vale da grama': 'ミナスジェライス南部',
        'minas gerais': 'ミナスジェライス',
        'mogiana': 'モジアナ',
    },
    'Honduras': {
        'comayagua': 'コマヤグア',
        'marcala': 'マルカラ',
        'intibuca': 'インティブカ',
        'santa barbara': 'サンタバーバラ',
        'lempira': 'レンピラ',
    },
    'Costa Rica': {
        'tarrazu': 'タラス',
        'central valley': '中央谷',
        'san ramon': '中央谷',
        'tres rios': 'トレスリオス',
        'west valley': '西部谷',
        'brunca': 'ブルンカ',
        'turrialba': 'トゥリアルバ',
    },
    'Taiwan': {
        'dongshan dist., tainan city 臺南市東山區': '台南東山',
        'natou county': '南投',
        'nantou': '南投',
        'taichung xinshe 台中市新社區': '台中新社',
        'changhua baguashan 彰化市八卦山': '彰化',
        'taiwan': 'その他',
        '台灣': 'その他',
        '南投國姓': '南投',
        '國姓鄉 guoshing township': '南投',
    },
    'United States (Hawaii)': {
        'kona': 'コナ',
    },
}

TOP_N = 5  # 上位N地域を表示、残りは「その他」


def get_region_jp(row):
    country = row['Country.of.Origin']
    region_raw = row['Region_raw']
    if not region_raw:
        return 'その他/不明'
    mapping = region_normalize.get(country, {})
    # 完全一致
    if region_raw in mapping:
        return mapping[region_raw]
    # 部分一致
    for key, val in mapping.items():
        if key in region_raw or region_raw in key:
            return val
    return None  # 後でその他に


df['Region_JP'] = df.apply(get_region_jp, axis=1)


def get_top_regions(country_df, country_en):
    known = country_df[country_df['Region_JP'].notna() & (country_df['Region_JP'] != 'その他/不明')]
    counts = known['Region_JP'].value_counts()
    top = counts.head(TOP_N).index.tolist()
    return top


# 各国の上位地域を決定
country_top_regions = {}
for country_en in country_jp.keys():
    sub = df[df['Country.of.Origin'] == country_en].copy()
    top = get_top_regions(sub, country_en)
    country_top_regions[country_en] = top


def finalize_region(row, top_regions):
    rjp = row['Region_JP']
    if rjp is None or rjp not in top_regions:
        return 'その他/不明'
    return rjp


def build_fig(country_en):
    country_name = country_jp[country_en]
    top_regions = country_top_regions[country_en]
    if not top_regions:
        top_regions = ['不明']
    region_order = top_regions + ['その他/不明']

    sub_country = df[df['Country.of.Origin'] == country_en].copy()
    sub_country['Region_Final'] = sub_country.apply(
        lambda r: finalize_region(r, top_regions), axis=1
    )

    n_rows = len(method_order)
    n_cols = len(region_order)

    specs = [[{'type': 'domain'} for _ in range(n_cols)] for _ in range(n_rows)]
    subplot_titles = []
    for method in method_order:
        for region in region_order:
            cell = sub_country[
                (sub_country['Method_JP'] == method) &
                (sub_country['Region_Final'] == region)
            ]
            subplot_titles.append(f'n={len(cell)}' if len(cell) > 0 else '')

    fig = make_subplots(
        rows=n_rows, cols=n_cols,
        specs=specs,
        subplot_titles=subplot_titles,
        vertical_spacing=0.07,
        horizontal_spacing=0.02,
    )

    for ann in fig.layout.annotations:
        ann.font.size = 9
        ann.font.color = '#888888'

    for row_i, method in enumerate(method_order):
        for col_i, region in enumerate(region_order):
            cell = sub_country[
                (sub_country['Method_JP'] == method) &
                (sub_country['Region_Final'] == region)
            ]
            total = len(cell)

            if total == 0:
                fig.add_trace(
                    go.Pie(
                        values=[1],
                        marker_colors=['#F0F0F0'],
                        showlegend=False,
                        hoverinfo='none',
                        textinfo='none',
                    ),
                    row=row_i + 1, col=col_i + 1,
                )
            else:
                counts = cell['ClusterName'].value_counts()
                sizes = [counts.get(c, 0) for c in all_clusters]
                colors = [cluster_colors[c] for c in all_clusters]
                fig.add_trace(
                    go.Pie(
                        labels=all_clusters,
                        values=sizes,
                        marker_colors=colors,
                        showlegend=False,
                        hovertemplate=(
                            f'<b>{region} × {method}</b><br>'
                            '%{label}: %{percent}<br>'
                            f'合計: {total}件'
                            '<extra></extra>'
                        ),
                        textinfo='none',
                        hole=0,
                    ),
                    row=row_i + 1, col=col_i + 1,
                )

    # 凡例ダミートレース
    for cluster, color in cluster_colors.items():
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            mode='markers',
            marker=dict(size=12, color=color, symbol='circle'),
            name=cluster,
            showlegend=True,
            legendgroup=cluster,
        ))

    # Y軸（精製方法）ラベル
    for row_i, method in enumerate(method_order):
        y_pos = 1 - (row_i + 0.5) / n_rows
        fig.add_annotation(
            x=-0.01, y=y_pos,
            xref='paper', yref='paper',
            text=f'<b>{method}</b>',
            showarrow=False,
            font=dict(size=11, color='#333333'),
            xanchor='right',
            yanchor='middle',
        )

    # X軸（地域）ラベル
    for col_i, region in enumerate(region_order):
        x_pos = (col_i + 0.5) / n_cols
        fig.add_annotation(
            x=x_pos, y=1.03,
            xref='paper', yref='paper',
            text=f'<b>{region}</b>',
            showarrow=False,
            font=dict(size=11, color='#333333'),
            xanchor='center',
            yanchor='bottom',
        )

    fig.update_layout(
        title=dict(
            text=f'{country_name} 地域別マトリクス<br>'
                 '<sup>地域×精製方法の味クラスター分布</sup>',
            font=dict(size=16, family='Hiragino Sans'),
            x=0.5, y=0.98,
        ),
        height=680,
        width=max(900, 150 * n_cols + 200),
        plot_bgcolor='white',
        paper_bgcolor='white',
        legend=dict(
            title=dict(text='味クラスター', font=dict(size=12)),
            font=dict(size=11),
            x=1.01, y=0.5,
            xanchor='left',
            yanchor='middle',
            bgcolor='rgba(255,255,255,0.9)',
            bordercolor='#CCCCCC',
            borderwidth=1,
        ),
        margin=dict(l=130, r=150, t=110, b=40),
        font=dict(family='Hiragino Sans'),
    )

    return fig


# 全国のfigをJSONとして書き出してHTMLに埋め込む
country_order_list = ['Mexico', 'Guatemala', 'Colombia', 'Brazil',
                      'Taiwan', 'United States (Hawaii)', 'Honduras', 'Costa Rica']

figs_json = {}
for country_en in country_order_list:
    fig = build_fig(country_en)
    figs_json[country_en] = fig.to_json()

country_options_html = '\n'.join(
    f'<option value="{c}">{country_jp[c]}</option>'
    for c in country_order_list
)

html_template = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>地域別 コーヒー味クラスター</title>
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
<style>
  body {{ font-family: 'Hiragino Sans', 'Noto Sans JP', sans-serif; background: #fafafa; margin: 0; padding: 20px; }}
  .header {{ text-align: center; margin-bottom: 16px; }}
  .header h1 {{ font-size: 1.4em; color: #333; margin: 0 0 8px; }}
  .selector {{ text-align: center; margin-bottom: 20px; }}
  .selector label {{ font-size: 1em; color: #555; margin-right: 8px; }}
  .selector select {{
    font-size: 1.1em; padding: 6px 16px; border-radius: 6px;
    border: 1px solid #ccc; background: #fff; cursor: pointer;
    font-family: 'Hiragino Sans', sans-serif;
  }}
  #chart-container {{ max-width: 1400px; margin: 0 auto; background: #fff;
    border-radius: 10px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); padding: 10px; }}
</style>
</head>
<body>
<div class="header">
  <h1>コーヒー産地・地域別 味クラスターマトリクス</h1>
</div>
<div class="selector">
  <label for="country-select">産地を選択：</label>
  <select id="country-select" onchange="showCountry(this.value)">
    {country_options_html}
  </select>
</div>
<div id="chart-container">
  <div id="plotly-div"></div>
</div>
<script>
const figsData = {json.dumps(figs_json)};

function showCountry(countryEn) {{
  const figJson = figsData[countryEn];
  const figObj = JSON.parse(figJson);
  Plotly.newPlot('plotly-div', figObj.data, figObj.layout, {{responsive: true}});
}}

// 初期表示
showCountry('{country_order_list[0]}');
</script>
</body>
</html>"""

with open('../outputs/html/grid_pie_region.html', 'w', encoding='utf-8') as f:
    f.write(html_template)

print('保存完了: grid_pie_region.html')

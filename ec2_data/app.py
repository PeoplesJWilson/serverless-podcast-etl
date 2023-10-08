from dash import Dash, html, dcc, Input, Output, ctx, callback
from dash.exceptions import PreventUpdate
import plotly.express as px
import pandas as pd
import mysql.connector
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import load_figure_template

from io import BytesIO
import base64
from wordcloud import WordCloud, STOPWORDS
import numpy as np
from PIL import Image

import environment

USER_NAME = environment.USER_NAME
PASSWORD = environment.PASSWORD
DB_NAME  = environment.DB_NAME
RDS_ENDPOINT = environment.RDS_ENDPOINT

wc_mask = np.array(Image.open("comment.png"))
template = "cyborg"
load_figure_template([template])


app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])


connection = mysql.connector.connect(
    host=RDS_ENDPOINT,
    user=USER_NAME,
    password=PASSWORD,
    database=DB_NAME
)
cursor = connection.cursor()

# Query the database to get unique values of episodes
query = "SELECT DISTINCT podcast_id, podcast_title FROM podcast_dimension"
cursor.execute(query)
unique_podcasts = cursor.fetchall()
cursor.close()
connection.close()
# Prepare options for the dropdown
podcast_options = [{'label': value[1], 'value': value[0]} for value in unique_podcasts]




# desired layout --> check id's 
app.layout = html.Div(children = [
            dbc.Row([
                dbc.Col(html.H1('Serverless Podcast ETL'), width = 9, style = {'margin-left':'7px','margin-top':'7px'})
            ]),
        html.Hr(),
            dbc.Row([
                dbc.Col(dcc.Dropdown(podcast_options, id = 'podcast', placeholder="Select a Podcast")), 
                dbc.Col(dcc.Dropdown(id = 'episode', placeholder="Select an Episode")), 
                dbc.Col(dcc.Dropdown(id = 'entity_type', placeholder="Select a Type of Entity"))
            ]),
        html.Br(),  
            dbc.Row([
                dbc.Col(dcc.Graph(id='piechart'), width=4),
                dbc.Col(dcc.Graph(id='horizontal_barplot'), width = 8)  
            ]),
        html.Br(),  
            dbc.Row([
                dbc.Col(dcc.Graph(id='rolling_mean'), width = 8),
                dbc.Col(html.Img(id="image_wc", style={"vertical-align": "center", 'height':'100%', 'width':'100%'}), width = 4)
            ]),
        html.Br(),
            dbc.Row([
                dbc.Col(dcc.Graph(id='barplot'), width = 12)
            ])
    ]
)
      

# untested but should be good
@callback(
        Output('episode', 'options'),
        Input(component_id='podcast', component_property="value")
)
def populate_episodes(pod_id):
    print("updating episodes!")
    if pod_id is None:
        pod_id = 1
    
    connection = mysql.connector.connect(
        host=RDS_ENDPOINT,
        user=USER_NAME,
        password=PASSWORD,
        database=DB_NAME
    )
    cursor = connection.cursor()

    select_query = f"""
        SELECT DISTINCT episode_id
        FROM episode_dimension
        WHERE podcast_id = {pod_id}
        ORDER BY episode_release_date DESC
    """

    cursor.execute(select_query)
    unique_episodes = cursor.fetchall()

    # Close the database connection
    cursor.close()
    connection.close()

    episode_options = [{'label': value[0], 'value': value[0]} for value in unique_episodes]

    return episode_options

# untested but should be good
@callback(
        Output('entity_type', 'options'),
        Input(component_id='episode', component_property="value")
)
def populate_entities(episode_id):
    print("updating entities!")
    if episode_id is None:
        episode_id = 3

    connection = mysql.connector.connect(
        host=RDS_ENDPOINT,
        user=USER_NAME,
        password=PASSWORD,
        database=DB_NAME
    )
    cursor = connection.cursor()
    select_entites_query= f"""
        SELECT DISTINCT entity_type 
        FROM entity_dimension e
        WHERE episode_id = {episode_id}
    """
    cursor.execute(select_entites_query)
    unique_entities = cursor.fetchall()

    # Close the database connection
    cursor.close()
    connection.close()

    entity_options = [{'label': value[0], 'value': value[0]} for value in unique_entities]

    return entity_options


# needs input double check
@callback(
    Output('barplot', 'figure'),
    Input(component_id='entity_type', component_property='value'),
    Input(component_id='episode', component_property='value')
)
def update_barplot(entity_type, episode_id):
    print("updating barplot!")
    print(f"Entity_type is {entity_type}, and episode is {episode_id}")
    if entity_type is None:
        entity_type = "PERSON"
    if episode_id is None:
        episode_id = 3

    if ctx.triggered_id == "episode":
        raise PreventUpdate
    


    # Establish database connection
    connection = mysql.connector.connect(
        host=RDS_ENDPOINT,
        user=USER_NAME,
        password=PASSWORD,
        database=DB_NAME
    )

    cursor = connection.cursor()


    # Query the database for graph data
    select_query = f"""SELECT
        entity_text, COUNT(*) AS num_occurences
    FROM entity_dimension e
    WHERE entity_type = '{entity_type}'
    AND episode_id = {episode_id}
    GROUP BY entity_text
    ORDER BY num_occurences DESC
    """

    cursor.execute(select_query)
    results = cursor.fetchall()

    # Close the database connection
    cursor.close()
    connection.close()

    df = pd.DataFrame(data=results, columns=["entity_text", "num_occurences"])

    # Create and return a Plotly figure
    fig = px.bar(df, x='entity_text', y='num_occurences', title="Entity Mentions",  labels={'entity_text': ' ', 'num_occurences':' '}, template = template)
    fig.update_layout(hovermode="x")
    return fig


# needs input double check
@callback(
    Output('piechart', 'figure'),
    Input(component_id='entity_type', component_property='value'),
    Input(component_id='episode', component_property='value')
)
def update_piechart(entity_type, episode_id):
    print("updating graph!")
    if entity_type is None:
        entity_type = "PERSON"
    if episode_id is None:
        episode_id = 3
    if ctx.triggered_id == "episode":
        raise PreventUpdate

    # Establish database connection
    connection = mysql.connector.connect(
        host=RDS_ENDPOINT,
        user=USER_NAME,
        password=PASSWORD,
        database=DB_NAME
    )

    cursor = connection.cursor()

    # Query the database for graph data
    select_query = f"""
    SELECT s.overall_sentiment, COUNT(*)
    FROM entity_dimension e
    LEFT JOIN sentence_dimension s
    ON s.sentence_index = e.sentence_index
    WHERE e.entity_type = '{entity_type}'
    AND e.episode_id = {episode_id}
    GROUP BY s.overall_sentiment
    """

    cursor.execute(select_query)
    results = cursor.fetchall()

    # Close the database connection
    cursor.close()
    connection.close()

    df = pd.DataFrame(data=results, columns=["sentiment", "value"])

    # Create and return a Plotly figure
    fig = px.pie(df, values = "value", names='sentiment', title="Overall Sentiment", template = template, hole = .7)
    #fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    return fig

# needs input double check
@callback(
    Output('rolling_mean', 'figure'),
    Input(component_id='entity_type', component_property='value'),
    Input(component_id='episode', component_property='value')
)
def update_rollingmean(entity_type, episode_id):
    print("updating graph!")
    if entity_type is None:
        entity_type = "PERSON"
    if episode_id is None:
        episode_id = 3
    
    if ctx.triggered_id == "episode":
        raise PreventUpdate

    rolling_window = 50


    connection = mysql.connector.connect(
                host = RDS_ENDPOINT,
                user = USER_NAME,
                password = PASSWORD,
                database = DB_NAME
                )

    cursor = connection.cursor()

    select_query = f"""
    SELECT 
    e.entity_text,
    e.sentence_index,
    s.positive_score - s.negative_score
    FROM entity_dimension e
    LEFT JOIN sentence_dimension s
    ON s.sentence_index = e.sentence_index
    WHERE e.entity_type = '{entity_type}'
    AND e.episode_id = {episode_id}
    ORDER BY e.sentence_index ASC
    """

    cursor.execute(select_query)

    results = cursor.fetchall()

    cursor.close()
    connection.close()

    df = pd.DataFrame(data=results, columns = ["name", "time", "score"])
    df["name"] = df["name"].str.lower()
    df["rolling_positive_score"] = df["score"].rolling(window=rolling_window, min_periods=1).mean()
    fig = px.line(df, x="time", y="rolling_positive_score", title="Rolling Mean of Adjusted Sentiment",  labels={'time': 'Sentence Index', 'rolling_positive_score':' '})
    return fig

# needs input double check
@callback(
    Output('horizontal_barplot', 'figure'),
    Input(component_id='entity_type', component_property='value'), 
    Input(component_id='episode', component_property='value')
)
def update_hbar(entity_type, episode_id):
    if entity_type is None:
        entity_type = "PERSON"
    if episode_id is None:
        episode_id = 3
    if ctx.triggered_id == "episode":
        raise PreventUpdate

    # Establish database connection
    connection = mysql.connector.connect(
        host=RDS_ENDPOINT,
        user=USER_NAME,
        password=PASSWORD,
        database=DB_NAME
    )

    cursor = connection.cursor()

    # Query the database for graph data
    select_query = f"""
    SELECT 
    e.entity_text, 
    AVG(s.neutral_score)/(AVG(s.positive_score) + AVG(s.neutral_score) + AVG(s.negative_score)), 
    AVG(s.negative_score)/(AVG(s.positive_score) + AVG(s.neutral_score) + AVG(s.negative_score)), 
    AVG(s.positive_score)/(AVG(s.positive_score) + AVG(s.neutral_score) + AVG(s.negative_score)) AS pos
    FROM entity_dimension e
    LEFT JOIN sentence_dimension s
    ON s.sentence_index = e.sentence_index
    WHERE e.entity_type = '{entity_type}'
    AND e.episode_id = {episode_id}
    GROUP BY e.entity_text
    ORDER BY pos DESC
    """

    cursor.execute(select_query)
    results = cursor.fetchall()

    # Close the database connection
    cursor.close()
    connection.close()

    df = pd.DataFrame(data=results, columns=["entity_text", "Neutral Score", "Negative Score", "Positive Score"])

    # Create and return a Plotly figure
    fig = px.bar(df, x="entity_text", y=["Neutral Score", "Negative Score", "Positive Score"], title="Sentiment Proportions", labels = {"value": " ", "entity_text": " ", "variable": "Sentiment"})
    fig.update_layout(yaxis_range=[0,1])
    fig.update_layout(hovermode="x")
    return fig


# needs input double check
def plot_wordcloud(text):
    wc = WordCloud(stopwords=STOPWORDS, mask = wc_mask, mode = "RGBA", collocations = False, background_color = None, prefer_horizontal = 1, colormap="winter", width=480, height=360).generate(text)
    return wc.to_image()
@app.callback(
        Output('image_wc', 'src'), 
        Input(component_id='episode', component_property="value")
        )
def make_image(episode_id):
    if episode_id is None:
        episode_id = 3
    connection = mysql.connector.connect(
            host = RDS_ENDPOINT,
            user = USER_NAME,
            password = PASSWORD,
            database = DB_NAME
            )

    cursor = connection.cursor()


    select_query = f"""
    SELECT sentence_text
    FROM sentence_dimension
    WHERE episode_id = {episode_id}
    """

    cursor.execute(select_query)
    results = cursor.fetchall()
    cursor.close()
    connection.close()

    df = pd.DataFrame(data=results, columns = ["sentences"])
    text = ""
    for i in range(df.shape[0]):
        text = text + df.loc[i,"sentences"].replace("\n", " ")

    if text == "":
        text = "Empty"

    img = BytesIO()
    plot_wordcloud(text).save(img, format='PNG')
    return 'data:image/png;base64,{}'.format(base64.b64encode(img.getvalue()).decode())


if __name__ == '__main__':
    app.run_server(host='0.0.0.0', debug=True)





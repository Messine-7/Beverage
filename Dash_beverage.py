import dash
from dash import dcc, dash_table
from dash import html, ctx, callback
from dash.dependencies import Output, Input
import dash_bootstrap_components as dbc
import pandas as pd
import json
import requests
from pandas import json_normalize
from datetime import datetime 
import plotly.express as px
import seaborn as sns
import timedelta
import plotly.graph_objects as go


link = "https://raw.githubusercontent.com/murpi/wilddata/master/quests/beverage_dispenser.json"

r = requests.get(link)

data = json.loads(r.text)

df = pd.json_normalize(data,record_path= 'content')
df

df["date"] = pd.to_datetime(df["date"])

df.info()

df['year'] = df['date'].dt.year
df['month'] = df['date'].dt.month
df['day'] = df['date'].dt.day
df['weekday'] = df['date'].dt.weekday
df['day_name'] = df['date'].dt.day_name()
df['hour'] = df['date'].dt.hour

df

df["product"].unique()

#Fonction create columns gross margin
dict_gross_margin = {'coffee' : 0.70, 'soda' : 1, 'nrj' : 0.80, "refill" : 0}

def gross_margin(product) :
    
    for i in dict_gross_margin :
        if product == i :
            return dict_gross_margin[i]

df["gross_margin"] = df["product"].apply(gross_margin)

#Set date to index
df.set_index("date", inplace =True)

#Extraction du df les produits et machine 
dict_capacity = {"A" :{"coffee": 280, "soda":120,"nrj" :60},
                "B" :{"coffee": 280, "soda":120,"nrj" :60},
                "C" :{"coffee": 280, "soda":120,"nrj" :60},
                "D" :{"coffee": 280, "soda":120,"nrj" :60},} 

product_list = df["product"].tolist()
machine_list = df["machine"].tolist()
    

#liste final pour stockage
stock_list =[]

#initialisation d'un compteur pour les indices
x = 0

#loop sur les produit 
for product in product_list :
    

    #repere la lettre de la machine
    machine = machine_list[x]

    # Condition pour le rechargement
    if product == "refill" :
        dict_capacity[machine] = {"coffee": 280, "soda":120,"nrj" :60} 
        stock_list.append("refill")
        
   
    for j in dict_capacity[machine] :
        
    # déduit le stock         
        if j == product and dict_capacity[machine][j] > 1 : 
            dict_capacity[machine][j] -= 1
            stock_list.append(dict_capacity[machine][j])

    # Condition pour machine vide     
        elif j == product and dict_capacity[machine][j] == 1 : 
            dict_capacity[machine][j] -= 1
            stock_list.append("empty")
            
    # Il y 4 vente signaler comme error alors que la machine est censé être vide       
        elif j == product and dict_capacity[machine][j] == 0 : 
            stock_list.append("error")
        
    #Suis l'indice pour reperer la machine
    x += 1
            
            
len(stock_list)

#add stock column 
df["stock"] = stock_list

#Création d'une serie avec les date de remplissage
df_refill = df["machine"].loc[df["stock"] == "refill"]

#reset 'lindex pour counserver le datatime dans  la fonction
df.reset_index(inplace =True)

def duration_empty(x) :
    
    product = x.product
    machine = x.machine
    stock = x.stock
    date = x.date
    
    list_duration = []
    
    if stock == "empty" :
        for date_fill, machine_fill in df_refill.items():
            if machine_fill == machine and date_fill > date :
                duration = (date_fill - date)
                list_duration.append(duration)

                
        if len(list_duration) > 0 :    
            duration = min(list_duration)
            return duration
    

    else :
        pass
    
df["duration"] = df.apply(duration_empty, axis = 1)

pd.set_option("display.max_rows", 0)

#Conserve uniqueùent les fill value de colone duration 
df_empty = df.loc[df["stock"] == ("empty")]
df_empty.dropna(subset = "duration", axis = 0, inplace =True)

#display mean /sum empty product duration, Fill on monday morning is the best way to be less empty
pt_duration = pd.pivot_table(df_empty, index = "product", values = "duration", aggfunc =["mean", "sum", "min", "max"]) 

pt_duration.columns = ['_'.join(map(str, c)).strip('_') for c in pt_duration]

#Set date to index
df.set_index("date", inplace =True)

#Mean fill once week
print("La marge brut moyenne journalière  =",round(df.gross_margin.resample('D').sum().mean()))
print("La marge brut moyenne hebdomadaire  =",round(df.gross_margin.resample('W').sum().mean()))
print("La marge brut moyenne mensuel =",round(df.gross_margin.resample('M').sum().mean()))

#Mean fill once week
pt_sum_margin = pd.pivot_table(df, index = "product", values =  "gross_margin", aggfunc = "sum")
pt_sum_margin

#Mean fill once week without empty
Jour_total_4 = (df.index[-1] -df.index[0])*4

#Moyenne brut par produit 

list_product = ["coffee", "soda", "nrj"]
dict_margin_day = {} 
for i in list_product :
    gross_marge_avg_day = round(pt_sum_margin.loc[i][0] / (Jour_total_4.total_seconds() / 86400 - pt_duration.loc[i]["sum_duration"].total_seconds() / 86400),2)
    dict_margin_day[i] = gross_marge_avg_day

dict_margin_day

#Perte Brut par produit sur durée totale du dataset

dict_loose_product = {} 
for i in dict_margin_day :
    loose = round(dict_margin_day[i] * pt_duration.loc[i]["sum_duration"].total_seconds() / 86400,2)
    dict_loose_product[i]  = loose

dict_loose_product

#Total perte brut 
total_perte_brut = round(sum(dict_loose_product.values()))
total_perte_brut

#Total gagné avec un refill par semaine

total_earn_1_refill = df.gross_margin.sum()
total_earn_1_refill

#Net mois 1 refill :

refill_cost = 4*110
location_cost = 500
maintenance_cost = 400
total_days = round(((df.index[-1] -df.index[0]).total_seconds() / 86400),2)

#CA ramené à un mois
CA_month_1_refill = total_earn_1_refill*31 / total_days

#Margin NET 1 month 1 refill 
margin_1_refill_month = round(CA_month_1_refill - refill_cost - location_cost - maintenance_cost)
print("Le bénéfice net par mois avec un remplissage par semaine est de :", margin_1_refill_month)


#Perte ramené à un mois
loose_month_1_refill = total_perte_brut*31 / total_days

#Margin NET 1 month 2 refill 
margin_2_refill_month = round(CA_month_1_refill - (2*refill_cost) - location_cost - maintenance_cost + loose_month_1_refill)
print("Le bénéfice net par mois avec deux remplissage par semaine est de :", margin_2_refill_month)


pt_duration2 = pt_duration
pt_duration2["mean_duration"] = round(pt_duration["mean_duration"].dt.total_seconds()/ 86400 ,2)
pt_duration2['sum_duration'] = round(pt_duration['sum_duration'].dt.total_seconds()/ 86400 ,2)
pt_duration2['min_duration'] = round(pt_duration['min_duration'].dt.total_seconds()/ 86400 ,2)
pt_duration2['max_duration'] = round(pt_duration['max_duration'].dt.total_seconds()/ 86400 ,2)

pt_duration2.reset_index(inplace = True)

#---------------------------- DATA VIZ 

# Nb Vente et refill par jours 
sns.countplot(df, x= "day_name", hue= "product", order =("Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"))

# Nb Vente et refill par mois, Attention il y a moins de jours en novembre dans le DF 
sns.countplot(df, x= "month", hue= "product")

#On voit clairement qu'après le remplissage les ventes repartent, c'est le café qui domine les vente et qui atteint sont climax vers 9h, les sodas sont en deuxième position une vente stable au cour de la journée
#Les boissons énérgisantes sont vendu principalement le vendredi et samedi en fin de journée 

array= ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

list_color = ["#BFA2DB","#ECA869","#6886C5","#FF87CA"]
fig_1 = px.histogram(df, x="hour", 
                   
             facet_col = "day_name",
             facet_row = "machine",
             color = "product",
                  barmode="group", 
                  category_orders={"day_name": ("Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday")},
                  width=1900, height=1000,
                  color_discrete_sequence = list_color 
                  )
fig_1.add_vrect(x0= 10, x1 = 14, fillcolor ="green", opacity=0.2, annotation_text="refill",row="all", col=4)

fig_1.update_layout({
    'plot_bgcolor': 'rgba(0.1,0.1,0.1,0.1)'
})



#Echantillon sur première semaine de décembre 
df_dec = df["2019-12-02":"2019-12-09"]
df_dec_A = df_dec.loc[df_dec["machine"] == "A"]
list_color = ["#ECA869","#6886C5","#FF87CA","#BFA2DB"]
#df_dec = pd.pivot_table(df_dec, index = ["day_name", "hour"], columns = "product", values ="gross_margin", aggfunc = "sum")
#df_dec.index = pd.CategoricalIndex(df_dec.index, categories=cats, ordered=True)
#df_dec.sort_index(inplace =True)
fig_2= px.histogram(df_dec_A, x="hour", 
             facet_col = "day_name",
             color = "product",
                  barmode="group", 
                  category_orders={"day_name": ("Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday")},
                  width=1900, height=500,
                  title = "FIRST WEEK DECEMBER MACHINE A",
                   color_discrete_sequence = list_color )

fig_2.add_vrect(x0= 10, x1 = 14, fillcolor ="green", opacity=0.2, annotation_text="refill",row="all", col=4)
fig_2.update_layout({
    'plot_bgcolor': 'rgba(0.1,0.1,0.1,0.1)'
})



# Mean gross_marge by day_name
pt_mean_day_name = pd.pivot_table(df, index ="day_name", values = "gross_margin", aggfunc ="sum")
pt_mean_day_name

df.columns

gross_margin_day = df.gross_margin.resample('D').sum()

gross_margin_day = df.groupby([df.index.date,"product"]).sum().reset_index()
gross_margin_day = gross_margin_day.loc[gross_margin_day["product"] != "refill"]
gross_margin_day
list_color = ["#ECA869","#FF87CA","#6886C5"]
fig_3 = px.line(gross_margin_day, x ="level_0", y ="gross_margin", color = "product",color_discrete_sequence = list_color  )
fig_3.update_layout({
    'plot_bgcolor': 'rgba(0.1,0.1,0.1,0.1)'
})

fig_4 = go.Figure()

fig_4.add_trace(go.Indicator(
    value = 5200,
    delta = {'reference': 80},
    gauge = {
        'axis': {'visible': False}},
    domain = {'row': 0, 'column': 0},
    title=  " ONCE REFILL NET MAGIN MONTH",))

fig_5 = go.Figure()

fig_5.add_trace(go.Indicator(
    value = 6600,
    delta = {'reference': 80},
    gauge = {
        'axis': {'visible': False}},
    domain = {'row': 0, 'column': 0},
    title=  " TWICE REFILL NET MAGIN MONTH",))

logo = "https://image.noelshack.com/fichiers/2023/28/3/1689192261-title.png"

#---------------------------- DASH

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets,
                meta_tags=[{'name': 'viewport','content': 'width=device-width, initial-scale=1.0'}]) # permet a notre app d'etre responsive, s'adapter a lecran utilise

app.layout = html.Div(
    children=[
        
        html.Div(
            # display: flex = disposition flexible des element de la div 
            # justify-content: center = centre horizontalement les elements 
            # align-items: center = centre verticalement les elements 
            style={'display': 'flex', 'justify-content': 'center', 'align-items': 'center'},
            # affichage du logo avec sa taille et une petite marge au dessus et en dessous 
            children=[
                html.Img(src=logo, style={'width': '100rem','margin-top': '2rem','margin-bottom': '2rem'})
            ]
        ),
        
        

        
        
        html.Div(
            children=[dcc.Graph(figure=fig_1), 
                      dcc.Graph(figure=fig_2), 
                      dcc.Graph(figure=fig_3)
            ]
        ),
  
        html.Div(
            children=[
                html.H2("TABLE  OF EMPTY DURATION IN DAYS", style={'textAlign': 'center','font-family': 'sans-serif'})
            ]
        ),                     
                      
        html.H6(
            children=[
                      dash_table.DataTable(pt_duration2.to_dict('records'), [{"name": i, "id": i} for i in pt_duration2.columns]),
 

        html.Div([
            html.Div([
                html.H3(''),
                dcc.Graph(id='g1',figure=fig_4)
            ], className="six columns"),

            html.Div([
                html.H3(''),
                dcc.Graph(id='g2', figure=fig_5)
            ], className="six columns"),
        ], className="row")              
                
                      
                      
            ]
        )
    ]
)

app.css.append_css({
    'external_url': 'https://codepen.io/chriddyp/pen/bWLwgP.css'
})


       
if __name__ == '__main__':
    app.run_server(debug=False)
    
    

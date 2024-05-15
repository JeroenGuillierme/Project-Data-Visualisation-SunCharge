import pandas as pd
import plotly.graph_objects as go

# Import vendors dataset
vendors = pd.read_csv("https://raw.githubusercontent.com/JannesPeeters/suncharge/main/data/Vendors.csv").iloc[:, 1:]
vendors["lat"] = [51.2998974, 51.1186258, 45.7555253, 30.775702, 51.4954609, 52.400426, 42.3528084, 31.1574046, 24.6716922]
vendors["lon"] = [4.3048587, 16.9958199, 4.7648154, 120.366306, 7.4761266, 16.5898525, -83.1816052, 121.4989051, 120.8843678]

# Import plants dataset
plants = pd.read_csv("https://raw.githubusercontent.com/JannesPeeters/suncharge/main/data/Plants.csv").iloc[:, 1:]
plants["lat"] = [51.2998974, 51.1186258, 45.7555253, 51.2998974, 51.1186258, 45.7555253, 52.4287204, 57.7234656]
plants["lon"] = [4.3048587, 16.9958199, 4.7648154, 4.3048587 + 1, 16.9958199 + 1, 4.7648154 + 1, -1.8993951, 11.8539931]

# Import materials and MaterialPlantRelation datasets
materials = pd.read_csv("https://raw.githubusercontent.com/JannesPeeters/suncharge/main/data/Materials.csv").iloc[:, 1:]
mpr = pd.read_csv("https://raw.githubusercontent.com/JannesPeeters/suncharge/main/data/MaterialPlantRelation.csv").iloc[:, 1:]
m = mpr.merge(materials, how="left", on="MaterialKey")

# Actual vendors, production centers, distribution centers datasets
avendors = vendors.iloc[3:, :].reset_index(drop=True)
pcenters = pd.merge(vendors.iloc[:3, :], plants.iloc[:3, :], on=["lat", "lon"]).reset_index(drop=True)
dcenters = plants.iloc[3:, :].reset_index(drop=True)

# Customers and sales tables
customers = pd.read_csv("https://raw.githubusercontent.com/JannesPeeters/suncharge/main/data/Customers.csv").iloc[:, 1:]
sales = pd.read_csv("https://raw.githubusercontent.com/JannesPeeters/suncharge/main/data/Sales.csv").iloc[:, 1:]
cl = pd.read_csv("https://raw.githubusercontent.com/google/dspl/master/samples/google/canonical/countries.csv").rename(columns={"name": "CustomerCountry", "latitude": "lat", "longitude": "lon"})

sales_pop = pd.merge(sales, customers, on=["CustomerKey", "PlantKey"])
sales_pop["DeliveryDate"] = pd.to_datetime(sales_pop["DeliveryDate"], yearfirst=True)
sales_pop["RequestedDeliveryDate"] = pd.to_datetime(sales_pop["RequestedDeliveryDate"], yearfirst=True)
sales_pop["AY"], sales_pop["AM"] = sales_pop["DeliveryDate"].dt.year, sales_pop["DeliveryDate"].dt.month
sales_pop["PY"], sales_pop["PM"] = sales_pop["RequestedDeliveryDate"].dt.year, sales_pop["RequestedDeliveryDate"].dt.month
sales_pop["delay"] = (sales_pop["DeliveryDate"] - sales_pop["RequestedDeliveryDate"]).dt.days

sqd = (
    sales_pop.drop(["DeliveryDate", "RequestedDeliveryDate"], axis=1).groupby(["CustomerCountry", "PlantKey", "AY", "AM"])
    .agg({'OrderQuantity': 'sum', 'delay': 'mean'})
    .reset_index()
    .merge(dcenters[["PlantKey", "PlantName", "lat", "lon"]], how="left", on="PlantKey")
    .merge(cl[["CustomerCountry", "lat", "lon"]], how="left", on="CustomerCountry")
    .rename(columns={"PlantName": "PlantName_x", "CustomerCountry": "PlantName_y", "OrderQuantity": "size"})
    .drop(columns=["PlantKey"])
)
uniq_sqd = sqd[["PlantName_y", "lat_y", "lon_y"]].drop_duplicates()

# Purchases table
purchases = pd.read_csv("https://raw.githubusercontent.com/JannesPeeters/suncharge/main/data/Purchases.csv").iloc[:, 1:]
purchases["ActualGoodsReceiptDate"] = pd.to_datetime(purchases["ActualGoodsReceiptDate"], yearfirst=True)
purchases["PlannedGoodsReceiptDate"] = pd.to_datetime(purchases["PlannedGoodsReceiptDate"], yearfirst=True)
purchases["AY"], purchases["AM"] = purchases["ActualGoodsReceiptDate"].dt.year, purchases["ActualGoodsReceiptDate"].dt.month
purchases["PY"], purchases["PM"] = purchases["PlannedGoodsReceiptDate"].dt.year, purchases["PlannedGoodsReceiptDate"].dt.month
purchases["delay"] = (purchases["ActualGoodsReceiptDate"] - purchases["PlannedGoodsReceiptDate"]).dt.days

pqd = (
    purchases.drop(["ActualGoodsReceiptDate", "PlannedGoodsReceiptDate"], axis=1).groupby(["VendorKey", "PlantKey", "AY", "AM"])
    .agg({'PurchaseOrderQuantity': 'sum', 'delay': 'mean'})
    .reset_index()
    .merge(pcenters[["VendorKey", "PlantKey", "PlantName", "lat", "lon"]], how="left", on="VendorKey")
    .merge(dcenters[["PlantKey", "PlantName", "lat", "lon"]], how="left", left_on="PlantKey_x", right_on="PlantKey")
    .drop(columns=["PlantKey", "PlantKey_x", "PlantKey_y", "VendorKey"])
    .rename(columns={"PurchaseOrderQuantity": "size"})
)

fig = go.Figure()
# Add vendors to map
fig.add_trace(
    go.Scattergeo(
        hoverinfo="text",
        lat=avendors["lat"],
        lon=avendors["lon"],
        marker=dict(
            color="rgb(255, 0, 0)",
            line=dict(
                width=3,
                color="rgba(68, 68, 68, 0)",
            ),
            opacity=0.5,
            size=10,
        ),
        name="Vendors",
        text=[text["VendorName"] + "<br>Vendor<br><br>Supplies:<br>" + "<br>".join(m[m["VendorKey"] == text["VendorKey"]]["MaterialDescription"].unique()) for *_, text in avendors[["VendorKey", "VendorName"]].iterrows()],
    )
)

# Add production centers to map
fig.add_trace(
    go.Scattergeo(
        hoverinfo="text",
        lat=pcenters["lat"],
        lon=pcenters["lon"],
        marker=dict(
            color="rgb(0, 255, 0)",
            line=dict(
                width=3,
                color="rgba(68, 68, 68, 0)",
            ),
            opacity=0.5,
            size=10,
        ),
        name="Production Centers",
        text=[text + "<br>Production" for text in pcenters["PlantName"]],
    )
)

# Add distribution centers to map
fig.add_trace(
    go.Scattergeo(
        hoverinfo="text",
        lat=dcenters["lat"],
        lon=dcenters["lon"],
        marker=dict(
            color="rgb(0, 0, 255)",
            line=dict(
                width=3,
                color="rgba(68, 68, 68, 0)",
            ),
            opacity=0.5,
            size=10,
        ),
        name="Distribution Centers",
        text=[text + "<br>Distribution" for text in dcenters["PlantName"]],
    )
)

# Add customers to map
fig.add_trace(
    go.Scattergeo(
        hoverinfo="text",
        lat=uniq_sqd["lat_y"],
        lon=uniq_sqd["lon_y"],
        marker=dict(
            color="rgb(0, 255, 255)",
            line=dict(
                width=3,
                color="rgba(68, 68, 68, 0)",
            ),
            opacity=0.5,
            size=10,
        ),
        name="Customers",
        text=[text + "<br>Customer" for text in uniq_sqd["PlantName_y"]],
    )
)

# Add legend groups
fig.add_trace(go.Scattergeo(lat=[None], lon=[None], legendgroup="dist", marker=dict(color="black", line=dict(width=3, color="black"), opacity=0.5, size=10, symbol="y-right"), name="Routes PROD -> DIST", showlegend=True))
fig.add_trace(go.Scattergeo(lat=[None], lon=[None], legendgroup="cust", marker=dict(color="black", line=dict(width=3, color="black"), opacity=0.5, size=10, symbol="y-right"), name="Routes DIST -> CUST", showlegend=True))

# Add custom color legend
fig.add_trace(go.Scattergeo(lat=[None], lon=[None], name="Delay <-1 days", marker=dict(color="purple", line=dict(width=3, color="purple"), opacity=0.5, size=10, symbol="line-ew"), showlegend=True))
fig.add_trace(go.Scattergeo(lat=[None], lon=[None], name="Delay <1 days", marker=dict(color="green", line=dict(width=3, color="green"), opacity=0.5, size=10, symbol="line-ew"), showlegend=True))
fig.add_trace(go.Scattergeo(lat=[None], lon=[None], name="Delay <3 days", marker=dict(color="orange", line=dict(width=3, color="orange"), opacity=0.5, size=10, symbol="line-ew"), showlegend=True))
fig.add_trace(go.Scattergeo(lat=[None], lon=[None], name="Delay >3 days", marker=dict(color="red", line=dict(width=3, color="red"), opacity=0.5, size=10, symbol="line-ew"), showlegend=True))

# World map
fig.update_layout(
    showlegend=True,
    geo=go.layout.Geo(
        center={"lat": 50.5039, "lon": 4.4699},
        countrycolor="rgb(217, 217, 217)",
        countrywidth=1,
        lakecolor="rgb(255, 255, 255)",
        landcolor="rgb(243, 243, 243)",
        projection={"type": "mercator", "scale": 5},
        showcountries=True,
        showlakes=True,
        showland=True,
        subunitcolor="rgb(217, 217, 217)",
        subunitwidth=0.5,
        scope="world",
    ),
)

def plot_line(figure, ser, max_size, leg):
    figure.add_trace(
        go.Scattergeo(
            hoverinfo="text",
            lat=ser[["lat_x", "lat_y"]],
            legendgroup=leg,
            line=dict(
                width=0.2+4*ser["size"]/max_size,
                color="purple" if ser["delay"] < -1 else ("green" if ser["delay"] < 1 else ("orange" if ser["delay"] < 3 else "red")),
            ),
            lon=ser[["lon_x", "lon_y"]],
            mode="lines+markers",
            name=f"{ser['PlantName_x']} -> {ser['PlantName_y']}",
            showlegend=False,
            text=f"{ser['PlantName_x']} -> {ser['PlantName_y']}<br><br>Quantity: {ser["size"]}<br>Avg. delay: {round(ser["delay"], 1)} days",
        )
    )
    
def plot_inactive(figure, ser, leg):
    figure.add_trace(
        go.Scattergeo(
            lat=ser[["lat_x", "lat_y"]],
            legendgroup=leg,
            line=dict(
                width=0,
                color="purple",
            ),
            lon=ser[["lon_x", "lon_y"]],
            showlegend=False
        )
    )

# Add arrows between dots
frames = []
ppp = pd.concat([pqd, sqd])

for *_, y in ppp[["AY", "AM"]].drop_duplicates().iterrows():
    fog = go.Figure()
    
    for *_, u in ppp[["PlantName_x", "PlantName_y"]].drop_duplicates().iterrows():
        pqu = pqd[(pqd["AY"] == y["AY"]) & (pqd["AM"] == y["AM"])
                  & (pqd["PlantName_x"] == u["PlantName_x"]) & (pqd["PlantName_y"] == u["PlantName_y"])].reset_index(drop=True)
        squ = sqd[(sqd["AY"] == y["AY"]) & (sqd["AM"] == y["AM"])
                  & (sqd["PlantName_x"] == u["PlantName_x"]) & (sqd["PlantName_y"] == u["PlantName_y"])].reset_index(drop=True)
        
        # Add lines between production and distribution centers
        if len(pqu):
            plot_line(fog, pqu.iloc[0], ppp["size"].max(), "dist")
        else:
            plot_inactive(fog, ppp[["lat_x", "lat_y", "lon_x", "lon_y"]], "dist")
                
        # Add lines between distribution centers and customers
        if len(squ):
            plot_line(fog, squ.iloc[0], ppp["size"].max(), "cust")
        else:
            plot_inactive(fog, ppp[["lat_x", "lat_y", "lon_x", "lon_y"]], "cust")
            
    frames.append(go.Frame(data=fig.data + fog.data, name=f"{y["AY"]}-{y["AM"]}"))

sliders = [
    {
        "currentvalue": {"prefix": "Month = "},
        "len": 0.9,
        "steps": [
            {
                "args": [
                    [f.name],
                    {
                        "frame": {"duration": 0},
                        "fromcurrent": True,
                        "mode": "immediate",
                        "transition": {"duration": 0, "easing": "linear"},
                    },
                ],
                "label": f.name,
                "method": "animate",
            }
            for f in frames
        ],
        "x": 0.1,
        "y": 0,
    }
]

go.Figure.write_html(go.Figure(data=frames[0].data, frames=frames, layout=fig.layout).update_layout(sliders=sliders), file="geoviz.html", auto_play=True)